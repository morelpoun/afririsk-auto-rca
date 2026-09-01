"""Table des États membres de la CIMA et enregistrement de leurs règles
réglementaires, par produit (auto RC, habitation MRH — voir `PRODUCTS`).

Choix de conception important : ce projet n'a **aucune donnée réelle** par
pays permettant de différencier statistiquement le risque auto entre le
Cameroun, le Gabon, le Congo, etc. Plutôt que d'inventer des coefficients de
risque par pays (ce qui donnerait une fausse impression de précision),
`ActuarialEngine` reste un modèle de risque **unique, partagé** par tous les
pays CIMA (calibré sur les hypothèses RCA — voir
`actuarial/data_simulation.py`). Ce que ce module généralise, c'est la couche
réglementaire (tarif minimum par pays, devise) et administrative (à quel pays
un contrat est rattaché) — pas le modèle de risque lui-même. La calibration
par pays sur données réelles reste un prérequis explicite avant toute
commercialisation hors RCA (voir docs/regulatory.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.regulatory.rules import RegulatoryRule, register_rule


class CimaCountryCode(str, Enum):
    BJ = "BJ"  # Bénin
    BF = "BF"  # Burkina Faso
    CM = "CM"  # Cameroun
    CF = "CF"  # République Centrafricaine
    KM = "KM"  # Comores
    CG = "CG"  # Congo
    CI = "CI"  # Côte d'Ivoire
    GA = "GA"  # Gabon
    GW = "GW"  # Guinée-Bissau
    GQ = "GQ"  # Guinée Équatoriale
    ML = "ML"  # Mali
    NE = "NE"  # Niger
    SN = "SN"  # Sénégal
    TD = "TD"  # Tchad
    TG = "TG"  # Togo


@dataclass(frozen=True)
class CimaCountry:
    code: CimaCountryCode
    name: str
    currency: str
    zone_monetaire: str  # UEMOA (XOF), CEMAC (XAF), ou hors zone franc CFA


CIMA_COUNTRIES: list[CimaCountry] = [
    CimaCountry(CimaCountryCode.BJ, "Bénin", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.BF, "Burkina Faso", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.CM, "Cameroun", "XAF", "CEMAC"),
    CimaCountry(CimaCountryCode.CF, "République Centrafricaine", "XAF", "CEMAC"),
    CimaCountry(CimaCountryCode.KM, "Comores", "KMF", "Hors zone franc CFA"),
    CimaCountry(CimaCountryCode.CG, "Congo", "XAF", "CEMAC"),
    CimaCountry(CimaCountryCode.CI, "Côte d'Ivoire", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.GA, "Gabon", "XAF", "CEMAC"),
    CimaCountry(CimaCountryCode.GW, "Guinée-Bissau", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.GQ, "Guinée Équatoriale", "XAF", "CEMAC"),
    CimaCountry(CimaCountryCode.ML, "Mali", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.NE, "Niger", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.SN, "Sénégal", "XOF", "UEMOA"),
    CimaCountry(CimaCountryCode.TD, "Tchad", "XAF", "CEMAC"),
    CimaCountry(CimaCountryCode.TG, "Togo", "XOF", "UEMOA"),
]

_BY_CODE = {c.code: c for c in CIMA_COUNTRIES}

PRODUCT_AUTO_RC = "AUTO_RC"
PRODUCT_HABITATION_MRH = "HABITATION_MRH"
PRODUCTS = [PRODUCT_AUTO_RC, PRODUCT_HABITATION_MRH]
REGULATORY_VERSION = "CIMA-code-provisoire"  # aucune règle n'a encore été validée pays par pays


def country_info(code: CimaCountryCode | str) -> CimaCountry:
    return _BY_CODE[CimaCountryCode(code)]


def currency_for_country(code: CimaCountryCode | str) -> str:
    return country_info(code).currency


def load_all_regulatory_rules() -> None:
    """Enregistre une règle par (pays, produit) pour tous les pays membres et
    tous les produits supportés (`PRODUCTS`), sans tarif minimum (voir
    l'avertissement du module `regulatory.rules` : `minimum_premium` reste
    `None` tant qu'aucune valeur n'a été obtenue et validée).
    """
    for country in CIMA_COUNTRIES:
        for product in PRODUCTS:
            register_rule(
                RegulatoryRule(
                    country=country.code.value,
                    currency=country.currency,
                    regulator="CIMA",
                    product=product,
                    regulatory_version=REGULATORY_VERSION,
                    effective_from=date(2024, 1, 1),
                    effective_to=None,
                    approval_required=True,
                    minimum_premium=None,
                )
            )
