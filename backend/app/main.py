from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.actuarial.data_simulation import generate_portfolio
from app.actuarial.pricing import ActuarialEngine
from app.database import models
from app.database.session import get_db, init_db
from app.regulatory.countries import cf as cf_rules
from app.regulatory.rules import check_minimum_tariff
from app.schemas import (
    ContractInput,
    PortfolioMetrics,
    PricingResponse,
    RegulatoryCheck,
    SimulationPoint,
    SimulationRequest,
    SimulationResponse,
)

PORTFOLIO_SIZE = 15_000
PORTFOLIO_SEED = 42
MODEL_VERSION = "GLM_FREQ_SEV_V1"
COUNTRY = "CF"
PRODUCT = "AUTO_RC"

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
MODEL_COMPARISON_PATH = Path(__file__).resolve().parent / "ml" / "comparison_results.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cf_rules.load()

    portfolio = generate_portfolio(n=PORTFOLIO_SIZE, seed=PORTFOLIO_SEED)
    engine = ActuarialEngine()
    engine.fit(portfolio)
    app.state.engine = engine
    app.state.portfolio = portfolio
    yield


app = FastAPI(
    title="AfriRisk Auto — moteur de tarification actuarielle RCA",
    description=(
        "API de tarification automobile pour le marché centrafricain "
        "(espace CIMA), calibrée sur un portefeuille synthétique "
        "(voir docs/cahier_des_charges.md)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tarif", response_model=PricingResponse)
def tarif(contract: ContractInput, request: Request, db: Session = Depends(get_db)) -> PricingResponse:
    engine: ActuarialEngine = request.app.state.engine
    result = engine.price(contract.model_dump())

    reg_check = check_minimum_tariff(COUNTRY, PRODUCT, result.prime_commerciale)

    row = models.PricingResult(
        model_version=MODEL_VERSION,
        regulatory_version=reg_check.rule.regulatory_version if reg_check.rule else None,
        input_data=contract.model_dump(),
        frequency=result.frequence_estimee,
        severity=result.cout_moyen_estime,
        pure_premium=result.prime_pure,
        expenses=result.frais_gestion + result.marge_technique,
        margin=result.marge_technique,
        commercial_premium=result.prime_commerciale,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return PricingResponse(
        **result.__dict__,
        model_version=MODEL_VERSION,
        regulatory_check=RegulatoryCheck(
            compliant=reg_check.compliant,
            regulatory_version=reg_check.rule.regulatory_version if reg_check.rule else None,
            message=reg_check.message,
        ),
        pricing_result_id=row.id,
    )


@app.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest, request: Request) -> SimulationResponse:
    engine: ActuarialEngine = request.app.state.engine
    base = payload.contrat_base.model_dump()

    points = []
    for valeur in payload.valeurs:
        contract = dict(base)
        contract[payload.parametre] = (
            int(valeur) if isinstance(base[payload.parametre], int) else valeur
        )
        result = engine.price(contract)
        points.append(SimulationPoint(valeur=valeur, prime_commerciale=result.prime_commerciale))

    return SimulationResponse(parametre=payload.parametre, points=points)


@app.get("/models")
def list_models() -> dict:
    """Registre léger des modèles disponibles (pas de MLflow en v0.2).

    Le GLM fréquence×sévérité (`GLM_FREQ_SEV_V1`) est le seul modèle utilisé
    par `/tarif` en production, pour rester pleinement interprétable et
    auditable — voir docs/ml_methodology.md. Le Tweedie et le XGBoost+SHAP
    sont des benchmarks de comparaison, produits par
    `scripts/compare_models.py`, pas des modèles servis en production.
    """
    if not MODEL_COMPARISON_PATH.exists():
        return {
            "production_model": MODEL_VERSION,
            "comparison_available": False,
            "message": (
                "Aucune comparaison enregistrée. Lancer "
                "`cd backend && python -m scripts.compare_models` "
                "(nécessite requirements-ml.txt) pour la générer."
            ),
        }
    comparison = json.loads(MODEL_COMPARISON_PATH.read_text())
    return {
        "production_model": MODEL_VERSION,
        "comparison_available": True,
        **comparison,
    }


@app.get("/portfolio/metrics", response_model=PortfolioMetrics)
def portfolio_metrics(request: Request) -> PortfolioMetrics:
    portfolio = request.app.state.portfolio
    sinistres = portfolio[portfolio["nb_sinistres"] > 0]
    frequence_moyenne = float(portfolio["nb_sinistres"].sum() / portfolio["exposition"].sum())
    cout_moyen = float(sinistres["cout_moyen_sinistre"].mean()) if len(sinistres) else 0.0

    return PortfolioMetrics(
        nombre_contrats=len(portfolio),
        frequence_moyenne=frequence_moyenne,
        cout_moyen_sinistre=cout_moyen,
        prime_pure_moyenne=frequence_moyenne * cout_moyen,
        exposition_totale=float(portfolio["exposition"].sum()),
        nombre_sinistres=int(portfolio["nb_sinistres"].sum()),
    )
