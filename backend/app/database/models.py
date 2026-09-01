from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date]
    gender: Mapped[str] = mapped_column(String(1))
    profession: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="CF")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="customer")
    policies: Mapped[list["Policy"]] = relationship(back_populates="customer")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    registration_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year: Mapped[int]
    vehicle_type: Mapped[str] = mapped_column(String(30))
    power: Mapped[int]
    market_value: Mapped[float]
    usage: Mapped[str] = mapped_column(String(20))

    customer: Mapped["Customer"] = relationship(back_populates="vehicles")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    product: Mapped[str] = mapped_column(String(30), default="AUTO_RC")
    start_date: Mapped[date]
    end_date: Mapped[date]
    coverage: Mapped[str] = mapped_column(String(30))
    deductible: Mapped[float] = mapped_column(default=0.0)
    premium: Mapped[float]
    status: Mapped[str] = mapped_column(String(20), default="active")

    customer: Mapped["Customer"] = relationship(back_populates="policies")
    claims: Mapped[list["Claim"]] = relationship(back_populates="policy")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"))
    claim_date: Mapped[date]
    claim_type: Mapped[str] = mapped_column(String(30))
    claim_amount: Mapped[float]
    paid_amount: Mapped[float] = mapped_column(default=0.0)
    reserved_amount: Mapped[float] = mapped_column(default=0.0)
    responsibility: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")

    policy: Mapped["Policy"] = relationship(back_populates="claims")


class PricingResult(Base):
    """Trace chaque cotation calculée, pour pouvoir reconstruire exactement
    un calcul passé (modèle, version réglementaire, entrées, sortie).
    """

    __tablename__ = "pricing_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int | None] = mapped_column(ForeignKey("policies.id"), nullable=True)
    model_version: Mapped[str] = mapped_column(String(30))
    regulatory_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_data: Mapped[dict] = mapped_column(JSON)
    frequency: Mapped[float]
    severity: Mapped[float]
    pure_premium: Mapped[float]
    expenses: Mapped[float]
    margin: Mapped[float]
    commercial_premium: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
