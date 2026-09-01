"""Moteur actuariel : fréquence (GLM Poisson), sévérité (GLM Gamma) et
calcul de prime pure / prime commerciale, avec décomposition explicative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

FREQUENCY_FORMULA = (
    "nb_sinistres ~ jeune + usage_pro + zone_bangui "
    "+ nb_sinistres_anterieurs + anciennete_plafonnee"
)
SEVERITY_FORMULA = "cout_moyen_sinistre ~ valeur_vehicule_fcfa + zone_bangui + puissance_cv"

# Chargements commerciaux — hypothèses de démonstration, à valider selon la
# réglementation CIMA et la politique tarifaire de la compagnie.
FRAIS_GESTION_FCFA = 8_000.0
MARGE_TECHNIQUE = 0.12
TAUX_TAXE = 0.20

# Chargement de garantie : la fréquence/sévérité simulées représentent un
# sinistre "type" ; on approxime l'élargissement de couverture par un
# multiplicateur simple (simplification MVP, à remplacer par un vrai modèle
# par garantie quand des données réelles seront disponibles).
GARANTIE_LOADING = {
    "tiers_simple": 1.0,
    "tiers_etendu": 1.3,
    "tous_risques": 1.8,
}


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les variables dérivées utilisées par les formules GLM."""
    df = df.copy()
    df["jeune"] = (df["age_conducteur"] < 25).astype(float)
    df["usage_pro"] = (df["usage"] == "professionnel").astype(float)
    df["zone_bangui"] = (df["zone"] == "bangui").astype(float)
    df["anciennete_plafonnee"] = df["anciennete_permis"].clip(upper=20).astype(float)
    return df


def _linear_predictor(params: pd.Series, x: dict[str, float]) -> float:
    lp = params.get("Intercept", 0.0)
    for name, coef in params.items():
        if name == "Intercept":
            continue
        lp += coef * x.get(name, 0.0)
    return lp


def _decompose(params: pd.Series, means: dict[str, float], x: dict[str, float]):
    """Décompose exp(linear_predictor) en (valeur moyenne du portefeuille)
    x (produit de facteurs multiplicatifs par variable), pour expliquer
    pourquoi une prédiction s'écarte de la moyenne du portefeuille.
    """
    baseline_lp = params.get("Intercept", 0.0)
    for name, coef in params.items():
        if name == "Intercept":
            continue
        baseline_lp += coef * means.get(name, 0.0)
    baseline = math.exp(baseline_lp)

    contributions = {}
    for name, coef in params.items():
        if name == "Intercept":
            continue
        contributions[name] = math.exp(coef * (x.get(name, 0.0) - means.get(name, 0.0)))

    prediction = baseline
    for factor in contributions.values():
        prediction *= factor
    return prediction, baseline, contributions


@dataclass
class PricingResult:
    frequence_estimee: float
    cout_moyen_estime: float
    prime_pure: float
    frais_gestion: float
    marge_technique: float
    taxes: float
    prime_commerciale: float
    frequence_contributions: dict[str, float] = field(default_factory=dict)
    severite_contributions: dict[str, float] = field(default_factory=dict)
    frequence_moyenne_portefeuille: float = 0.0
    cout_moyen_portefeuille: float = 0.0


class ActuarialEngine:
    """Encapsule les modèles GLM fréquence/sévérité calibrés sur un portefeuille."""

    def __init__(self) -> None:
        self.freq_model = None
        self.sev_model = None
        self.freq_means: dict[str, float] = {}
        self.sev_means: dict[str, float] = {}

    def fit(self, portfolio: pd.DataFrame) -> None:
        df = add_derived_features(portfolio)

        self.freq_model = smf.glm(
            formula=FREQUENCY_FORMULA,
            data=df,
            family=sm.families.Poisson(),
            offset=np.log(df["exposition"]),
        ).fit()
        freq_vars = ["jeune", "usage_pro", "zone_bangui", "nb_sinistres_anterieurs", "anciennete_plafonnee"]
        self.freq_means = {v: float(df[v].mean()) for v in freq_vars}

        sev_df = df[df["nb_sinistres"] > 0]
        self.sev_model = smf.glm(
            formula=SEVERITY_FORMULA,
            data=sev_df,
            family=sm.families.Gamma(link=sm.families.links.Log()),
        ).fit()
        sev_vars = ["valeur_vehicule_fcfa", "zone_bangui", "puissance_cv"]
        self.sev_means = {v: float(sev_df[v].mean()) for v in sev_vars}

    def _fitted(self) -> bool:
        return self.freq_model is not None and self.sev_model is not None

    def price(self, contract: dict) -> PricingResult:
        if not self._fitted():
            raise RuntimeError("ActuarialEngine.fit() doit être appelé avant price().")

        x = {
            "jeune": 1.0 if contract["age_conducteur"] < 25 else 0.0,
            "usage_pro": 1.0 if contract["usage"] == "professionnel" else 0.0,
            "zone_bangui": 1.0 if contract["zone"] == "bangui" else 0.0,
            "nb_sinistres_anterieurs": float(contract["nb_sinistres_anterieurs"]),
            "anciennete_plafonnee": min(float(contract["anciennete_permis"]), 20.0),
            "valeur_vehicule_fcfa": float(contract["valeur_vehicule_fcfa"]),
            "puissance_cv": float(contract["puissance_cv"]),
        }

        frequence, freq_baseline, freq_contrib = _decompose(
            self.freq_model.params, self.freq_means, x
        )
        cout_moyen, sev_baseline, sev_contrib = _decompose(
            self.sev_model.params, self.sev_means, x
        )

        garantie = contract["garantie"]
        loading = GARANTIE_LOADING.get(garantie, 1.0)

        prime_pure = frequence * cout_moyen * loading
        prime_nette = prime_pure * (1 + MARGE_TECHNIQUE) + FRAIS_GESTION_FCFA
        prime_commerciale = prime_nette * (1 + TAUX_TAXE)

        return PricingResult(
            frequence_estimee=frequence,
            cout_moyen_estime=cout_moyen,
            prime_pure=prime_pure,
            frais_gestion=FRAIS_GESTION_FCFA,
            marge_technique=prime_pure * MARGE_TECHNIQUE,
            taxes=prime_commerciale - prime_nette,
            prime_commerciale=prime_commerciale,
            frequence_contributions=freq_contrib,
            severite_contributions=sev_contrib,
            frequence_moyenne_portefeuille=freq_baseline,
            cout_moyen_portefeuille=sev_baseline,
        )
