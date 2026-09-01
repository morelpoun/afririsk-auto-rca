# AfriRisk Auto — MVP tarification automobile (RCA)

Moteur de tarification actuarielle pour l'assurance automobile particulière en
République Centrafricaine. Ce MVP expose une API qui calcule une prime pure et
une prime commerciale à partir des caractéristiques d'un contrat, avec des
modèles de fréquence (GLM Poisson) et de sévérité (GLM Gamma) calibrés — pour
l'instant — sur un portefeuille synthétique documenté.

Voir [`docs/cahier_des_charges.md`](docs/cahier_des_charges.md) pour le
périmètre, les hypothèses et la feuille de route complète.

## Installation

```bash
cd afririsk-auto-rca
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l'API

```bash
uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs

## Exemple d'appel

```bash
curl -X POST http://localhost:8000/tarif \
  -H "Content-Type: application/json" \
  -d '{
    "age_conducteur": 28,
    "anciennete_permis": 8,
    "usage": "professionnel",
    "zone": "bangui",
    "puissance_cv": 9,
    "valeur_vehicule_fcfa": 12000000,
    "garantie": "tous_risques",
    "nb_sinistres_anterieurs": 2
  }'
```

La réponse contient la fréquence et le coût moyen estimés, le détail des
chargements (frais, marge, taxes), la prime commerciale finale, ainsi qu'une
décomposition multiplicative par variable expliquant l'écart de fréquence et
de coût moyen par rapport à la moyenne du portefeuille.

`POST /simulate` permet de faire varier un paramètre du contrat (ex :
`age_conducteur`) sur une liste de valeurs et d'obtenir la prime commerciale
correspondante à chaque point, pour tracer une courbe de sensibilité côté
frontend (non inclus dans ce MVP).

## Inspecter la calibration des modèles

```bash
python -m scripts.calibrate
```

Affiche les résumés statsmodels des GLM fréquence/sévérité et un exemple de
tarification complet.

## Tests

```bash
python -m pytest
```

## État du MVP et prochaines étapes

- ✅ Génération de données simulées + moteur actuariel GLM
- ✅ API FastAPI (`/tarif`, `/simulate`)
- ⬜ Frontend (formulaire + graphique de sensibilité)
- ⬜ Calibration sur données réelles d'une compagnie RCA
- ⬜ Extension multi-branches / multi-pays

Voir le cahier des charges pour le détail des hypothèses et des jalons.
