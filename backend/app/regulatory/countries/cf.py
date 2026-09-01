"""Règles réglementaires pour la République Centrafricaine (CF), espace CIMA.

`minimum_premium` est volontairement `None` : le tarif minimum RC auto prévu
par l'article 212 du Code CIMA est approuvé État par État et n'a pas encore
été obtenu/validé pour la RCA dans ce projet. Ne pas y substituer une valeur
inventée — voir docs/regulatory.md.
"""
from __future__ import annotations

from datetime import date

from app.regulatory.rules import RegulatoryRule, register_rule

CF_AUTO_RC = RegulatoryRule(
    country="CF",
    currency="XAF",
    regulator="CIMA",
    product="AUTO_RC",
    regulatory_version="CIMA-code-provisoire",
    effective_from=date(2024, 1, 1),
    effective_to=None,
    approval_required=True,
    minimum_premium=None,
)


def load() -> None:
    register_rule(CF_AUTO_RC)
