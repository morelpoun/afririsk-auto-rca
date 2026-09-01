from fastapi.testclient import TestClient

from app.database import models
from app.database.session import SessionLocal
from app.main import app

BASE_CONTRACT = {
    "country": "CF",
    "age_conducteur": 35,
    "anciennete_permis": 15,
    "usage": "particulier",
    "zone": "rural",
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
        "usage_taxi_moto",
        "zone_urbain",
        "nb_sinistres_anterieurs",
        "anciennete_plafonnee",
    }
    assert data["model_version"] == "GLM_FREQ_SEV_V1"
    assert data["pricing_result_id"] is not None
    assert data["currency"] == "XAF"
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


def test_countries_endpoint_lists_15_cima_members():
    with TestClient(app) as client:
        response = client.get("/countries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 15
    codes = {c["code"] for c in data}
    assert {"CF", "CM", "GA", "CG", "SN", "CI"} <= codes
    cf = next(c for c in data if c["code"] == "CF")
    assert cf["currency"] == "XAF"


def test_tarif_uses_currency_and_regulatory_rule_of_contract_country():
    senegal_contract = dict(BASE_CONTRACT, country="SN")
    with TestClient(app) as client:
        response = client.post("/tarif", json=senegal_contract)
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "XOF"
    assert data["regulatory_check"]["regulatory_version"] is not None


def test_same_contract_prices_identically_regardless_of_country():
    # Le modèle de risque est unique et partagé par tous les pays CIMA
    # (voir docs/regulatory.md) : seuls la devise et le contrôle
    # réglementaire doivent varier avec le pays, pas la prime elle-même.
    with TestClient(app) as client:
        cf_result = client.post("/tarif", json=dict(BASE_CONTRACT, country="CF")).json()
        cm_result = client.post("/tarif", json=dict(BASE_CONTRACT, country="CM")).json()

    assert cf_result["prime_commerciale"] == cm_result["prime_commerciale"]
    assert cf_result["currency"] == cm_result["currency"] == "XAF"  # CF et CM partagent la zone CEMAC


def test_taxi_moto_usage_increases_frequency():
    with TestClient(app) as client:
        particulier = client.post("/tarif", json=BASE_CONTRACT).json()
        taxi_moto_contract = dict(BASE_CONTRACT, usage="taxi_moto")
        taxi_moto = client.post("/tarif", json=taxi_moto_contract).json()

    assert taxi_moto["frequence_estimee"] > particulier["frequence_estimee"]
    assert set(taxi_moto["frequence_contributions"]) == {
        "jeune",
        "usage_pro",
        "usage_taxi_moto",
        "zone_urbain",
        "nb_sinistres_anterieurs",
        "anciennete_plafonnee",
    }


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


def test_bonus_malus_rejects_negative_claim_counts():
    with TestClient(app) as client:
        response = client.post("/bonus-malus/compute", json={"historique_sinistres": [0, -5, 1]})
    assert response.status_code == 422


def test_policy_subscription_and_claim_flow(agent_headers):
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
        policy_response = client.post("/policies", json=payload, headers=agent_headers)
        assert policy_response.status_code == 200
        policy = policy_response.json()
        assert policy["premium"] > 0
        assert policy["currency"] == "XAF"
        assert policy["pricing_result_id"] is not None
        assert policy["regulatory_check"]["compliant"] is True

        listed = client.get("/policies").json()
        listed_policy = next(p for p in listed if p["id"] == policy["id"])
        assert listed_policy["pricing_result_id"] == policy["pricing_result_id"]
        assert listed_policy["regulatory_check"]["compliant"] is True

        claim_response = client.post(
            "/claims",
            json={
                "policy_id": policy["id"],
                "claim_date": "2026-03-01",
                "claim_type": "materiel",
                "claim_amount": 150_000,
            },
            headers=agent_headers,
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
        assert kpis["currencies"] == ["XAF"]

        kpis_cf_only = client.get("/portfolio/kpis?country=CF").json()
        assert kpis_cf_only["nombre_polices"] >= 1

        kpis_other_country = client.get("/portfolio/kpis?country=SN").json()
        assert kpis_other_country["nombre_polices"] == 0
        assert kpis_other_country["currencies"] == []


def test_claim_on_unknown_policy_returns_404(agent_headers):
    with TestClient(app) as client:
        response = client.post(
            "/claims",
            json={
                "policy_id": 999_999,
                "claim_date": "2026-03-01",
                "claim_type": "materiel",
                "claim_amount": 100_000,
            },
            headers=agent_headers,
        )
    assert response.status_code == 404


def test_policy_subscription_requires_authentication():
    payload = {
        "customer": {
            "first_name": "Anon",
            "last_name": "Test",
            "birth_date": "1990-05-10",
            "gender": "M",
        },
        "vehicle": {
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
        response = client.post("/policies", json=payload)
    assert response.status_code == 401


def test_policy_subscription_rejects_viewer_role(viewer_headers):
    payload = {
        "customer": {
            "first_name": "Viewer",
            "last_name": "Test",
            "birth_date": "1990-05-10",
            "gender": "M",
        },
        "vehicle": {
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
        response = client.post("/policies", json=payload, headers=viewer_headers)
    assert response.status_code == 403


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
