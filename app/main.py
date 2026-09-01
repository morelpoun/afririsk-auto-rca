from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.actuarial_model import ActuarialEngine
from app.data_simulation import generate_portfolio
from app.schemas import (
    ContractInput,
    PricingResponse,
    SimulationPoint,
    SimulationRequest,
    SimulationResponse,
)

PORTFOLIO_SIZE = 15_000
PORTFOLIO_SEED = 42


@asynccontextmanager
async def lifespan(app: FastAPI):
    portfolio = generate_portfolio(n=PORTFOLIO_SIZE, seed=PORTFOLIO_SEED)
    engine = ActuarialEngine()
    engine.fit(portfolio)
    app.state.engine = engine
    yield


app = FastAPI(
    title="AfriRisk Auto — MVP tarification RCA",
    description=(
        "API de tarification automobile pour le marché centrafricain, "
        "calibrée sur un portefeuille synthétique (voir docs/cahier_des_charges.md)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tarif", response_model=PricingResponse)
def tarif(contract: ContractInput, request: Request) -> PricingResponse:
    engine: ActuarialEngine = request.app.state.engine
    result = engine.price(contract.model_dump())
    return PricingResponse(**result.__dict__)


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
