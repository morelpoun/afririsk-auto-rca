from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Usage = Literal["particulier", "professionnel"]
Zone = Literal["bangui", "province"]
Garantie = Literal["tiers_simple", "tiers_etendu", "tous_risques"]


class ContractInput(BaseModel):
    age_conducteur: int = Field(..., ge=18, le=90, description="Âge du conducteur principal")
    anciennete_permis: int = Field(..., ge=0, le=72, description="Ancienneté du permis en années")
    usage: Usage = "particulier"
    zone: Zone = "bangui"
    puissance_cv: int = Field(..., ge=1, le=60, description="Puissance fiscale du véhicule (CV)")
    valeur_vehicule_fcfa: float = Field(..., gt=0, description="Valeur assurée du véhicule (FCFA)")
    garantie: Garantie = "tiers_simple"
    nb_sinistres_anterieurs: int = Field(0, ge=0, le=20)


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
    frequence_contributions: dict[str, float]
    severite_contributions: dict[str, float]
    frequence_moyenne_portefeuille: float
    cout_moyen_portefeuille: float
    model_version: str
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
