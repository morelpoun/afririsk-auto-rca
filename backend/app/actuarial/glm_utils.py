"""Utilitaires GLM partagés entre les moteurs actuariels par branche
(auto, habitation...) : calcul du prédicteur linéaire et décomposition
explicative d'une prédiction par rapport à la moyenne du portefeuille.
"""
from __future__ import annotations

import math

import pandas as pd


def linear_predictor(params: pd.Series, x: dict[str, float]) -> float:
    lp = params.get("Intercept", 0.0)
    for name, coef in params.items():
        if name == "Intercept":
            continue
        lp += coef * x.get(name, 0.0)
    return lp


def decompose(params: pd.Series, means: dict[str, float], x: dict[str, float]):
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
