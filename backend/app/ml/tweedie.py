"""Modèle Tweedie : prédit directement le coût total par police (0 si aucun
sinistre, sinon somme des sinistres), sans passer par fréquence × sévérité.
Bon benchmark actuariel classique face au GLM fréquence/sévérité et à
l'approche machine learning — voir docs/ml_methodology.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from app.ml.features import FEATURES

MODEL_VERSION = "TWEEDIE_GLM_V1"
VAR_POWER = 1.5  # entre 1 (Poisson) et 2 (Gamma) : régime Poisson composé-Gamma, typique des coûts de sinistres


class TweedieModel:
    """GLM Tweedie (lien log) sur `df` enrichi par
    `app.actuarial.pricing.add_derived_features` (doit contenir FEATURES,
    `exposition`, `nb_sinistres`, `cout_moyen_sinistre`).
    """

    formula = "cout_total ~ " + " + ".join(FEATURES)

    def __init__(self) -> None:
        self.result = None

    def fit(self, df: pd.DataFrame) -> "TweedieModel":
        data = df.copy()
        data["cout_total"] = data["nb_sinistres"] * data["cout_moyen_sinistre"].fillna(0.0)
        family = sm.families.Tweedie(var_power=VAR_POWER, link=sm.families.links.Log())
        self.result = smf.glm(
            formula=self.formula,
            data=data,
            family=family,
            offset=np.log(data["exposition"]),
        ).fit()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.result is None:
            raise RuntimeError("TweedieModel.fit() doit être appelé avant predict().")
        offset = np.log(df["exposition"])
        predicted_total = self.result.predict(df, offset=offset)
        return (predicted_total / df["exposition"]).to_numpy()
