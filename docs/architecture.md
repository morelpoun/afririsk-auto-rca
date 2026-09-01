# Architecture — AfriRisk Auto RCA

## Vue d'ensemble

```text
frontend/            interface statique (formulaire de cotation, dashboard)
      │  fetch() JSON
      ▼
backend/app/
  main.py            routes FastAPI, orchestration
  schemas.py          contrats d'entrée/sortie (Pydantic)
  actuarial/           moteur de tarification
    data_simulation.py   portefeuille synthétique documenté
    pricing.py            GLM fréquence (Poisson) + sévérité (Gamma), décomposition
  regulatory/          couche réglementaire configurable
    rules.py              modèle de règle + contrôle de tarif minimum
    countries/cf.py        paramètres RCA (CIMA)
  database/            persistance
    models.py             customers, vehicles, policies, claims, pricing_results
    session.py             SQLite (dev/tests) ou PostgreSQL (docker-compose)
  ml/                  benchmarks (pas utilisés par /tarif en production)
    tweedie.py             GLM Tweedie
    xgboost_model.py        XGBoost (objectif Tweedie)
    explain.py               explicabilité SHAP
    comparison_results.json  résultat de la dernière comparaison, exposé par GET /models
```

## Principe directeur : le moteur actuariel est séparé de l'API

`main.py` ne calcule jamais de prime lui-même. Il appelle
`ActuarialEngine.price(contrat)` (dans `actuarial/pricing.py`), qui renvoie un
`PricingResult` complet (fréquence, sévérité, prime pure, chargements, prime
commerciale, décomposition explicative). Cela permet de faire évoluer le
moteur (nouveaux modèles, nouvelles branches) sans toucher à l'API, et
inversement.

## Cycle de vie d'une cotation (`POST /tarif`)

1. Validation du contrat entrant (`schemas.ContractInput`)
2. `ActuarialEngine.price(...)` → fréquence, sévérité, prime pure, prime commerciale
3. `regulatory.check_minimum_tariff(...)` → conformité au tarif minimum configuré
   pour (pays, produit), s'il existe
4. Écriture d'une ligne dans `pricing_results` : entrées, sorties, version du
   modèle (`model_version`), version réglementaire appliquée — pour pouvoir
   reconstruire exactement un calcul passé
5. Réponse JSON à l'appelant (frontend ou tout autre client de l'API)

## Persistance

Par défaut, l'application utilise SQLite (`afririsk.db`, fichier local, exclu
du dépôt) — zéro configuration pour développer ou lancer les tests.
`docker-compose.yml` démarre un PostgreSQL réel et positionne `DATABASE_URL`
en conséquence, pour un environnement proche de la production.

Les tables `customers`, `vehicles`, `policies` et `claims` existent déjà dans
le schéma (`database/models.py`) mais ne sont pas encore alimentées par un
workflow de souscription complet — seul `pricing_results` est écrit à chaque
cotation dans ce MVP. Le branchement d'un vrai parcours de souscription
(création client → véhicule → police) est prévu en v0.2/v0.3.

## Modèles benchmark (`ml/`, v0.2)

`ml/tweedie.py` et `ml/xgboost_model.py` (+ `ml/explain.py` pour SHAP) ne sont
**pas** importés par `main.py` : la comparaison se fait hors ligne via
`scripts/compare_models.py`, qui écrit `ml/comparison_results.json`. L'API de
production reste donc légère (pas besoin de `xgboost`/`shap` pour servir
`/tarif`) ; `GET /models` se contente de lire ce fichier JSON s'il existe.
Voir `docs/ml_methodology.md` pour la méthodologie et le résultat de
référence.

## Ce qui n'est pas encore là (volontairement)

- Bonus-malus
- Authentification / RBAC
- Migrations de schéma (Alembic) — pour l'instant `Base.metadata.create_all()`
  au démarrage, suffisant tant que le schéma n'est pas encore stabilisé
- Frontend React/Next.js — l'interface actuelle est volontairement minimale
  (HTML/JS statique) pour rester démontrable sans toolchain supplémentaire

Voir `docs/cahier_des_charges.md` pour la feuille de route complète.
