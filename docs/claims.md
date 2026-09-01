# Souscription, sinistres et bonus-malus (v0.6)

## Authentification requise

`POST /policies`, `POST /habitation/policies` et `POST /claims` nécessitent
un compte `admin` ou `agent` (en-tête `Authorization: Bearer <token>`) depuis
la v0.6 voir `docs/auth.md` pour créer un compte et obtenir un jeton. La
lecture (`GET /policies`, `GET /claims`, `GET /portfolio/kpis`) reste
publique pour l'instant (limitation documentée dans `docs/auth.md`).

## Parcours de souscription

`POST /policies` (auto) prend un client, un véhicule et un contrat de
tarification (le même format que `POST /tarif`), calcule la prime avec le
moteur GLM, puis persiste dans l'ordre : `Customer` → `Vehicle` → `Policy` →
`PricingResult` (avec `policy_id` renseigné, contrairement à une cotation
`/tarif` isolée qui n'est rattachée à aucune police). `POST /habitation/policies`
suit exactement le même principe pour la branche habitation, avec un
`Property` (voir `docs/habitation.md`) à la place du véhicule. C'est le lien
`PricingResult.policy_id` qui permet à `GET /portfolio/kpis` de retrouver les
frais chargés à la souscription de chaque police, quelle que soit la branche.

`GET /policies` liste les polices toutes branches confondues (pagination
`limit`/`offset`) `vehicle_id` et `property_id` sont mutuellement exclusifs
selon le produit (`product` : `AUTO_RC` ou `HABITATION_MRH`).

## Sinistres

`POST /claims` déclare un sinistre sur une police existante, auto ou
habitation (404 si `policy_id` n'existe pas) le schéma est générique,
indépendant de la branche. `GET /claims` liste les sinistres, filtrable par
`policy_id`. Le schéma (`database/models.Claim`) porte `claim_amount`,
`paid_amount`, `reserved_amount` et `responsibility` séparément, mais ce MVP
n'utilise pour l'instant que `claim_amount` dans les KPI — la distinction
payé/provisionné devient utile dès qu'un vrai suivi de gestion de sinistres
(règlement progressif) sera ajouté.

## KPI de rentabilité (`GET /portfolio/kpis`)

Calculés sur les polices et sinistres **réellement persistés** (pas le
portefeuille synthétique de calibration utilisé par `/portfolio/metrics`) :

```text
loss_ratio     = sinistres_totaux / primes_totales
expense_ratio  = frais_totaux / primes_totales      (frais_gestion + marge, depuis pricing_results)
combined_ratio = loss_ratio + expense_ratio
```

Renvoie `None` pour les trois ratios tant qu'aucune police n'a été souscrite
(pas de division par zéro silencieuse).

**Attention aux devises (depuis v0.4, multi-pays) :** sans le paramètre
`?country=`, l'agrégat porte sur toutes les polices, quel que soit leur pays
additionner des primes en XAF et en XOF n'a de sens que parce que ces deux
devises sont à parité fixe avec l'EUR ; ce ne serait plus vrai avec le KMF
(Comores). Le champ `currencies` de la réponse liste les devises réellement
incluses : si plusieurs pays ont des polices, préférer filtrer avec
`?country=CF` (ou tout autre code CIMA) pour un total dans une seule devise.

**Attention au mélange de branches (depuis v0.6, habitation) :** de la même
façon, sans `?product=`, l'agrégat mélange polices auto et habitation — deux
sinistralités différentes, un loss ratio combiné n'a pas de sens pour le
pilotage préférer `?product=AUTO_RC` ou `?product=HABITATION_MRH`.

## Peupler des données de démonstration

```bash
cd backend
python -m scripts.seed_database --n 500
```

Génère 500 polices synthétiques (primes calculées par le moteur de
production) et leurs sinistres associés (fréquence/coût issus de la même
simulation que la calibration), pour que le dashboard et `/portfolio/kpis`
aient un contenu réaliste à afficher sans attendre de vraies données
compagnie.

## Bonus-malus

`POST /bonus-malus/compute` prend un historique de sinistres responsables
par année (`[0, 1, 0, 0]`, du plus ancien au plus récent) et renvoie un
coefficient (borné entre 0,50 et 3,50) et une classe indicative. La grille
appliquée (`backend/app/actuarial/bonus_malus.py`) est une **grille par
défaut générique** (−5 %/an sans sinistre, +25 %/sinistre responsable),
**pas** la grille réglementaire CIMA validée pour la RCA chaque réponse le
rappelle explicitement dans son champ `avertissement`.

Le coefficient obtenu se transmet ensuite tel quel dans le champ
`coefficient_bonus_malus` de `ContractInput` (défaut `1.0`), multiplié à la
prime pure comme le chargement de garantie. Le calcul du coefficient et son
application à la tarification sont donc deux étapes séparées et explicites,
jamais automatiques cohérent avec la couche réglementaire (`regulatory/`)
qui suit le même principe de ne rien appliquer sans une valeur validée.
