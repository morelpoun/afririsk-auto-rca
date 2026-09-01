# Authentification et contrôle d'accès (RBAC) — v0.6

## Pourquoi

Jusqu'à la v0.5, n'importe qui pouvait souscrire une police ou déclarer un
sinistre via l'API, sans notion de compte ni de responsabilité. Ce n'est pas
tenable dès que l'outil sort du cadre d'une démonstration : une compagnie a
besoin de savoir **qui** a souscrit quoi.

## Modèle de rôles

Trois rôles fixes, portés par `database/models.User.role` :

| Rôle | Peut |
|---|---|
| `admin` | Tout ce que peut `agent`, + créer des comptes avec un rôle choisi (`POST /auth/users`) |
| `agent` | Souscrire une police (`POST /policies`, `POST /habitation/policies`), déclarer un sinistre (`POST /claims`) |
| `viewer` | Rien de plus qu'un visiteur anonyme pour l'instant (voir limitation ci-dessous) — préparé pour un futur accès en lecture authentifié |

## Bootstrap du premier compte admin

Il n'y a pas d'interface d'administration pour créer le tout premier compte.
`POST /auth/register` est public ; **le tout premier compte créé sur une
instance donnée devient automatiquement `admin`**, tous les suivants sont
créés avec le rôle `agent` par défaut. Un admin peut ensuite créer des
comptes avec un rôle explicite (y compris un autre admin, ou un viewer) via
`POST /auth/users`.

```bash
# Premier compte de l'instance → admin automatiquement
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@compagnie.example", "password": "un-mot-de-passe-solide"}'
```

La réponse contient `access_token` (JWT, valable 8h) et l'utilisateur créé.

## Utiliser le jeton

```bash
curl -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

`GET /auth/me` renvoie le compte associé au jeton fourni (utile pour vérifier
qu'un jeton est encore valide).

## Ce qui est protégé, ce qui ne l'est pas

**Protégé (rôle `admin` ou `agent` requis) :**
- `POST /policies`, `POST /habitation/policies`
- `POST /claims`
- `POST /auth/users` (`admin` uniquement)

**Public, volontairement (v0.6) :**
- `POST /tarif`, `POST /habitation/tarif`, `POST /simulate` — cotation, pas
  d'engagement contractuel, doit rester accessible sans compte (formulaire
  public de tarification)
- `GET /policies`, `GET /claims`, `GET /portfolio/kpis`,
  `GET /portfolio/metrics` — **lecture non protégée pour l'instant**

**Limitation assumée et non résolue :** les données de portefeuille (polices,
sinistres, KPI de rentabilité) restent lisibles par n'importe qui via l'API,
même sans compte. Ce n'est pas un oubli mais un choix de scope pour ne pas
casser le dashboard existant (`frontend/dashboard.html`) sans lui ajouter en
même temps une gestion de session complète. **Ne pas déployer cette version
en environnement où ces données seraient sensibles sans ajouter une
protection en lecture** (`Depends(auth.require_roles(...))` sur les routes
`GET` concernées, puis mettre à jour le dashboard pour transmettre le
jeton) — prévu comme prochain incrément.

## Jeton JWT et secret de signature

`JWT_SECRET_KEY` (variable d'environnement, voir `.env.example`) signe les
jetons (HS256, expiration 8h). Une valeur de développement par défaut est
utilisée si absente — **à changer obligatoirement en production**
(`openssl rand -hex 32`), sinon n'importe qui peut forger un jeton admin
valide.

## Ce qui n'est délibérément pas fait

- Pas de refresh token : le jeton expire après 8h, il faut se reconnecter
- Pas de réinitialisation de mot de passe par email (pas de service d'envoi
  d'email configuré dans ce projet)
- Pas de verrouillage de compte après échecs de connexion répétés
- Pas de scoping des données par compagnie/courtier (`User` n'est pas encore
  rattaché à une organisation) — tous les comptes voient le même portefeuille

Ces limitations sont acceptables pour un MVP à usage interne restreint ; à
traiter avant toute exposition publique à plusieurs compagnies clientes.
