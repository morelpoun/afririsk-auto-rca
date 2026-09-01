from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.regulatory.cima_countries import CimaCountryCode

Usage = Literal["particulier", "professionnel"]
Zone = Literal["urbain", "rural"]
Garantie = Literal["tiers_simple", "tiers_etendu", "tous_risques"]
Gender = Literal["M", "F"]


class ContractInput(BaseModel):
    country: CimaCountryCode = Field(
        CimaCountryCode.CF,
        description=(
            "Pays CIMA du contrat. Le modèle de risque reste identique pour tous les "
            "pays (voir docs/regulatory.md) ; seuls le contrôle réglementaire et la "
            "devise en dépendent."
        ),
    )
    age_conducteur: int = Field(..., ge=18, le=90, description="Âge du conducteur principal")
    anciennete_permis: int = Field(..., ge=0, le=72, description="Ancienneté du permis en années")
    usage: Usage = "particulier"
    zone: Zone = Field("urbain", description="Zone de la capitale/grande ville, ou zone rurale")
    puissance_cv: int = Field(..., ge=1, le=60, description="Puissance fiscale du véhicule (CV)")
    valeur_vehicule_fcfa: float = Field(..., gt=0, description="Valeur assurée du véhicule (devise du pays)")
    garantie: Garantie = "tiers_simple"
    nb_sinistres_anterieurs: int = Field(0, ge=0, le=20)
    coefficient_bonus_malus: float = Field(
        1.0, ge=0.5, le=3.5, description="Coefficient bonus-malus déjà calculé (voir POST /bonus-malus/compute)"
    )


class RegulatoryCheck(BaseModel):
    compliant: bool
    regulatory_version: str | None
    message: str


class PricingResponse(BaseModel):
    frequence_estimee: float
    cout_moyen_estime: float
    prime_pure: float
    frais_gestion: float
    marge_technique: float
    taxes: float
    prime_commerciale: float
    coefficient_bonus_malus: float
    frequence_contributions: dict[str, float]
    severite_contributions: dict[str, float]
    frequence_moyenne_portefeuille: float
    cout_moyen_portefeuille: float
    model_version: str
    currency: str
    regulatory_check: RegulatoryCheck
    pricing_result_id: int | None = None


class SimulationRequest(BaseModel):
    contrat_base: ContractInput
    parametre: Literal[
        "age_conducteur",
        "anciennete_permis",
        "puissance_cv",
        "valeur_vehicule_fcfa",
        "nb_sinistres_anterieurs",
    ]
    valeurs: list[float] = Field(..., min_length=1, max_length=50)


class SimulationPoint(BaseModel):
    valeur: float
    prime_commerciale: float


class SimulationResponse(BaseModel):
    parametre: str
    points: list[SimulationPoint]


class PortfolioMetrics(BaseModel):
    nombre_contrats: int
    frequence_moyenne: float
    cout_moyen_sinistre: float
    prime_pure_moyenne: float
    exposition_totale: float
    nombre_sinistres: int


class PortfolioKPIs(BaseModel):
    nombre_polices: int
    primes_totales: float
    sinistres_totaux: float
    frais_totaux: float
    loss_ratio: float | None
    expense_ratio: float | None
    combined_ratio: float | None
    currencies: list[str] = Field(
        default_factory=list,
        description="Devises effectivement incluses dans l'agrégat — plusieurs valeurs signalent un mélange de devises",
    )


class BonusMalusRequest(BaseModel):
    historique_sinistres: list[Annotated[int, Field(ge=0, le=20)]] = Field(
        ..., min_length=1, max_length=30, description="Sinistres responsables par année, du plus ancien au plus récent"
    )


class BonusMalusResponse(BaseModel):
    coefficient: float
    classe_indicative: int
    avertissement: str


class CustomerInput(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    profession: str | None = None
    city: str | None = None
    country: CimaCountryCode = CimaCountryCode.CF


class VehicleInput(BaseModel):
    registration_number: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int = Field(..., ge=1970, le=2100)
    vehicle_type: str
    power: int = Field(..., ge=1, le=60)
    market_value: float = Field(..., gt=0)
    usage: Usage = "particulier"


class PolicySubscriptionRequest(BaseModel):
    customer: CustomerInput
    vehicle: VehicleInput
    contract: ContractInput
    start_date: date
    end_date: date


class PolicyResponse(BaseModel):
    id: int
    customer_id: int
    vehicle_id: int
    product: str
    start_date: date
    end_date: date
    coverage: str
    deductible: float
    premium: float
    currency: str
    status: str
    pricing_result_id: int | None = None
    regulatory_check: RegulatoryCheck

    model_config = {"from_attributes": True}


class CimaCountryResponse(BaseModel):
    code: CimaCountryCode
    name: str
    currency: str
    zone_monetaire: str


class ClaimInput(BaseModel):
    policy_id: int
    claim_date: date
    claim_type: str
    claim_amount: float = Field(..., ge=0)
    paid_amount: float = Field(0.0, ge=0)
    reserved_amount: float = Field(0.0, ge=0)
    responsibility: float | None = Field(None, ge=0, le=1)


class ClaimResponse(BaseModel):
    id: int
    policy_id: int
    claim_date: date
    claim_type: str
    claim_amount: float
    paid_amount: float
    reserved_amount: float
    responsibility: float | None
    status: str

    model_config = {"from_attributes": True}
