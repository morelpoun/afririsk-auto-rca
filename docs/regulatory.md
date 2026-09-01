# Réglementaire — espace CIMA / RCA

## Pourquoi une couche séparée

Le Code des assurances CIMA impose, pour la RC automobile, un tarif minimum
approuvé État par État (art. 212) et un visa des tarifs par l'autorité de
tutelle (art. 305). La réglementation évolue (le Conseil des ministres CIMA
publie régulièrement des règlements modifiant le Code — par exemple des
règlements 2026). Ces règles ne doivent donc **jamais** être codées en dur
dans le moteur actuariel : elles vivent dans `backend/app/regulatory/`,
versionnées et remplaçables sans toucher au calcul de prime.

## Ce qui est implémenté

- `regulatory/rules.py` : un modèle `RegulatoryRule` (pays, devise, régulateur,
  produit, version réglementaire, dates de validité, tarif minimum optionnel)
  et une fonction `check_minimum_tariff(...)` qui compare la prime calculée au
  minimum configuré, s'il existe.
- `regulatory/countries/cf.py` : la règle pour la RCA (`country="CF"`,
  `product="AUTO_RC"`, `regulator="CIMA"`, `currency="XAF"`).

## Ce qui n'est délibérément pas implémenté

**`minimum_premium` vaut `None`.** Le montant réel du tarif minimum RC auto
approuvé pour la RCA n'a pas été obtenu et validé auprès du régulateur CIMA
dans le cadre de ce projet. Tant que cette valeur reste `None`, le contrôle
réglementaire est toujours `compliant=True` avec un message explicite —
**aucune contrainte n'est simulée avec un chiffre inventé**. Présenter un tarif
calculé uniquement sur données synthétiques comme un tarif officiellement
conforme serait trompeur.

## Comment l'intégrer plus tard

1. Obtenir le texte réglementaire à jour et la valeur du tarif minimum RC auto
   approuvé pour la RCA (et sa devise/date d'entrée en vigueur)
2. Renseigner `minimum_premium`, `effective_from` et `regulatory_version` dans
   `regulatory/countries/cf.py`
3. `check_minimum_tariff` appliquera alors automatiquement la contrainte, sans
   changement dans `main.py` ni dans le moteur actuariel

## Extension à d'autres pays CIMA

Ajouter un nouveau fichier `regulatory/countries/<code>.py` suivant le même
modèle (ex. `cm.py` pour le Cameroun), l'enregistrer via `register_rule(...)`,
et charger ce module au démarrage — comme `cf.load()` l'est aujourd'hui dans
`main.py`. Le moteur actuariel et l'API n'ont pas besoin de connaître le pays
à l'avance : `country`/`product` sont de simples clés de lookup.
