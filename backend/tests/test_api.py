from fastapi.testclient import TestClient

from app.database import models
from app.database.session import SessionLocal
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
    assert data["model_version"] == "GLM_FREQ_SEV_V1"
    assert data["pricing_result_id"] is not None
    # Aucun tarif minimum CIMA/RCA n'est encore configuré (valeur non validée) :
    # le contrôle réglementaire doit donc rester non bloquant pour l'instant.
    assert data["regulatory_check"]["compliant"] is True


def test_portfolio_metrics_endpoint():
    with TestClient(app) as client:
        response = client.get("/portfolio/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["nombre_contrats"] > 0
    assert 0 < data["frequence_moyenne"] < 1
    assert data["cout_moyen_sinistre"] > 0


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


def test_tarif_is_persisted_to_pricing_results():
    with TestClient(app) as client:
        response = client.post("/tarif", json=BASE_CONTRACT)
        pricing_result_id = response.json()["pricing_result_id"]

    db = SessionLocal()
    try:
        row = db.get(models.PricingResult, pricing_result_id)
        assert row is not None
        assert row.model_version == "GLM_FREQ_SEV_V1"
        assert row.input_data["age_conducteur"] == BASE_CONTRACT["age_conducteur"]
    finally:
        db.close()


def test_models_endpoint_reports_production_model():
    with TestClient(app) as client:
        response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert data["production_model"] == "GLM_FREQ_SEV_V1"
    # La comparaison est un artefact généré par scripts/compare_models.py
    # (nécessite requirements-ml.txt) ; si elle n'a pas été lancée, l'endpoint
    # doit rester fonctionnel et l'indiquer clairement plutôt que planter.
    if data["comparison_available"]:
        model_ids = {m["model_id"] for m in data["models"]}
        assert "GLM_FREQ_SEV_V1" in model_ids
    else:
        assert "message" in data


def test_bonus_malus_coefficient_reduces_premium():
    with TestClient(app) as client:
        neutral = client.post("/tarif", json=BASE_CONTRACT).json()
        malussed_contract = dict(BASE_CONTRACT, coefficient_bonus_malus=1.25)
        malussed = client.post("/tarif", json=malussed_contract).json()

    assert malussed["coefficient_bonus_malus"] == 1.25
    assert malussed["prime_commerciale"] > neutral["prime_commerciale"]


def test_bonus_malus_compute_endpoint():
    with TestClient(app) as client:
        response = client.post("/bonus-malus/compute", json={"historique_sinistres": [0, 0, 1, 0]})
    assert response.status_code == 200
    data = response.json()
    assert 0.5 <= data["coefficient"] <= 3.5
    assert "avertissement" in data


def test_policy_subscription_and_claim_flow():
    payload = {
        "customer": {
            "first_name": "Jean",
            "last_name": "Test",
            "birth_date": "1990-05-10",
            "gender": "M",
            "city": "Bangui",
        },
        "vehicle": {
            "brand": "Toyota",
            "model": "Corolla",
            "year": 2019,
            "vehicle_type": "berline",
            "power": 8,
            "market_value": 7_000_000,
            "usage": "particulier",
        },
        "contract": BASE_CONTRACT,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    with TestClient(app) as client:
        policy_response = client.post("/policies", json=payload)
        assert policy_response.status_code == 200
        policy = policy_response.json()
        assert policy["premium"] > 0
        assert policy["pricing_result_id"] is not None

        listed = client.get("/policies").json()
        assert any(p["id"] == policy["id"] for p in listed)

        claim_response = client.post(
            "/claims",
            json={
                "policy_id": policy["id"],
                "claim_date": "2026-03-01",
                "claim_type": "materiel",
                "claim_amount": 150_000,
            },
        )
        assert claim_response.status_code == 200
        claim = claim_response.json()
        assert claim["policy_id"] == policy["id"]

        claims_for_policy = client.get(f"/claims?policy_id={policy['id']}").json()
        assert len(claims_for_policy) == 1

        kpis = client.get("/portfolio/kpis").json()
        assert kpis["nombre_polices"] >= 1
        assert kpis["sinistres_totaux"] >= 150_000
        assert kpis["loss_ratio"] is not None


def test_claim_on_unknown_policy_returns_404():
    with TestClient(app) as client:
        response = client.post(
            "/claims",
            json={
                "policy_id": 999_999,
                "claim_date": "2026-03-01",
                "claim_type": "materiel",
                "claim_amount": 100_000,
            },
        )
    assert response.status_code == 404


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
