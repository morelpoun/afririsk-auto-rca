# Branche habitation (multirisque habitation / MRH) v0.6

## Périmètre

Deuxième branche d'assurance, après l'auto. Même architecture actuarielle
(GLM fréquence Poisson + sévérité Gamma, décomposition explicative,
chargements commerciaux, contrôle réglementaire par pays) appliquée à des
facteurs de risque habitation plutôt qu'automobile voir
`backend/app/actuarial/habitation_pricing.py` et
`habitation_data_simulation.py`.

**Depuis v0.6, le cycle de vie est complet** : `POST /habitation/tarif` et
`POST /habitation/simulate` pour la cotation (comme depuis la v0.5), et
`POST /habitation/policies` pour la souscription — même principe que
`POST /policies` pour l'auto (voir `docs/claims.md`), avec un `Property`
(`database/models.Property`, pendant de `Vehicle`) plutôt qu'un véhicule.
Les sinistres réutilisent `POST /claims` tel quel (générique par
`policy_id`, indépendant de la branche). `GET /portfolio/kpis` agrège donc
déjà les polices habitation avec les polices auto tant que
`?country=` (ou une vraie séparation par produit) n'est pas ajouté pour les
isoler — voir la limite ci-dessous.

**Souscription protégée par authentification** (rôle `admin` ou `agent`,
voir `docs/auth.md`) — comme la souscription auto.

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

## Souscription et sinistres

```bash
curl -X POST http://localhost:8000/habitation/policies \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {"first_name": "Aïcha", "last_name": "Doumbia", "birth_date": "1985-02-15", "gender": "F"},
    "property": {
      "type_logement": "maison", "zone": "urbain", "surface_m2": 120,
      "materiaux_construction": "semi_dur", "valeur_batiment": 15000000,
      "valeur_contenu": 3000000, "anciennete_batiment": 15, "securite": false
    },
    "contract": { "...": "même corps que POST /habitation/tarif" },
    "start_date": "2026-01-01", "end_date": "2026-12-31"
  }'
```

`POST /claims` (voir `docs/claims.md`) fonctionne tel quel pour un
`policy_id` habitation, aucune adaptation nécessaire — le modèle `Claim` est
générique par police.

**Attention :** `GET /portfolio/kpis` agrège par défaut polices auto et
habitation ensemble (elles partagent la même table `policies`). Un loss
ratio mélangeant deux branches à la sinistralité très différente est
trompeur pour le pilotage utiliser `?product=AUTO_RC` ou
`?product=HABITATION_MRH` (ajouté en v0.6) dès qu'un vrai usage
multi-branches apparaît, comme `?country=` pour les devises.
