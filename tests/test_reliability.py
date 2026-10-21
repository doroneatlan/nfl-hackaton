"""!
@file test_reliability.py
@brief Tests du calcul de confiance et du niveau de fiabilité.
"""

import math

import pytest

from src.reliability import confidence_fewer, reliability_label


def test_no_effect_gives_about_half():
    """! @brief Autant de pressions qu'attendu : aucune preuve, confiance proche de 50 %. """
    assert confidence_fewer(observed=10, expected=10) == pytest.approx(0.5, abs=0.05)


def test_far_fewer_pressures_gives_high_confidence():
    """! @brief 0 pression sur 5 attendues : le chip marche presque sûrement. """
    assert confidence_fewer(observed=0, expected=5) > 0.95


def test_more_pressures_gives_low_confidence():
    """! @brief 5 pressions sur 1,5 attendue : le chip ne marche presque sûrement pas. """
    assert confidence_fewer(observed=5, expected=1.5) < 0.05


def test_more_data_gives_more_confidence():
    """! @brief Même effet relatif (-30 %), mais 10 fois plus de chips : confiance plus haute. """
    small = confidence_fewer(observed=7, expected=10)
    large = confidence_fewer(observed=70, expected=100)
    assert large > small


def test_no_expected_pressure_is_unknown():
    """! @brief Sans pression attendue, la confiance n'a pas de sens. """
    assert math.isnan(confidence_fewer(observed=0, expected=0))


def test_reliability_labels():
    """! @brief Fiabilité forte au-delà de 90 % de certitude, dans un sens comme dans l'autre. """
    assert reliability_label(0.95) == "forte"
    assert reliability_label(0.05) == "forte"
    assert reliability_label(0.80) == "moyenne"
    assert reliability_label(0.50) == "faible"
    assert reliability_label(math.nan) == "inconnue"
