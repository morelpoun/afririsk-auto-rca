from fastapi.testclient import TestClient

from app.main import app

BASE_CONTRACT = {
    "age_conducteur": 35,
    "anciennete_permis": 15,
    "usage": "particulier",
    "zone": "province",
    "puissance_cv": 8,
    "valeur_vehicule_fcfa": 6_000_000,
    "garantie": "tiers_simple",
    "nb_sinistres_anterieurs": 0,
}


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tarif_returns_coherent_pricing():
    with TestClient(app) as client:
        response = client.post("/tarif", json=BASE_CONTRACT)
    assert response.status_code == 200
    data = response.json()

    assert data["frequence_estimee"] > 0
    assert data["cout_moyen_estime"] > 0
    assert data["prime_pure"] > 0
    assert data["prime_commerciale"] > data["prime_pure"]
    assert set(data["frequence_contributions"]) == {
        "jeune",
        "usage_pro",
        "zone_bangui",
        "nb_sinistres_anterieurs",
        "anciennete_plafonnee",
    }


def test_young_driver_pays_more_all_else_equal():
    with TestClient(app) as client:
        older = client.post("/tarif", json=BASE_CONTRACT).json()
        younger_contract = dict(BASE_CONTRACT, age_conducteur=20, anciennete_permis=2)
        younger = client.post("/tarif", json=younger_contract).json()

    assert younger["prime_commerciale"] > older["prime_commerciale"]


def test_prior_claims_increase_frequency():
    with TestClient(app) as client:
        clean = client.post("/tarif", json=BASE_CONTRACT).json()
        risky_contract = dict(BASE_CONTRACT, nb_sinistres_anterieurs=3)
        risky = client.post("/tarif", json=risky_contract).json()

    assert risky["frequence_estimee"] > clean["frequence_estimee"]


def test_simulate_endpoint_returns_one_point_per_value():
    payload = {
        "contrat_base": BASE_CONTRACT,
        "parametre": "age_conducteur",
        "valeurs": [20, 30, 40, 50, 60],
    }
    with TestClient(app) as client:
        response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["parametre"] == "age_conducteur"
    assert len(data["points"]) == 5
    assert all(p["prime_commerciale"] > 0 for p in data["points"])
