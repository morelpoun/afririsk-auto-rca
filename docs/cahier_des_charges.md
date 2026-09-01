# Cahier des charges "AfriRisk" (tarification multi-branches CIMA)

## 1. Objectif
Fournir un outil permettant à un assureur ou courtier des 15 États membres de
la CIMA de saisir les caractéristiques d'un contrat (auto, puis habitation)
et d'obtenir instantanément une prime pure et une prime commerciale,
calculées par un moteur actuariel transparent et explicable.

## 2. Périmètre

**Dans le périmètre :**
- Deux branches : assurance automobile particulière (y compris taxi-moto) et
  multirisque habitation (MRH) voir `docs/habitation.md`. Auto a le cycle
  de vie complet (souscription, sinistres, KPI) ; habitation n'a pour
  l'instant que le moteur de tarification (`POST /habitation/tarif`)
- Les 15 États membres de la CIMA, avec **un seul modèle de risque partagé
  par branche** (voir `docs/regulatory.md`) seuls la devise et le contrôle
  réglementaire varient par pays, pas encore le risque lui-même faute de
  données réelles par marché
- Pour l'auto : calcul de prime à la souscription, souscription de polices,
  déclaration de sinistres et KPI de rentabilité (loss/expense/combined
  ratio) pas de provisionnement actuariel des sinistres (IBNR, triangles)
- Données simulées, calibrées sur des hypothèses de marché documentées et ajustables

**Hors périmètre (phases suivantes) :**
- Santé et vie (voir §10) pour pourquoi elles ne sont pas traitées comme
  l'habitation (paradigmes actuariels différents)
- Cycle de vie complet (souscription/sinistres/KPI) pour l'habitation
- Calibration du risque par pays sur données réelles (voir `docs/regulatory.md`)
- Scoring fraude, provisionnement (IBNR), MLflow (registre de modèles versionné)
- Authentification/RBAC
- Frontend React/Next.js aboutissant (le MVP a une interface statique minimale,
  voir §7)
- Données réelles compagnie (phase 4)
- Facturation SaaS avec encaissement réel (prestataire de paiement à choisir)

## 3. Utilisateur cible
Chargé de tarification / souscripteur dans une compagnie ou un courtier. L'API est
conçue pour être appelée par une interface simple, sans connaissances en data
science requises côté utilisateur final.

## 4. Variables d'entrée
- Pays : un des 15 États membres CIMA (`GET /countries`)
- Conducteur : âge, sexe, ancienneté du permis
- Véhicule : puissance (CV), année de mise en circulation, valeur assurée
  (devise du pays sélectionné)
- Contexte : zone urbaine (capitale/grande ville) ou rurale, usage (particulier
  / professionnel / taxi-moto), nombre d'années assuré, nombre de sinistres
  antérieurs
- Garantie : tiers simple / tiers étendu / tous risques

Pour l'habitation, voir `docs/habitation.md`.

## 5. Moteur actuariel
- **Fréquence de sinistre** : GLM Poisson (offset = exposition), variables ci-dessus
  comme régresseurs
- **Coût moyen par sinistre** : GLM Gamma (lien log)
- **Prime pure** = fréquence estimée × coût moyen estimé
- **Prime commerciale** = prime pure + chargement frais généraux + marge technique
  + taxes réglementaires (hypothèses RCA/CIMA, à valider)
- **Explicabilité** : décomposition multiplicative de la prédiction GLM par variable,
  pour expliquer pourquoi la prime d'un assuré est plus ou moins élevée que la
  moyenne du portefeuille

## 6. Données v1
Portefeuille synthétique généré avec des relations réalistes documentées dans le
code (`backend/app/actuarial/data_simulation.py`) : conducteurs jeunes et zone
urbaine plus risqués, sinistralité antérieure comme facteur aggravant, coût
moyen lié à la valeur du véhicule et à la zone. Ces hypothèses sont des points
de départ démonstratifs, à recalibrer sur données réelles en phase 4.

## 7. Architecture technique (MVP actuel)
- Backend : Python + FastAPI, structuré en sous-modules `actuarial/`
  (fréquence/sévérité/prime/bonus-malus), `regulatory/` (règles CIMA
  configurables par pays), `database/` (persistance + CRUD polices/sinistres)
  et `ml/` (benchmarks Tweedie/XGBoost, hors production voir §6 v0.2)
- Moteur actuariel : pandas, numpy, statsmodels (GLM Poisson / Gamma)
- Persistance : PostgreSQL via `docker-compose` (SQLite en développement/tests
  sans configuration). Chaque tarification est tracée dans `pricing_results`
  (entrées, modèle, version réglementaire) pour pouvoir reconstruire un calcul
  passé — voir `docs/architecture.md`
- Réglementaire : couche `regulatory/` configurable par (pays, produit), voir
  `docs/regulatory.md` table des 15 pays CIMA (`cima_countries.py`), tarif
  minimum non codé en dur tant qu'il n'a pas été obtenu et validé auprès du
  régulateur, pour aucun pays
- Frontend : interface statique minimale (`frontend/index.html` formulaire de
  cotation, `frontend/dashboard.html` KPI portefeuille), servie par FastAPI en
  HTML/JS vanilla un frontend React/Next.js plus riche reste une évolution
  possible, pas un prérequis du MVP

## 8. Jalons
1. ✅ Hypothèses de tarification + génération de données simulées + moteur GLM
2. ✅ API FastAPI (`/tarif`, `/simulate`, `/portfolio/metrics`) testable via Swagger
3. ✅ Persistance PostgreSQL + traçabilité de chaque cotation
4. ✅ Couche réglementaire configurable (CIMA/RCA)
5. ✅ Interface de tarification et dashboard minimalistes
6. ✅ Modèles Tweedie / XGBoost + SHAP, comparaison de modèles (v0.2, voir
   `docs/ml_methodology.md`) le GLM fréquence×sévérité reste le modèle de
   production ; les alternatives sont des benchmarks, pas encore justifiées
   par un gain net sur données réelles
7. ✅ Bonus-malus, gestion des sinistres, KPI de rentabilité (v0.3, voir
   `docs/claims.md`) grille bonus-malus par défaut non validée CIMA,
   souscription de polices (`POST /policies`), sinistres (`POST /claims`),
   loss/expense/combined ratio (`GET /portfolio/kpis`)
8. ⬜ Partenariat avec une compagnie RCA pour données réelles anonymisées et
   recalibration des modèles
9. ✅ Extension sous-régionale aux 15 pays CIMA (v0.4, voir `docs/regulatory.md`)
   — réglementaire et devise par pays ; modèle de risque encore partagé,
   calibration par pays hors périmètre tant que des données réelles ne sont
   pas disponibles
10. ⬜ Authentification/RBAC, frontend React/Next.js complet, facturation SaaS
11. 🟡 Extension multi-branches (v0.5, voir `docs/habitation.md`) — habitation
    (MRH) livrée avec moteur de tarification complet (fréquence×sévérité,
    explicabilité) et taxi-moto ajouté à la branche auto ; souscription/
    sinistres/KPI habitation, santé et vie restent à faire (§10 explique
    pourquoi santé et vie ne sont pas traitées de la même manière)

## 10. Pourquoi santé et vie ne sont pas traitées comme l'habitation
L'habitation a pu être ajoutée comme un second incrément direct de l'auto
parce qu'elle suit le **même paradigme actuariel** : fréquence de sinistre ×
sévérité, modélisée par GLM Poisson/Gamma sur des facteurs de risque
observables à la souscription. Santé et vie sont différentes :

- **Vie** repose sur des **tables de mortalité/survie**, pas sur une
  fréquence de sinistre au sens habituel il s'agit de modéliser la
  probabilité de décès par âge et d'actualiser des flux futurs (valeur
  actuelle probable des prestations), un outillage mathématique distinct
  (tables actuarielles, taux technique, provisions mathématiques) qui
  mériterait son propre moteur plutôt qu'une adaptation du moteur
  fréquence×sévérité existant.
- **Santé** est actuariellement plus proche du paradigme fréquence×sévérité,
  mais soulève des enjeux supplémentaires : données médicales (sensibilité
  et réglementation sur les données de santé), réseaux de soins et tarifs
  conventionnés propres à chaque pays, sélection adverse et anti-sélection à
  gérer explicitement un périmètre qui mérite d'être cadré avant de coder,
  pas improvisé dans le même mouvement que l'habitation.

Ces deux branches restent donc de futurs incréments séparés, chacun avec sa
propre conception, plutôt que des variantes rapides du moteur auto/habitation.

## 11. Risques principaux
- Sans données réelles, le modèle reste démonstratif une mise en production
  nécessite une calibration sur les données d'une vraie compagnie
- Le même modèle de risque est utilisé pour les 15 pays CIMA (voir
  `docs/regulatory.md`) : ne jamais présenter une prime calculée hors RCA
  comme calibrée sur le marché réel de ce pays
- Cadre réglementaire CIMA à valider pays par pays pour les tarifs minimums,
  chargements et taxes
- Disponibilité de référentiels véhicules/zones fiables par pays
