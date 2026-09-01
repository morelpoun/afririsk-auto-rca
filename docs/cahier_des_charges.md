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
- Autres pays
- Bonus-malus historique réel, scoring fraude, provisions techniques
- Données réelles compagnie (phase 4)
- Interface web (frontend React) — le MVP actuel expose une API

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
code (`app/data_simulation.py`) : conducteurs jeunes et zone urbaine plus
risqués, sinistralité antérieure comme facteur aggravant, coût moyen lié à la
valeur du véhicule et à la zone. Ces hypothèses sont des points de départ
démonstratifs, à recalibrer sur données réelles en phase 4.

## 7. Architecture technique (MVP actuel)
- Backend : Python + FastAPI
- Moteur actuariel : pandas, numpy, statsmodels (GLM Poisson / Gamma)
- Pas de base de données en v1 : portefeuille simulé généré et les modèles
  ajustés au démarrage de l'application (volume réduit, calcul rapide)
- Frontend : non inclus dans ce MVP (prochaine phase)

## 8. Jalons
1. ✅ Hypothèses de tarification + génération de données simulées + moteur GLM
2. ✅ API FastAPI (`/tarif`, `/simulate`) testable via Swagger
3. ⬜ Frontend (formulaire de saisie + graphique de sensibilité)
4. ⬜ Partenariat avec une compagnie RCA pour données réelles anonymisées et
   recalibration des modèles
5. ⬜ Extension multi-branches / multi-pays

## 9. Risques principaux
- Sans données réelles, le modèle reste démonstratif — une mise en production
  nécessite une calibration sur les données d'une vraie compagnie
- Cadre réglementaire assurance RCA (CIMA) à valider pour les chargements et taxes
- Disponibilité de référentiels véhicules/zones RCA fiables
