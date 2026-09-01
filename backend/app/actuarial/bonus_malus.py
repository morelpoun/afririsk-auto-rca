"""Moteur de coefficient bonus-malus.

Important : la grille ci-dessous est une **grille par défaut générique**
(réduction/majoration classiques observées sur des marchés bonus-malus), pas
la grille réglementaire CIMA validée pour la RC automobile en RCA. Elle ne
doit pas être présentée comme une règle réglementaire tant qu'elle n'a pas
été confrontée et alignée sur le texte applicable (voir docs/regulatory.md
pour la même précaution appliquée au tarif minimum). C'est une table de
règles configurable, pas une vérité réglementaire.
"""
from __future__ import annotations

from dataclasses import dataclass

BASE_COEFFICIENT = 1.0
REDUCTION_PER_CLAIM_FREE_YEAR = 0.95  # -5% par année sans sinistre
INCREASE_PER_CLAIM = 1.25  # +25% par sinistre responsable dans l'année
MIN_COEFFICIENT = 0.50
MAX_COEFFICIENT = 3.50

AVERTISSEMENT = (
    "Grille bonus-malus par défaut, non validée auprès du régulateur CIMA — "
    "à ne pas présenter comme une règle réglementaire applicable en RCA."
)


@dataclass(frozen=True)
class BonusMalusResult:
    coefficient: float
    classe_indicative: int
    avertissement: str = AVERTISSEMENT


def compute_bonus_malus(historique_sinistres: list[int]) -> BonusMalusResult:
    """`historique_sinistres` : nombre de sinistres responsables par année
    d'assurance, du plus ancien au plus récent. Coefficient de départ 1.00.
    """
    coefficient = BASE_COEFFICIENT
    for nb_sinistres_annee in historique_sinistres:
        if nb_sinistres_annee <= 0:
            coefficient *= REDUCTION_PER_CLAIM_FREE_YEAR
        else:
            coefficient *= INCREASE_PER_CLAIM**nb_sinistres_annee
        coefficient = min(max(coefficient, MIN_COEFFICIENT), MAX_COEFFICIENT)

    classe_indicative = round((coefficient - BASE_COEFFICIENT) / 0.05)
    return BonusMalusResult(coefficient=round(coefficient, 4), classe_indicative=classe_indicative)
