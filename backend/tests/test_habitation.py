from fastapi.testclient import TestClient

from app.main import app

BASE_HABITATION_CONTRACT = {
    "country": "CF",
    "type_logement": "maison",
    "zone": "rural",
    "surface_m2": 90,
    "materiaux_construction": "dur",
    "valeur_batiment": 10_000_000,
    "valeur_contenu": 2_000_000,
    "anciennete_batiment": 10,
    "securite": True,
    "nb_sinistres_anterieurs": 0,
    "garantie": "incendie_simple",
}


def test_habitation_tarif_returns_coherent_pricing():
    with TestClient(app) as client:
        response = client.post("/habitation/tarif", json=BASE_HABITATION_CONTRACT)
    assert response.status_code == 200
    data = response.json()

    assert data["frequence_estimee"] > 0
    assert data["cout_moyen_estime"] > 0
    assert data["prime_pure"] > 0
    assert data["prime_commerciale"] > data["prime_pure"]
    assert data["model_version"] == "GLM_FREQ_SEV_HABITATION_V1"
    assert data["currency"] == "XAF"
    assert data["pricing_result_id"] is not None
    assert set(data["frequence_contributions"]) == {
        "materiaux_precaire",
        "materiaux_semi_dur",
        "zone_urbain",
        "sans_securite",
        "anciennete_plafonnee",
        "nb_sinistres_anterieurs",
    }


def test_precarious_construction_increases_frequency():
    with TestClient(app) as client:
        dur = client.post("/habitation/tarif", json=BASE_HABITATION_CONTRACT).json()
        precaire_contract = dict(BASE_HABITATION_CONTRACT, materiaux_construction="precaire")
        precaire = client.post("/habitation/tarif", json=precaire_contract).json()

    assert precaire["frequence_estimee"] > dur["frequence_estimee"]


def test_no_security_increases_premium():
    with TestClient(app) as client:
        secure = client.post("/habitation/tarif", json=BASE_HABITATION_CONTRACT).json()
        insecure_contract = dict(BASE_HABITATION_CONTRACT, securite=False)
        insecure = client.post("/habitation/tarif", json=insecure_contract).json()

    assert insecure["prime_commerciale"] > secure["prime_commerciale"]


def test_multirisque_garantie_costs_more_than_incendie_simple():
    with TestClient(app) as client:
        simple = client.post("/habitation/tarif", json=BASE_HABITATION_CONTRACT).json()
        multirisque_contract = dict(BASE_HABITATION_CONTRACT, garantie="multirisque")
        multirisque = client.post("/habitation/tarif", json=multirisque_contract).json()

    assert multirisque["prime_commerciale"] > simple["prime_commerciale"]


def test_habitation_simulate_endpoint_returns_one_point_per_value():
    payload = {
        "contrat_base": BASE_HABITATION_CONTRACT,
        "parametre": "valeur_batiment",
        "valeurs": [5_000_000, 10_000_000, 20_000_000, 40_000_000],
    }
    with TestClient(app) as client:
        response = client.post("/habitation/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["parametre"] == "valeur_batiment"
    assert len(data["points"]) == 4
    assert all(p["prime_commerciale"] > 0 for p in data["points"])
    # Prime croissante avec la valeur assurée
    premiums = [p["prime_commerciale"] for p in data["points"]]
    assert premiums == sorted(premiums)
