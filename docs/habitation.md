# Branche habitation (multirisque habitation / MRH) v0.5

## Périmètre

Deuxième branche d'assurance, après l'auto. Même architecture actuarielle
(GLM fréquence Poisson + sévérité Gamma, décomposition explicative,
chargements commerciaux, contrôle réglementaire par pays) appliquée à des
facteurs de risque habitation plutôt qu'automobile voir
`backend/app/actuarial/habitation_pricing.py` et
`habitation_data_simulation.py`.

**v0.5 livre le moteur de tarification (`POST /habitation/tarif`,
`POST /habitation/simulate`) mais pas encore le cycle de vie complet**
(souscription de police, sinistres, KPI de rentabilité) que l'auto a depuis
la v0.3 voir `docs/claims.md`. Étendre `POST /policies` à l'habitation est
une extension naturelle mais non triviale (le schéma `PolicySubscriptionRequest`
est aujourd'hui typé pour un contrat auto) : prévu comme prochain incrément
si cette branche est utilisée.

## Variables d'entrée

- Pays CIMA (même liste que l'auto)
- Type de logement : maison / appartement
- Zone : urbaine (capitale/grande ville) ou rurale
- Surface (m²)
- Matériaux de construction : dur (béton/parpaings), semi-dur, précaire
- Valeur assurée du bâtiment et du contenu (devise du pays)
- Ancienneté du bâtiment
- Présence d'un gardiennage/alarme
- Nombre de sinistres antérieurs
- Garantie : incendie simple ou multirisque

## Hypothèses de risque (démonstration, pas des statistiques réelles)

Comme pour l'auto, ces hypothèses sont documentées dans le code
(`habitation_data_simulation.py`) et partagées par tous les pays CIMA faute
de données réelles par pays même avertissement que `docs/regulatory.md`.

- Construction précaire : risque incendie/effondrement nettement plus élevé
  (+90 % de fréquence), mais coût de reconstruction par sinistre plus faible
  (matériaux moins chers)
- Zone urbaine : risque de vol plus élevé
- Absence de sécurité (gardiennage/alarme) : risque de vol plus élevé
- Bâtiment ancien : risque accru (installations électriques/plomberie
  vieillissantes), effet plafonné à 40 ans
- Sévérité : proportionnelle à la valeur du bâtiment et du contenu assurés

**Simplification assumée :** un seul type de sinistre "habitation" simulé
(incendie + vol + dégât des eaux combinés), pas décomposé par péril comme le
ferait un vrai contrat multirisque. Une évolution future pourrait modéliser
chaque péril séparément (fréquence/sévérité propres à l'incendie, au vol, au
dégât des eaux).

## Exemple d'appel

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
