# Cahier des charges — MVP "AfriRisk Auto" (tarification auto RCA)

## 1. Objectif
Fournir un outil permettant à un assureur ou courtier centrafricain de saisir les
caractéristiques d'un contrat auto et d'obtenir instantanément une prime pure et
une prime commerciale, calculées par un moteur actuariel transparent et explicable.

## 2. Périmètre du MVP

**Dans le périmètre :**
- Une seule branche : assurance automobile particulière (hors flottes, hors taxis)
- Un seul pays : République Centrafricaine (RCA)
- Calcul de prime à la souscription (pas de gestion de sinistres, pas de provisionnement)
- Données simulées, calibrées sur des hypothèses de marché documentées et ajustables

**Hors périmètre (phases suivantes) :**
- Autres branches (santé, habitation, vie...)
- Autres pays (l'architecture le permet — voir `docs/regulatory.md` — mais seule
  la RCA est configurée)
- Bonus-malus, scoring fraude, modèles Tweedie/ML (XGBoost) + SHAP, MLflow
- Authentification/RBAC
- Frontend React/Next.js aboutissant (le MVP a une interface statique minimale,
  voir §7)
- Données réelles compagnie (phase 4)

## 3. Utilisateur cible
Chargé de tarification / souscripteur dans une compagnie ou un courtier. L'API est
conçue pour être appelée par une interface simple, sans connaissances en data
science requises côté utilisateur final.

## 4. Variables d'entrée (v1)
- Conducteur : âge, sexe, ancienneté du permis
- Véhicule : puissance (CV), année de mise en circulation, valeur assurée (FCFA)
- Contexte : zone géographique (Bangui / province), usage (particulier / professionnel),
  nombre d'années assuré, nombre de sinistres antérieurs
- Garantie : tiers simple / tiers étendu / tous risques

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
  (fréquence/sévérité/prime), `regulatory/` (règles CIMA configurables par
  pays) et `database/` (persistance)
- Moteur actuariel : pandas, numpy, statsmodels (GLM Poisson / Gamma)
- Persistance : PostgreSQL via `docker-compose` (SQLite en développement/tests
  sans configuration). Chaque tarification est tracée dans `pricing_results`
  (entrées, modèle, version réglementaire) pour pouvoir reconstruire un calcul
  passé — voir `docs/architecture.md`
- Réglementaire : couche `regulatory/` configurable par (pays, produit), voir
  `docs/regulatory.md` — le tarif minimum CIMA/RCA n'est pas codé en dur tant
  qu'il n'a pas été obtenu et validé auprès du régulateur
- Frontend : interface statique minimale (`frontend/index.html` formulaire de
  cotation, `frontend/dashboard.html` KPI portefeuille), servie par FastAPI en
  HTML/JS vanilla — un frontend React/Next.js plus riche reste une évolution
  possible, pas un prérequis du MVP

## 8. Jalons
1. ✅ Hypothèses de tarification + génération de données simulées + moteur GLM
2. ✅ API FastAPI (`/tarif`, `/simulate`, `/portfolio/metrics`) testable via Swagger
3. ✅ Persistance PostgreSQL + traçabilité de chaque cotation
4. ✅ Couche réglementaire configurable (CIMA/RCA)
5. ✅ Interface de tarification et dashboard minimalistes
6. ⬜ Modèles Tweedie / ML (XGBoost) + explicabilité SHAP, comparaison de modèles
7. ⬜ Bonus-malus, gestion des sinistres, KPI de rentabilité (loss/combined ratio)
8. ⬜ Partenariat avec une compagnie RCA pour données réelles anonymisées et
   recalibration des modèles
9. ⬜ Extension multi-branches / multi-pays (Cameroun, Gabon, ...)

## 9. Risques principaux
- Sans données réelles, le modèle reste démonstratif — une mise en production
  nécessite une calibration sur les données d'une vraie compagnie
- Cadre réglementaire assurance RCA (CIMA) à valider pour les chargements et taxes
- Disponibilité de référentiels véhicules/zones RCA fiables
