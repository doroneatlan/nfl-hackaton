"""!
@file reliability.py
@brief Fiabilité d'un résultat : probabilité que le chip réduise vraiment la pression.

Question posée : "si le chip ne servait à rien, les défenseurs visés auraient-ils fait
plus de pressions que ce qu'on observe ?". Sans effet du chip, le nombre de pressions suit
à peu près une loi de Poisson de moyenne = pressions attendues (leur taux habituel).
"""

import pandas as pd
from scipy.stats import poisson

## Seuil de confiance pour déclarer un effet (75 % = 3 chances sur 4).
CONFIDENT = 0.75

## Seuil de confiance pour une fiabilité forte.
VERY_CONFIDENT = 0.90


def confidence_fewer(observed: float, expected: float) -> float:
    """!
    @brief Probabilité que le chip réduise vraiment la pression.
    @param observed Nombre de pressions observées sur les chips.
    @param expected Nombre de pressions attendues sans chip (somme des taux habituels).
    @return Probabilité entre 0 et 1 (0,5 = aucune preuve dans un sens ni dans l'autre).
    @note "mid-p" : P(X > observé) + P(X = observé) / 2, avec X ~ Poisson(attendu).
          Symétrique : un chip qui augmente la pression donne une confiance proche de 0.
    """
    if pd.isna(expected) or expected <= 0:
        return float("nan")
    return float(poisson.sf(observed, expected) + poisson.pmf(observed, expected) / 2)


def reliability_label(confidence: float) -> str:
    """!
    @brief Traduit une confiance en niveau de fiabilité lisible par un coach.
    @param confidence Probabilité entre 0 et 1 (confidence_fewer).
    @return "forte", "moyenne", "faible", ou "inconnue" si NaN.
    @note Une confiance de 5 % est aussi fiable qu'une de 95 % : l'effet est juste négatif.
    """
    if pd.isna(confidence):
        return "inconnue"
    certainty = max(confidence, 1 - confidence)
    if certainty >= VERY_CONFIDENT:
        return "forte"
    if certainty >= CONFIDENT:
        return "moyenne"
    return "faible"
