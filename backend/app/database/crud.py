"""Opérations de persistance pour le parcours de souscription et les
sinistres. Séparé de main.py pour garder les routes fines et testables.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models


def create_customer(db: Session, data: dict) -> models.Customer:
    customer = models.Customer(**data)
    db.add(customer)
    db.flush()
    return customer


def create_vehicle(db: Session, customer_id: int, data: dict) -> models.Vehicle:
    vehicle = models.Vehicle(customer_id=customer_id, **data)
    db.add(vehicle)
    db.flush()
    return vehicle


def create_policy(db: Session, customer_id: int, vehicle_id: int, data: dict) -> models.Policy:
    policy = models.Policy(customer_id=customer_id, vehicle_id=vehicle_id, **data)
    db.add(policy)
    db.flush()
    return policy


def create_claim(db: Session, data: dict) -> models.Claim:
    claim = models.Claim(**data)
    db.add(claim)
    db.flush()
    return claim


def record_pricing_result(
    db: Session,
    *,
    policy_id: int | None,
    model_version: str,
    regulatory_version: str | None,
    input_data: dict,
    frequency: float,
    severity: float,
    pure_premium: float,
    expenses: float,
    margin: float,
    commercial_premium: float,
) -> models.PricingResult:
    """Point unique de construction d'une ligne `pricing_results`, utilisé
    aussi bien par la souscription (`POST /policies`) que par le générateur
    de données de démonstration (`scripts/seed_database.py`), pour éviter que
    les deux chemins ne divergent silencieusement.
    """
    row = models.PricingResult(
        policy_id=policy_id,
        model_version=model_version,
        regulatory_version=regulatory_version,
        input_data=input_data,
        frequency=frequency,
        severity=severity,
        pure_premium=pure_premium,
        expenses=expenses,
        margin=margin,
        commercial_premium=commercial_premium,
    )
    db.add(row)
    db.flush()
    return row


def get_policy(db: Session, policy_id: int) -> models.Policy | None:
    return db.get(models.Policy, policy_id)


def list_policies(db: Session, limit: int = 50, offset: int = 0) -> list[models.Policy]:
    stmt = select(models.Policy).order_by(models.Policy.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def pricing_result_ids_for_policies(db: Session, policy_ids: list[int]) -> dict[int, int]:
    """Dernier `pricing_results.id` connu par police (une police peut en
    théorie être re-tarifée ; on garde le plus récent).
    """
    if not policy_ids:
        return {}
    stmt = (
        select(models.PricingResult)
        .where(models.PricingResult.policy_id.in_(policy_ids))
        .order_by(models.PricingResult.id.desc())
    )
    mapping: dict[int, int] = {}
    for row in db.scalars(stmt):
        mapping.setdefault(row.policy_id, row.id)
    return mapping


def list_claims(db: Session, policy_id: int | None = None, limit: int = 50, offset: int = 0) -> list[models.Claim]:
    stmt = select(models.Claim).order_by(models.Claim.id.desc())
    if policy_id is not None:
        stmt = stmt.where(models.Claim.policy_id == policy_id)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def portfolio_kpis(db: Session) -> dict:
    policies = list(db.scalars(select(models.Policy)))
    nombre_polices = len(policies)
    primes_totales = sum(p.premium for p in policies)

    policy_ids = [p.id for p in policies]
    sinistres_totaux = 0.0
    frais_totaux = 0.0
    if policy_ids:
        claims = db.scalars(select(models.Claim).where(models.Claim.policy_id.in_(policy_ids)))
        sinistres_totaux = sum(c.claim_amount for c in claims)

        pricing_rows = db.scalars(
            select(models.PricingResult).where(models.PricingResult.policy_id.in_(policy_ids))
        )
        frais_totaux = sum(r.expenses for r in pricing_rows)

    loss_ratio = sinistres_totaux / primes_totales if primes_totales else None
    expense_ratio = frais_totaux / primes_totales if primes_totales else None
    combined_ratio = (
        loss_ratio + expense_ratio if loss_ratio is not None and expense_ratio is not None else None
    )

    return {
        "nombre_polices": nombre_polices,
        "primes_totales": primes_totales,
        "sinistres_totaux": sinistres_totaux,
        "frais_totaux": frais_totaux,
        "loss_ratio": loss_ratio,
        "expense_ratio": expense_ratio,
        "combined_ratio": combined_ratio,
    }
