from app.actuarial.bonus_malus import (
    BASE_COEFFICIENT,
    MAX_COEFFICIENT,
    MIN_COEFFICIENT,
    compute_bonus_malus,
)


def test_no_history_keeps_base_coefficient():
    result = compute_bonus_malus([])
    assert result.coefficient == BASE_COEFFICIENT


def test_claim_free_years_reduce_coefficient():
    result = compute_bonus_malus([0, 0, 0])
    assert result.coefficient < BASE_COEFFICIENT
    assert result.coefficient == round(0.95**3, 4)


def test_claims_increase_coefficient():
    result = compute_bonus_malus([1, 1])
    assert result.coefficient > BASE_COEFFICIENT


def test_coefficient_is_bounded():
    very_good = compute_bonus_malus([0] * 50)
    very_bad = compute_bonus_malus([3] * 20)
    assert very_good.coefficient >= MIN_COEFFICIENT
    assert very_bad.coefficient <= MAX_COEFFICIENT


def test_avertissement_present():
    result = compute_bonus_malus([0])
    assert "non validée" in result.avertissement
