"""!
@file rushers.py
@brief Fiche des défenseurs qui foncent sur le QB : danger, côté et effet du chip sur eux.
"""

import pandas as pd

from src.pressure import MIN_BASELINE_RUSHES, RUSH_KEYS, chip_targets, rusher_pressure
from src.reliability import confidence_fewer, reliability_label

## Positions défensives centrales (ni à gauche, ni à droite).
CENTER_POSITIONS = ("NT", "MLB")


def offense_side(position: str) -> str:
    """!
    @brief Côté d'un défenseur, vu par l'attaque.
    @param position Position d'alignement PFF (LE, ROLB, DLT...).
    @return "gauche", "droite" ou "centre".
    @note PFF nomme le côté défensif du point de vue de la défense : vérifié sur le tracking,
          un défenseur "L" est aligné à droite de l'attaque, et inversement.
    """
    if position in CENTER_POSITIONS:
        return "centre"
    if position.startswith(("L", "DL", "NL")):
        return "droite"
    if position.startswith(("R", "DR", "NR")):
        return "gauche"
    return "centre"


def rushes_with_context(pff: pd.DataFrame, plays: pd.DataFrame, runners: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Tous les rushs, avec l'équipe du défenseur, son alignement et s'il a été bousculé.
    @param pff Données de scouting PFF (load_pff).
    @param plays Contexte des actions (load_plays).
    @param runners Routes sélectionnées (select_route_runners).
    @return Une ligne par défenseur et par action.
    """
    positions = pff.rename(columns={"nflId": "rusherId"})[RUSH_KEYS + ["pff_positionLinedUp"]]
    chipped = chip_targets(runners)[RUSH_KEYS].drop_duplicates().assign(chipped=True)

    rushes = rusher_pressure(pff).merge(positions, on=RUSH_KEYS)
    rushes = rushes.merge(plays[["gameId", "playId", "defensiveTeam"]], on=["gameId", "playId"])
    rushes = rushes.merge(chipped, on=RUSH_KEYS, how="left")
    rushes["chipped"] = rushes["chipped"].notna()
    return rushes


def chip_effect(rushes: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Pression de chaque défenseur avec et sans chip, et confiance que le chip le freine.
    @param rushes Rushs avec contexte (rushes_with_context).
    @return Une ligne par défenseur (index rusherId), taux en %.
    """
    unchipped = rushes[~rushes["chipped"]].groupby("rusherId")["pressure"].mean()
    chipped = rushes[rushes["chipped"]].groupby("rusherId")["pressure"].agg(["size", "sum", "mean"])

    effect = pd.DataFrame({
        "taux_pression_non_chippe": unchipped * 100,
        "taux_pression_chippe": chipped["mean"] * 100,
    })
    effect["pression_evitee"] = effect["taux_pression_non_chippe"] - effect["taux_pression_chippe"]
    expected = chipped["size"] * unchipped.reindex(chipped.index)
    effect["confiance"] = pd.Series(
        [confidence_fewer(obs, exp) * 100 for obs, exp in zip(chipped["sum"], expected)],
        index=chipped.index)
    return effect


def summarize_rushers(rushes: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Construit la fiche de chaque défenseur ayant assez de rushs.
    @param rushes Rushs avec contexte (rushes_with_context).
    @param players Identité des joueurs (load_players).
    @return Une ligne par défenseur, colonnes du contrat rushers.csv, du plus dangereux au moins dangereux.
    @note Le danger est le nombre de pressions : un défenseur qui rush souvent et touche
          souvent le QB passe devant un blitzeur occasionnel au taux flatteur.
    """
    grouped = rushes.groupby("rusherId")
    summary = pd.DataFrame({
        "equipe": grouped["defensiveTeam"].agg(lambda teams: teams.mode().iloc[0]),
        "alignement": grouped["pff_positionLinedUp"].agg(lambda pos: pos.mode().iloc[0]),
        "nb_rush": grouped.size(),
        "nb_pressions": grouped["pressure"].sum(),
        "taux_pression": grouped["pressure"].mean() * 100,
        "nb_chippe": grouped["chipped"].sum(),
    })
    summary = summary[summary["nb_rush"] - summary["nb_chippe"] >= MIN_BASELINE_RUSHES]
    summary["cote"] = summary["alignement"].map(offense_side)
    summary = summary.join(chip_effect(rushes))
    summary["fiabilite"] = (summary["confiance"] / 100).map(reliability_label)

    identity = players.rename(columns={"nflId": "rusherId", "displayName": "nom",
                                       "officialPosition": "poste"}).set_index("rusherId")
    summary = identity.join(summary, how="inner").sort_values("nb_pressions", ascending=False)
    return summary.round(2).reset_index().rename(columns={"rusherId": "nflId"})
