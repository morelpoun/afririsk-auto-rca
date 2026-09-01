"""Métriques de comparaison de modèles de prime pure."""
from __future__ import annotations

import numpy as np


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def normalized_gini(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Indice de Gini normalisé (pouvoir de discrimination du risque),
    implémentation standard utilisée dans les compétitions de tarification
    actuarielle (classement des polices par prédiction décroissante, puis
    aire entre la courbe de Lorenz et la diagonale).
    """

    def _gini(actual: np.ndarray, pred: np.ndarray) -> float:
        n = len(actual)
        data = np.c_[actual, pred, np.arange(n)]
        order = np.lexsort((data[:, 2], -data[:, 1]))
        data = data[order]
        total_losses = data[:, 0].sum()
        if total_losses == 0:
            return 0.0
        cumulative = data[:, 0].cumsum().sum() / total_losses
        cumulative -= (n + 1) / 2.0
        return cumulative / n

    denom = _gini(y_true, y_true)
    if denom == 0:
        return 0.0
    return _gini(y_true, y_pred) / denom
