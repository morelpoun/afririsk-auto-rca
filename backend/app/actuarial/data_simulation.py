"""Génération d'un portefeuille auto synthétique.

Les relations entre variables et sinistralité sont des hypothèses de
démonstration (documentées ci-dessous, initialement établies pour la RCA),
pas des statistiques de marché réelles. Faute de données réelles par pays,
ce même modèle sert de base de calibration pour tous les pays CIMA — voir
`app/regulatory/cima_countries.py` pour l'avertissement complet sur cette
limite. `zone` est volontairement une classification générique
urbain/rural (zone de la capitale ou d'une grande ville vs. reste du pays)
plutôt qu'un nom de ville RCA-spécifique, pour rester applicable à n'importe
quel pays CIMA.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CURRENT_YEAR = 2026

# Hypothèses de sinistralité (log-fréquence de base et effets multiplicatifs)
BASE_LOG_FREQUENCY = -2.1
EFFECT_JEUNE_CONDUCTEUR = 0.45  # < 25 ans
EFFECT_USAGE_PROFESSIONNEL = 0.20
EFFECT_ZONE_URBAINE = 0.25
EFFECT_SINISTRE_ANTERIEUR = 0.18  # par sinistre antérieur
EFFECT_ANCIENNETE_PERMIS = -0.02  # par année d'ancienneté (plafonnée)

# Hypothèses de coût moyen par sinistre (FCFA)
BASE_SEVERITY = 120_000.0
EFFECT_VALEUR_VEHICULE = 0.025  # part de la valeur assurée
EFFECT_ZONE_URBAINE_SEVERITY = 60_000.0
EFFECT_PUISSANCE_SEVERITY = 8_000.0  # par CV


def generate_portfolio(n: int = 15_000, seed: int = 42) -> pd.DataFrame:
    """Génère un portefeuille de contrats auto avec sinistralité simulée."""
    rng = np.random.default_rng(seed)

    age_conducteur = rng.integers(18, 76, size=n)
    sexe = rng.choice(["M", "F"], size=n, p=[0.65, 0.35])

    max_anciennete = np.maximum(age_conducteur - 18, 0)
    anciennete_permis = rng.integers(0, max_anciennete + 1)

    usage = rng.choice(["particulier", "professionnel"], size=n, p=[0.8, 0.2])
    zone = rng.choice(["urbain", "rural"], size=n, p=[0.6, 0.4])
    puissance_cv = rng.integers(4, 21, size=n)
    annee_vehicule = rng.integers(2000, CURRENT_YEAR, size=n)
    valeur_vehicule_fcfa = rng.lognormal(mean=15.8, sigma=0.5, size=n).round(-3)
    garantie = rng.choice(
        ["tiers_simple", "tiers_etendu", "tous_risques"], size=n, p=[0.5, 0.3, 0.2]
    )
    nb_annees_assure = rng.integers(0, 16, size=n)
    nb_sinistres_anterieurs = rng.poisson(0.3, size=n)
    exposition = np.ones(n)  # contrats annuels pleins (v1)

    jeune = (age_conducteur < 25).astype(float)
    usage_pro = (usage == "professionnel").astype(float)
    zone_urbain = (zone == "urbain").astype(float)
    anciennete_plafonnee = np.minimum(anciennete_permis, 20)

    log_lambda = (
        BASE_LOG_FREQUENCY
        + EFFECT_JEUNE_CONDUCTEUR * jeune
        + EFFECT_USAGE_PROFESSIONNEL * usage_pro
        + EFFECT_ZONE_URBAINE * zone_urbain
        + EFFECT_SINISTRE_ANTERIEUR * nb_sinistres_anterieurs
        + EFFECT_ANCIENNETE_PERMIS * anciennete_plafonnee
    )
    lam = np.exp(log_lambda) * exposition
    nb_sinistres = rng.poisson(lam)

    mean_cost = (
        BASE_SEVERITY
        + EFFECT_VALEUR_VEHICULE * valeur_vehicule_fcfa
        + EFFECT_ZONE_URBAINE_SEVERITY * zone_urbain
        + EFFECT_PUISSANCE_SEVERITY * puissance_cv
    )
    # Gamma(shape=2) borné positif, moyenne = mean_cost
    shape = 2.0
    cost_draws = rng.gamma(shape=shape, scale=mean_cost / shape, size=n)
    cout_moyen_sinistre = np.where(nb_sinistres > 0, cost_draws, np.nan)

    return pd.DataFrame(
        {
            "age_conducteur": age_conducteur,
            "sexe": sexe,
            "anciennete_permis": anciennete_permis,
            "usage": usage,
            "zone": zone,
            "puissance_cv": puissance_cv,
            "annee_vehicule": annee_vehicule,
            "valeur_vehicule_fcfa": valeur_vehicule_fcfa,
            "garantie": garantie,
            "nb_annees_assure": nb_annees_assure,
            "nb_sinistres_anterieurs": nb_sinistres_anterieurs,
            "exposition": exposition,
            "nb_sinistres": nb_sinistres,
            "cout_moyen_sinistre": cout_moyen_sinistre,
        }
    )
