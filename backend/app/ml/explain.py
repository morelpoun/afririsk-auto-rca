"""Explicabilité du modèle XGBoost via SHAP (contribution additive par
variable — complément du modèle boîte noire, indispensable en assurance où
un tarif doit pouvoir être justifié).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from app.ml.features import FEATURES
from app.ml.xgboost_model import XGBoostPricingModel


def explain_instance(model: XGBoostPricingModel, x_row: pd.DataFrame) -> dict[str, float]:
    """Contribution SHAP de chaque variable pour une seule police (x_row :
    une ligne de DataFrame contenant les colonnes FEATURES).
    """
    explainer = shap.TreeExplainer(model.model)
    shap_values = explainer.shap_values(x_row[FEATURES])
    return dict(zip(FEATURES, np.asarray(shap_values)[0].tolist()))


def global_feature_importance(model: XGBoostPricingModel, X: pd.DataFrame) -> dict[str, float]:
    """Importance globale (moyenne des |SHAP|) sur un échantillon, pour
    comparer l'influence des variables à l'échelle du portefeuille.
    """
    explainer = shap.TreeExplainer(model.model)
    shap_values = np.asarray(explainer.shap_values(X[FEATURES]))
    mean_abs = np.abs(shap_values).mean(axis=0)
    return dict(zip(FEATURES, mean_abs.tolist()))
