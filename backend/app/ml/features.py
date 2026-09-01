"""Jeu de variables et cible communs aux modèles ML, pour une comparaison
équitable avec le moteur GLM fréquence/sévérité de production.
"""
from __future__ import annotations

import pandas as pd

from app.actuarial.pricing import add_derived_features

FEATURES = [
    "age_conducteur",
    "anciennete_permis",
    "usage_pro",
    "zone_bangui",
    "puissance_cv",
    "valeur_vehicule_fcfa",
    "nb_sinistres_anterieurs",
]


def prepare_ml_dataset(portfolio: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Retourne (X, prime_pure_observee, exposition).

    `prime_pure_observee` est le coût total observé par police divisé par son
    exposition (0 si aucun sinistre) — la cible que fréquence×sévérité,
    Tweedie et XGBoost cherchent chacun à prédire.
    """
    df = add_derived_features(portfolio)
    cout_total = df["nb_sinistres"] * df["cout_moyen_sinistre"].fillna(0.0)
    prime_pure_observee = cout_total / df["exposition"]
    return df[FEATURES].copy(), prime_pure_observee, df["exposition"].copy()
