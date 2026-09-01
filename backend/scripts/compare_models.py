"""Compare le GLM fréquence×sévérité de production, un GLM Tweedie et un
XGBoost (objectif Tweedie) sur un même jeu de test, et écrit le résultat dans
app/ml/comparison_results.json (lu par l'endpoint GET /models).

Usage: cd backend && python -m scripts.compare_models
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

from app.actuarial.data_simulation import generate_portfolio
from app.actuarial.pricing import ActuarialEngine, add_derived_features
from app.ml.explain import global_feature_importance
from app.ml.features import prepare_ml_dataset
from app.ml.metrics import mae, normalized_gini, rmse
from app.ml.tweedie import TweedieModel
from app.ml.xgboost_model import XGBoostPricingModel

RESULTS_PATH = Path(__file__).resolve().parents[1] / "app" / "ml" / "comparison_results.json"


def main() -> None:
    portfolio = generate_portfolio(n=15_000, seed=42)
    train_df, test_df = train_test_split(portfolio, test_size=0.3, random_state=42)

    train_enriched = add_derived_features(train_df)
    test_enriched = add_derived_features(test_df)

    X_train, y_train, w_train = prepare_ml_dataset(train_df)
    X_test, y_test, _w_test = prepare_ml_dataset(test_df)
    y_true = y_test.to_numpy()

    # 1. GLM fréquence × sévérité (modèle de production) — comparé sans le
    #    chargement de garantie, qui n'existe pas dans la simulation de
    #    référence, pour une comparaison à périmètre égal.
    engine = ActuarialEngine()
    engine.fit(train_df)
    freq_pred = engine.freq_model.predict(test_enriched, offset=np.log(test_enriched["exposition"]))
    sev_pred = engine.sev_model.predict(test_enriched)
    glm_pred = (freq_pred * sev_pred).to_numpy()

    # 2. GLM Tweedie
    tweedie = TweedieModel().fit(train_enriched)
    tweedie_pred = tweedie.predict(test_enriched)

    # 3. XGBoost (objectif Tweedie)
    xgb_model = XGBoostPricingModel().fit(X_train, y_train, w_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_importance = global_feature_importance(xgb_model, X_test.sample(min(2000, len(X_test)), random_state=42))

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_size": len(portfolio),
        "train_size": len(train_df),
        "test_size": len(test_df),
        "models": [
            {
                "model_id": "GLM_FREQ_SEV_V1",
                "type": "GLM fréquence (Poisson) × sévérité (Gamma)",
                "status": "production",
                "interpretable": True,
                "metrics": {
                    "rmse": rmse(y_true, glm_pred),
                    "mae": mae(y_true, glm_pred),
                    "gini": normalized_gini(y_true, glm_pred),
                },
            },
            {
                "model_id": "TWEEDIE_GLM_V1",
                "type": "GLM Tweedie (coût total direct)",
                "status": "benchmark",
                "interpretable": True,
                "metrics": {
                    "rmse": rmse(y_true, tweedie_pred),
                    "mae": mae(y_true, tweedie_pred),
                    "gini": normalized_gini(y_true, tweedie_pred),
                },
            },
            {
                "model_id": "XGBOOST_TWEEDIE_V1",
                "type": "XGBoost (objectif Tweedie) + SHAP",
                "status": "benchmark",
                "interpretable": False,
                "metrics": {
                    "rmse": rmse(y_true, xgb_pred),
                    "mae": mae(y_true, xgb_pred),
                    "gini": normalized_gini(y_true, xgb_pred),
                },
                "shap_global_importance": xgb_importance,
            },
        ],
    }

    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    print(f"{'Modèle':<20}{'RMSE':>14}{'MAE':>14}{'Gini':>10}")
    for m in results["models"]:
        met = m["metrics"]
        print(f"{m['model_id']:<20}{met['rmse']:>14,.0f}{met['mae']:>14,.0f}{met['gini']:>10.3f}")
    print(f"\nRésultats écrits dans {RESULTS_PATH}")


if __name__ == "__main__":
    main()
