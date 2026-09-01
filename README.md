# AfriRisk — moteur de tarification actuarielle multi-branches CIMA

Moteur de tarification actuarielle pour les 15 États membres de la CIMA,
auto (y compris taxi-moto) et habitation (MRH). L'API calcule une prime pure
et une prime commerciale à partir des caractéristiques d'un contrat, avec des
modèles de fréquence (GLM Poisson) et de sévérité (GLM Gamma) — un moteur par
branche — calibrés pour l'instant sur un portefeuille synthétique documenté
et **partagé par tous les pays** (voir `docs/regulatory.md` — aucune donnée
réelle ne permet encore de différencier le risque par pays), une couche
réglementaire et une devise configurables par pays, et une traçabilité
complète de chaque cotation.

Voir [`docs/cahier_des_charges.md`](docs/cahier_des_charges.md) (périmètre,
hypothèses, feuille de route), [`docs/architecture.md`](docs/architecture.md),
[`docs/regulatory.md`](docs/regulatory.md) (couche réglementaire CIMA),
[`docs/ml_methodology.md`](docs/ml_methodology.md) (comparaison GLM / Tweedie
/ XGBoost+SHAP), [`docs/claims.md`](docs/claims.md) (souscription, sinistres,
bonus-malus, KPI de rentabilité — branche auto) et
[`docs/habitation.md`](docs/habitation.md) (branche habitation).

## Démarrage rapide avec Docker (recommandé)

```bash
docker compose up --build
```

- API + interface : http://localhost:8000/app/index.html
- Documentation interactive : http://localhost:8000/docs
- PostgreSQL est démarré automatiquement (`docker-compose.yml`)

## Installation manuelle (sans Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Sans variable `DATABASE_URL`, l'application utilise SQLite en local
(`backend/afririsk.db`, non versionné) — zéro configuration nécessaire pour
développer. Copier `.env.example` en `.env` pour pointer vers un PostgreSQL
existant si besoin.

## Interface

- `http://localhost:8000/app/index.html` — formulaire de cotation
- `http://localhost:8000/app/dashboard.html` — KPI du portefeuille synthétique

## Exemple d'appel API

```bash
curl -X POST http://localhost:8000/tarif \
  -H "Content-Type: application/json" \
  -d '{
    "country": "CF",
    "age_conducteur": 28,
    "anciennete_permis": 8,
    "usage": "professionnel",
    "zone": "urbain",
    "puissance_cv": 9,
    "valeur_vehicule_fcfa": 12000000,
    "garantie": "tous_risques",
    "nb_sinistres_anterieurs": 2
  }'
```

`GET /countries` liste les 15 pays CIMA supportés (code, devise, zone
monétaire). La réponse de `/tarif` contient la fréquence et le coût moyen
estimés, le détail des chargements (frais, marge, taxes), la prime
commerciale finale dans la devise du pays, une décomposition multiplicative
par variable expliquant l'écart par rapport à la moyenne du portefeuille, le
résultat du contrôle réglementaire (tarif minimum CIMA du pays — non
contraignant tant qu'aucune valeur validée n'est configurée, voir
`docs/regulatory.md`), et l'identifiant de la cotation persistée.

`POST /simulate` fait varier un paramètre du contrat sur une liste de valeurs
et renvoie la prime commerciale à chaque point (courbe de sensibilité).
`GET /portfolio/metrics` renvoie les KPI agrégés du portefeuille synthétique.

## Branche habitation (MRH)

`POST /habitation/tarif` et `POST /habitation/simulate` — même principe que
l'auto, moteur de tarification séparé (voir `docs/habitation.md`). Pas
encore de souscription de police ni de sinistres pour cette branche.

```bash
curl -X POST http://localhost:8000/habitation/tarif \
  -H "Content-Type: application/json" \
  -d '{
    "country": "CF",
    "type_logement": "maison",
    "zone": "urbain",
    "surface_m2": 120,
    "materiaux_construction": "semi_dur",
    "valeur_batiment": 15000000,
    "valeur_contenu": 3000000,
    "anciennete_batiment": 15,
    "securite": false,
    "nb_sinistres_anterieurs": 0,
    "garantie": "multirisque"
  }'
```

## Souscription, sinistres et bonus-malus

`POST /policies` souscrit une police (client + véhicule + contrat tarifé) ;
`POST /claims` déclare un sinistre ; `GET /portfolio/kpis` calcule loss ratio,
expense ratio et combined ratio sur les données réellement persistées.
`POST /bonus-malus/compute` calcule un coefficient à partir d'un historique de
sinistres (grille par défaut, **non validée CIMA** — voir `docs/claims.md`).

```bash
cd backend && python -m scripts.seed_database --n 500
```

Peuple la base avec des polices/sinistres synthétiques réalistes pour donner
du contenu au dashboard et à `/portfolio/kpis` sans attendre de vraies
données compagnie.

## Inspecter la calibration des modèles

```bash
cd backend && python -m scripts.calibrate
```

Affiche les résumés statsmodels des GLM fréquence/sévérité et un exemple de
tarification complet.

## Comparer GLM, Tweedie et XGBoost+SHAP

`/tarif` utilise uniquement le GLM fréquence×sévérité, choisi pour son
interprétabilité. Deux benchmarks (GLM Tweedie, XGBoost+SHAP) sont comparés
hors production — voir `docs/ml_methodology.md` pour la méthodologie et les
résultats de référence :

```bash
cd backend
pip install -r requirements-ml.txt   # xgboost, shap, scikit-learn — pas nécessaire pour l'API
python -m scripts.compare_models
```

Écrit `backend/app/ml/comparison_results.json`, exposé par `GET /models`.

## Tests

```bash
cd backend && python -m pytest
```

## État du MVP et prochaines étapes

- ✅ Génération de données simulées + moteur actuariel GLM (fréquence/sévérité)
- ✅ API FastAPI (`/tarif`, `/simulate`, `/portfolio/metrics`)
- ✅ Persistance PostgreSQL + traçabilité de chaque cotation
- ✅ Couche réglementaire et devise configurables par pays CIMA
- ✅ Interface de tarification et dashboard minimalistes
- ✅ Benchmarks Tweedie / XGBoost + SHAP comparés au GLM de production (v0.2)
- ✅ Bonus-malus, souscription/sinistres, KPI de rentabilité réels (v0.3)
- ✅ Extension aux 15 pays CIMA — réglementaire/devise par pays, modèle de
  risque encore partagé (v0.4, voir `docs/regulatory.md`)
- ✅ Taxi-moto (auto) et branche habitation MRH — moteur de tarification
  complet, pas encore souscription/sinistres (v0.5, voir `docs/habitation.md`)
- ⬜ Authentification/RBAC, frontend React/Next.js complet, facturation SaaS
- ⬜ Calibration du risque par pays sur données réelles
- ⬜ Santé et vie (paradigmes actuariels différents de l'habitation — voir
  `docs/cahier_des_charges.md` §10)

Voir le cahier des charges pour le détail des hypothèses et des jalons.
