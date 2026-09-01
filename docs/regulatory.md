# Réglementaire — espace CIMA (15 États membres)

## Pourquoi une couche séparée

Le Code des assurances CIMA impose, pour la RC automobile, un tarif minimum
approuvé État par État (art. 212) et un visa des tarifs par l'autorité de
tutelle (art. 305). La réglementation évolue (le Conseil des ministres CIMA
publie régulièrement des règlements modifiant le Code par exemple des
règlements 2026). Ces règles ne doivent donc **jamais** être codées en dur
dans le moteur actuariel : elles vivent dans `backend/app/regulatory/`,
versionnées et remplaçables sans toucher au calcul de prime.

## Décision de conception (v0.4) : un seul moteur de risque pour 15 pays

Depuis v0.4, l'API accepte un contrat pour n'importe lequel des 15 États
membres de la CIMA (`GET /countries`). **Le moteur de risque
(`ActuarialEngine`, fréquence/sévérité GLM) reste unique et partagé par tous
ces pays** — il n'existe pas 15 modèles calibrés séparément.

Ce n'est pas un raccourci technique paresseux : c'est le choix honnête compte
tenu des données disponibles. Ce projet n'a **aucune donnée réelle** par pays
qui permettrait de dire que le risque auto au Cameroun diffère de celui du
Congo ou du Sénégal, ni dans quelle mesure. Inventer des coefficients de
risque différents par pays donnerait une **fausse impression de précision**
pire qu'admettre franchement qu'un seul modèle démonstratif (calibré sur les
hypothèses RCA, voir `docs/cahier_des_charges.md`) est utilisé partout en
attendant des données réelles par marché.

Ce qui *varie* réellement par pays :
- la **couche réglementaire** (tarif minimum CIMA, quand il sera configuré)
- la **devise** (XAF/XOF/KMF selon la zone monétaire, voir
  `regulatory/cima_countries.py`)
- l'**identité du contrat** (à quel État il est administrativement rattaché)

Ce qui ne varie *pas* (encore) :
- la fréquence et la sévérité prédites pour un même profil de risque, quel
  que soit le pays sélectionné

## Ce qui est implémenté

- `regulatory/rules.py` : un modèle `RegulatoryRule` (pays, devise, régulateur,
  produit, version réglementaire, dates de validité, tarif minimum optionnel)
  et une fonction `check_minimum_tariff(...)` qui compare la prime calculée au
  minimum configuré, s'il existe.
- `regulatory/cima_countries.py` : la table des 15 États membres CIMA (code,
  nom, devise, zone monétaire UEMOA/CEMAC), la liste des produits supportés
  (`PRODUCTS` : `AUTO_RC`, `HABITATION_MRH`) et `load_all_regulatory_rules()`
  qui enregistre une règle par (pays, produit) — une nouvelle branche n'a
  besoin que d'ajouter son code produit à `PRODUCTS`.

## Ce qui n'est délibérément pas implémenté

**`minimum_premium` vaut `None` pour les 15 pays.** Aucun tarif minimum RC
auto n'a été obtenu et validé auprès du régulateur CIMA dans le cadre de ce
projet, pour aucun pays. Tant que cette valeur reste `None`, le contrôle
réglementaire est toujours `compliant=True` avec un message explicite
**aucune contrainte n'est simulée avec un chiffre inventé**. Présenter un tarif
calculé uniquement sur données synthétiques comme un tarif officiellement
conforme serait trompeur, quel que soit le pays.

## Comment intégrer un vrai tarif minimum plus tard

1. Obtenir le texte réglementaire à jour et la valeur du tarif minimum RC auto
   approuvé pour le pays concerné (et sa devise/date d'entrée en vigueur)
2. Renseigner `minimum_premium` pour ce pays dans
   `regulatory/cima_countries.py` (ou l'extraire dans une table de
   configuration externe si les valeurs commencent à être nombreuses)
3. `check_minimum_tariff` appliquera alors automatiquement la contrainte, sans
   changement dans `main.py` ni dans le moteur actuariel

## Comment calibrer un vrai modèle de risque par pays plus tard

Quand des données réelles seront disponibles pour un pays donné :
1. Générer/charger un portefeuille spécifique à ce pays au lieu du
   portefeuille synthétique partagé (`actuarial/data_simulation.py`)
2. Faire tourner un `ActuarialEngine` distinct par pays (au lieu de l'instance
   unique actuelle dans `app.state.engine`), et sélectionner l'engine à
   utiliser selon `contract.country` dans `main.py`
3. Documenter la source des données et la date de calibration dans
   `docs/ml_methodology.md`, pays par pays

Tant que cette étape n'a pas été faite, ne jamais présenter une prime
calculée par ce MVP comme calibrée sur le marché réel d'un pays autre que
« démonstration ».
