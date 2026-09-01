"""Couche réglementaire configurable.

Le Code CIMA impose un tarif minimum RC automobile approuvé par État membre
(art. 212) et un visa des tarifs par l'autorité de tutelle (art. 305). La
réglementation évolue (règlements du Conseil des ministres CIMA, ex. 2026) :
elle ne doit donc jamais être codée en dur dans le moteur actuariel, mais
chargée depuis ce module de règles, versionné et remplaçable pays par pays.

Important : tant qu'une valeur de tarif minimum n'a pas été obtenue et
validée auprès du régulateur pour un (pays, produit) donné, `minimum_premium`
reste `None` et aucune contrainte n'est appliquée — un moteur qui inventerait
ce chiffre produirait un faux résultat de conformité.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RegulatoryRule:
    country: str
    currency: str
    regulator: str
    product: str
    regulatory_version: str
    effective_from: date
    effective_to: date | None
    approval_required: bool
    minimum_premium: float | None = None


@dataclass(frozen=True)
class RegulatoryCheckResult:
    compliant: bool
    rule: RegulatoryRule | None
    message: str


_REGISTRY: dict[tuple[str, str], RegulatoryRule] = {}


def register_rule(rule: RegulatoryRule) -> None:
    _REGISTRY[(rule.country, rule.product)] = rule


def get_rule(country: str, product: str) -> RegulatoryRule | None:
    return _REGISTRY.get((country, product))


def check_minimum_tariff(country: str, product: str, commercial_premium: float) -> RegulatoryCheckResult:
    rule = get_rule(country, product)
    if rule is None:
        return RegulatoryCheckResult(
            compliant=True,
            rule=None,
            message=f"Aucune règle réglementaire configurée pour ({country}, {product}).",
        )
    if rule.minimum_premium is None:
        return RegulatoryCheckResult(
            compliant=True,
            rule=rule,
            message=(
                "Tarif minimum non configuré (valeur à obtenir et valider auprès du "
                f"régulateur {rule.regulator}) — aucune contrainte appliquée."
            ),
        )
    if commercial_premium < rule.minimum_premium:
        return RegulatoryCheckResult(
            compliant=False,
            rule=rule,
            message=(
                f"Prime commerciale ({commercial_premium:.0f} {rule.currency}) inférieure "
                f"au tarif minimum réglementaire ({rule.minimum_premium:.0f} {rule.currency})."
            ),
        )
    return RegulatoryCheckResult(
        compliant=True,
        rule=rule,
        message="Prime commerciale conforme au tarif minimum réglementaire configuré.",
    )
