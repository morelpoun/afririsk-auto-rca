# Méthodologie de comparaison des modèles (v0.2)

## Pourquoi comparer plusieurs approches

Le GLM fréquence×sévérité est interprétable et auditable, ce qui compte en
assurance (justification du tarif, revue par un régulateur). Mais ce n'est
pas la seule approche possible : `scripts/compare_models.py` le compare à un
GLM Tweedie (coût total prédit directement) et à un XGBoost avec objectif
Tweedie, sur le **même** jeu de test.

## Modèles comparés

| Modèle | Description | Interprétable |
|---|---|---|
| `GLM_FREQ_SEV_V1` | Fréquence (Poisson) × sévérité (Gamma) — modèle de production (`/tarif`) | Oui |
| `TWEEDIE_GLM_V1` | GLM Tweedie sur le coût total par police (`var_power=1.5`) | Oui |
| `XGBOOST_TWEEDIE_V1` | XGBoost, objectif `reg:tweedie`, expliqué par SHAP | Non (nécessite SHAP) |

Cible commune : prime pure observée (coût total réel de la police divisé par
son exposition, 0 si aucun sinistre). Split train/test 70/30, mêmes données
pour les trois modèles.

## Métriques

- **RMSE / MAE** : erreur de prédiction sur la prime pure
- **Gini normalisé** : pouvoir de discrimination du risque (capacité à
  classer les mauvais risques au-dessus des bons), implémentation standard
  des compétitions de tarification actuarielle

## Résultat de référence (portefeuille synthétique, seed=42)

```text
Modèle                        RMSE           MAE      Gini
GLM_FREQ_SEV_V1            257 901       122 052     0.310
TWEEDIE_GLM_V1              258 555       122 308     0.286
XGBOOST_TWEEDIE_V1          260 738       117 641     0.219
```

(Mis à jour en v0.5 après l'ajout du facteur taxi-moto à la branche auto,
qui améliore le pouvoir de discrimination du portefeuille pour les trois
modèles — mais davantage pour le GLM, cohérent avec le fait que la donnée
simulée reste générée par une relation log-linéaire.)

Sur ce portefeuille **synthétique** (généré par une relation log-linéaire —
voir `backend/app/actuarial/data_simulation.py`), le GLM fréquence×sévérité
est déjà compétitif, voire légèrement meilleur en Gini que les deux
alternatives. C'est attendu : la donnée de calibration est elle-même
générée par un modèle proche d'un GLM. Ce résultat ne dit donc rien sur ce
qui se passerait sur des données réelles, où des effets non linéaires ou des
interactions pourraient avantager XGBoost — c'est précisément pourquoi ce
benchmark devra être rejoué dès que des données réelles seront disponibles
(phase 4 du cahier des charges), avant de décider de changer de modèle de
production.

## Pourquoi GLM_FREQ_SEV_V1 reste le modèle de production

Comme discuté dans le document de vision initial (comparaison de modèles,
§22) : le meilleur modèle n'est pas automatiquement celui qui a la meilleure
performance brute. L'interprétabilité, la stabilité et l'acceptabilité
réglementaire comptent aussi — un XGBoost, même expliqué par SHAP, reste plus
difficile à justifier ligne par ligne face à un régulateur qu'un GLM dont
chaque coefficient a un sens actuariel direct. Tant que cette analyse n'a pas
été refaite sur données réelles avec un avantage net et robuste pour un
modèle ML, `/tarif` continue à utiliser le GLM.

## Comment rejouer la comparaison

```bash
cd backend
pip install -r requirements-ml.txt
python -m scripts.compare_models
```

Écrit `backend/app/ml/comparison_results.json`, lu par `GET /models`.
