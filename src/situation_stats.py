"""!
@file situation_stats.py
@brief Rentabilité du chip selon la situation de jeu : distance à faire, tentative, couverture.
@note Calcul des chiffres (situations.csv). Le graphique est dans situations.py (Personne 3).
"""

import pandas as pd

from src.reliability import confidence_fewer, reliability_label

## Bornes des tranches de distance à faire (yards) et leurs noms.
DISTANCE_BINS = [0, 3, 7, 100]
DISTANCE_LABELS = ["courte (1-3)", "moyenne (4-7)", "longue (8+)"]

## Nombre minimal de chips pour afficher une situation.
MIN_SITUATION_CHIPS = 30


def add_situations(table: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Ajoute les colonnes de situation lisibles par un coach.
    @param table Table contenant down, yardsToGo et pff_passCoverageType.
    @return Copie avec les colonnes distance, tentative et couverture.
    """
    result = table.copy()
    result["distance"] = pd.cut(result["yardsToGo"], DISTANCE_BINS, labels=DISTANCE_LABELS).astype(str)
    result["tentative"] = result["down"].map(lambda down: "3e / 4e" if down >= 3 else "1re / 2e")
    result["couverture"] = result["pff_passCoverageType"].fillna("inconnue")
    return result


def situation_effect(chips: pd.DataFrame, measured: pd.DataFrame, column: str) -> pd.DataFrame:
    """!
    @brief Gain (pression évitée) et coût (profondeur perdue) du chip pour chaque valeur d'une situation.
    @param chips Chips mesurés avec situations (chip_pressure + add_situations).
    @param measured Routes mesurées avec situations, des seuls joueurs qui font des chips.
    @param column Situation étudiée ("distance", "tentative" ou "couverture").
    @return Une ligne par valeur de la situation.
    """
    gain = chips.groupby(column).agg(
        nb_chips=("pressure", "size"),
        pressions_attendues=("expected_pressure", "sum"),
        pressions_reelles=("pressure", "sum"),
    )
    gain["pression_evitee"] = (gain["pressions_attendues"] - gain["pressions_reelles"]) / gain["nb_chips"] * 100
    gain["confiance"] = [confidence_fewer(obs, exp) * 100 for obs, exp
                         in zip(gain["pressions_reelles"], gain["pressions_attendues"])]

    depth = measured.pivot_table(index=column, columns="chip", values="depth", aggfunc="mean")
    gain["cout_profondeur"] = depth[False] - depth[True]

    gain = gain[gain["nb_chips"] >= MIN_SITUATION_CHIPS]
    gain["fiabilite"] = (gain["confiance"] / 100).map(reliability_label)
    return gain.reset_index().rename(columns={column: "valeur"}).assign(situation=column)


def summarize_situations(chips: pd.DataFrame, runners: pd.DataFrame, measured: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Table de toutes les situations, prête pour l'interface.
    @param chips Chips mesurés (chip_pressure).
    @param runners Routes sélectionnées avec contexte (add_play_context).
    @param measured Routes mesurées (measure_all_games).
    @return Une ligne par situation et par valeur.
    @note Le coût compare chaque joueur qui fait des chips à ses propres routes directes,
          pour ne pas mélanger avec les WR qui ne font jamais de chip.
    """
    context = runners[["gameId", "playId", "nflId", "down", "yardsToGo", "pff_passCoverageType"]]
    chips = add_situations(chips.merge(context, on=["gameId", "playId", "nflId"]))
    chippers = chips["nflId"].unique()
    measured = add_situations(measured[measured["nflId"].isin(chippers)])

    tables = [situation_effect(chips, measured, column) for column in ("distance", "tentative", "couverture")]
    columns = ["situation", "valeur", "nb_chips", "pressions_attendues", "pressions_reelles",
               "pression_evitee", "confiance", "fiabilite", "cout_profondeur"]
    return pd.concat(tables, ignore_index=True)[columns].round(2)
