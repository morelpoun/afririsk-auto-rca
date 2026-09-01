"""Modèle XGBoost avec objectif Tweedie, entraîné sur la prime pure observée
(coût total / exposition) pondérée par l'exposition — approche standard pour
transposer un GBM aux données de sinistralité.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from app.ml.features import FEATURES

MODEL_VERSION = "XGBOOST_TWEEDIE_V1"
VAR_POWER = 1.5


class XGBoostPricingModel:
    def __init__(self) -> None:
        self.model = XGBRegressor(
            objective="reg:tweedie",
            tweedie_variance_power=VAR_POWER,
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )

    def fit(self, X: pd.DataFrame, y_pure_premium: pd.Series, exposure: pd.Series) -> "XGBoostPricingModel":
        self.model.fit(X[FEATURES], y_pure_premium, sample_weight=exposure)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X[FEATURES])
