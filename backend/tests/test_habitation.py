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


def test_habitation_policy_subscription_and_claim_flow(agent_headers):
    payload = {
        "customer": {
            "first_name": "Aïcha",
            "last_name": "Test",
            "birth_date": "1985-02-15",
            "gender": "F",
            "city": "Bangui",
        },
        "property": {
            "type_logement": "maison",
            "zone": "urbain",
            "surface_m2": 120,
            "materiaux_construction": "semi_dur",
            "valeur_batiment": 15_000_000,
            "valeur_contenu": 3_000_000,
            "anciennete_batiment": 15,
            "securite": False,
        },
        "contract": BASE_HABITATION_CONTRACT,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    with TestClient(app) as client:
        policy_response = client.post("/habitation/policies", json=payload, headers=agent_headers)
        assert policy_response.status_code == 200
        policy = policy_response.json()
        assert policy["premium"] > 0
        assert policy["product"] == "HABITATION_MRH"
        assert policy["property_id"] is not None
        assert policy["vehicle_id"] is None
        assert policy["pricing_result_id"] is not None

        listed = client.get("/policies").json()
        listed_policy = next(p for p in listed if p["id"] == policy["id"])
        assert listed_policy["property_id"] == policy["property_id"]
        # Régression : le contrôle réglementaire doit utiliser le bon
        # produit (HABITATION_MRH), pas AUTO_RC en dur.
        assert listed_policy["regulatory_check"]["compliant"] is True

        claim_response = client.post(
            "/claims",
            json={
                "policy_id": policy["id"],
                "claim_date": "2026-04-01",
                "claim_type": "incendie",
                "claim_amount": 500_000,
            },
            headers=agent_headers,
        )
        assert claim_response.status_code == 200
        assert claim_response.json()["policy_id"] == policy["id"]

        # Le loss ratio habitation ne doit pas être pollué par les polices
        # auto (voir docs/habitation.md) : le filtre ?product= isole la branche.
        kpis_habitation = client.get("/portfolio/kpis?product=HABITATION_MRH").json()
        assert kpis_habitation["nombre_polices"] >= 1
        assert kpis_habitation["sinistres_totaux"] >= 500_000


def test_habitation_policy_subscription_requires_authentication():
    payload = {
        "customer": {"first_name": "Anon", "last_name": "Test", "birth_date": "1985-02-15", "gender": "F"},
        "property": {
            "type_logement": "maison",
            "zone": "urbain",
            "surface_m2": 120,
            "materiaux_construction": "dur",
            "valeur_batiment": 10_000_000,
            "valeur_contenu": 2_000_000,
            "anciennete_batiment": 5,
            "securite": True,
        },
        "contract": BASE_HABITATION_CONTRACT,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    with TestClient(app) as client:
        response = client.post("/habitation/policies", json=payload)
    assert response.status_code == 401
