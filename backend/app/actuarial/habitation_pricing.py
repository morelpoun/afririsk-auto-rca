"""Moteur actuariel habitation (MRH) : même architecture que le moteur auto
(`pricing.py`) — GLM fréquence (Poisson) + sévérité (Gamma), décomposition
explicative, chargements commerciaux — appliquée aux facteurs de risque
habitation. Modèle de risque unique, partagé par tous les pays CIMA (voir
app/regulatory/cima_countries.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from app.actuarial.glm_utils import decompose

FREQUENCY_FORMULA = (
    "nb_sinistres ~ materiaux_precaire + materiaux_semi_dur + zone_urbain "
    "+ sans_securite + anciennete_plafonnee + nb_sinistres_anterieurs"
)
SEVERITY_FORMULA = "cout_moyen_sinistre ~ valeur_batiment + valeur_contenu + materiaux_precaire"

# Chargements commerciaux — indépendants de ceux de la branche auto (une
# compagnie peut avoir une politique de frais différente par branche), mêmes
# hypothèses de démonstration à valider selon la réglementation CIMA.
FRAIS_GESTION = 6_000.0
MARGE_TECHNIQUE = 0.15
TAUX_TAXE = 0.20

# Chargement de garantie : "multirisque" couvre plus de périls que
# "incendie_simple" — approximé par un multiplicateur simple, comme pour la
# garantie auto (simplification MVP).
GARANTIE_LOADING = {
    "incendie_simple": 1.0,
    "multirisque": 1.6,
}


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les variables dérivées utilisées par les formules GLM."""
    df = df.copy()
    df["materiaux_precaire"] = (df["materiaux_construction"] == "precaire").astype(float)
    df["materiaux_semi_dur"] = (df["materiaux_construction"] == "semi_dur").astype(float)
    df["zone_urbain"] = (df["zone"] == "urbain").astype(float)
    df["sans_securite"] = (~df["securite"].astype(bool)).astype(float)
    df["anciennete_plafonnee"] = df["anciennete_batiment"].clip(upper=40).astype(float)
    return df


@dataclass
class HabitationPricingResult:
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


class HabitationActuarialEngine:
    """Encapsule les modèles GLM fréquence/sévérité habitation calibrés sur
    un portefeuille — même principe que `actuarial.pricing.ActuarialEngine`.
    """

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
        freq_vars = [
            "materiaux_precaire",
            "materiaux_semi_dur",
            "zone_urbain",
            "sans_securite",
            "anciennete_plafonnee",
            "nb_sinistres_anterieurs",
        ]
        self.freq_means = {v: float(df[v].mean()) for v in freq_vars}

        sev_df = df[df["nb_sinistres"] > 0]
        self.sev_model = smf.glm(
            formula=SEVERITY_FORMULA,
            data=sev_df,
            family=sm.families.Gamma(link=sm.families.links.Log()),
        ).fit()
        sev_vars = ["valeur_batiment", "valeur_contenu", "materiaux_precaire"]
        self.sev_means = {v: float(sev_df[v].mean()) for v in sev_vars}

    def _fitted(self) -> bool:
        return self.freq_model is not None and self.sev_model is not None

    def price(self, contract: dict) -> HabitationPricingResult:
        if not self._fitted():
            raise RuntimeError("HabitationActuarialEngine.fit() doit être appelé avant price().")

        x = {
            "materiaux_precaire": 1.0 if contract["materiaux_construction"] == "precaire" else 0.0,
            "materiaux_semi_dur": 1.0 if contract["materiaux_construction"] == "semi_dur" else 0.0,
            "zone_urbain": 1.0 if contract["zone"] == "urbain" else 0.0,
            "sans_securite": 0.0 if contract["securite"] else 1.0,
            "anciennete_plafonnee": min(float(contract["anciennete_batiment"]), 40.0),
            "nb_sinistres_anterieurs": float(contract["nb_sinistres_anterieurs"]),
            "valeur_batiment": float(contract["valeur_batiment"]),
            "valeur_contenu": float(contract["valeur_contenu"]),
        }

        frequence, freq_baseline, freq_contrib = decompose(self.freq_model.params, self.freq_means, x)
        cout_moyen, sev_baseline, sev_contrib = decompose(self.sev_model.params, self.sev_means, x)

        garantie = contract["garantie"]
        loading = GARANTIE_LOADING.get(garantie, 1.0)

        prime_pure = frequence * cout_moyen * loading
        prime_nette = prime_pure * (1 + MARGE_TECHNIQUE) + FRAIS_GESTION
        prime_commerciale = prime_nette * (1 + TAUX_TAXE)

        return HabitationPricingResult(
            frequence_estimee=frequence,
            cout_moyen_estime=cout_moyen,
            prime_pure=prime_pure,
            frais_gestion=FRAIS_GESTION,
            marge_technique=prime_pure * MARGE_TECHNIQUE,
            taxes=prime_commerciale - prime_nette,
            prime_commerciale=prime_commerciale,
            frequence_contributions=freq_contrib,
            severite_contributions=sev_contrib,
            frequence_moyenne_portefeuille=freq_baseline,
            cout_moyen_portefeuille=sev_baseline,
        )
