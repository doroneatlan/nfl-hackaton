"""!
@file summary.py
@brief Fiche de synthèse par joueur : coût du chip, pression évitée, fiabilité et verdict.
"""

import pandas as pd

from src.reliability import CONFIDENT, confidence_fewer, reliability_label

## Nombre minimal de chips mesurés pour juger un joueur.
MIN_CHIPS = 10

## Verdicts possibles.
VERDICT_GOOD = "rentable"
VERDICT_BAD = "pas rentable"
VERDICT_UNSURE = "incertain"
VERDICT_UNKNOWN = "pas assez de données"


def mean_by_chip(measured: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
    """!
    @brief Moyenne d'une mesure par joueur, séparée entre routes avec et sans chip.
    @param measured Routes mesurées (measure_all_games).
    @param column Mesure à moyenner ("depth" ou "separation").
    @param name Préfixe des colonnes de sortie.
    @return Une ligne par joueur (index nflId) : <name>_chip, <name>_sans_chip.
    """
    means = measured.pivot_table(index="nflId", columns="chip", values=column, aggfunc="mean")
    means = means.reindex(columns=[True, False])
    means.columns = [f"{name}_chip", f"{name}_sans_chip"]
    return means


def player_identity(runners: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Nom, poste, équipe et nombre de routes de chaque joueur.
    @param runners Routes sélectionnées avec contexte (add_play_context).
    @return Une ligne par joueur (index nflId).
    @note L'équipe retenue est celle avec laquelle le joueur a joué le plus d'actions.
    """
    return runners.groupby("nflId").agg(
        nom=("displayName", "first"),
        poste=("officialPosition", "first"),
        equipe=("possessionTeam", lambda teams: teams.mode().iloc[0]),
        nb_chips=("chip", "sum"),
        nb_sans_chip=("chip", lambda chips: (~chips).sum()),
    )


def pressure_by_player(chips: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Pression attendue, réelle et évitée par les chips de chaque joueur, avec la confiance.
    @param chips Chips mesurés (chip_pressure).
    @return Une ligne par joueur (index nflId). Taux en %, pressions en nombre d'actions.
    """
    grouped = chips.groupby("nflId")
    result = pd.DataFrame({
        "nb_chips_mesures": grouped.size(),
        "pressions_attendues": grouped["expected_pressure"].sum(),
        "pressions_reelles": grouped["pressure"].sum(),
        "pression_chip": grouped["pressure"].mean() * 100,
        "pression_sans_chip": grouped["expected_pressure"].mean() * 100,
    })
    result["pression_evitee"] = result["pression_sans_chip"] - result["pression_chip"]
    result["confiance"] = [confidence_fewer(obs, exp) * 100 for obs, exp
                           in zip(result["pressions_reelles"], result["pressions_attendues"])]
    return result


def verdict(nb_chips: int, confiance: float) -> str:
    """!
    @brief Décide si le chip d'un joueur est rentable, en tenant compte du hasard.
    @param nb_chips Nombre de chips mesurés du joueur.
    @param confiance Probabilité (en %) que le chip réduise vraiment la pression.
    @return VERDICT_GOOD si confiance >= 75 %, VERDICT_BAD si <= 25 %,
            VERDICT_UNSURE entre les deux, VERDICT_UNKNOWN avec trop peu de chips.
    """
    if nb_chips < MIN_CHIPS or pd.isna(confiance):
        return VERDICT_UNKNOWN
    if confiance >= CONFIDENT * 100:
        return VERDICT_GOOD
    if confiance <= (1 - CONFIDENT) * 100:
        return VERDICT_BAD
    return VERDICT_UNSURE


def explain(row: pd.Series) -> str:
    """!
    @brief Explique le verdict d'un joueur en une phrase lisible par un coach.
    @param row Ligne de la synthèse (summarize_players).
    @return Le pourquoi du verdict : coût, gain et fiabilité.
    """
    if row["verdict"] == VERDICT_UNKNOWN:
        return f"Seulement {int(row['nb_chips'])} chips : pas assez pour juger."
    return (
        f"Sur {int(row['nb_chips_mesures'])} chips, les défenseurs visés auraient dû faire "
        f"{row['pressions_attendues']:.1f} pressions ; ils en ont fait {int(row['pressions_reelles'])}. "
        f"Coût : {row['cout_profondeur']:.1f} yards de profondeur. "
        f"Confiance : {row['confiance']:.0f} % (fiabilité {row['fiabilite']})."
    )


def summarize_players(runners: pd.DataFrame, measured: pd.DataFrame, chips: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Construit la fiche de synthèse de chaque joueur ayant fait au moins un chip.
    @param runners Routes sélectionnées avec contexte (add_play_context).
    @param measured Routes mesurées (measure_all_games).
    @param chips Chips mesurés (chip_pressure).
    @return Une ligne par joueur, colonnes du contrat player_summary.csv.
    """
    summary = player_identity(runners)
    summary = summary[summary["nb_chips"] > 0]
    summary = summary.join(mean_by_chip(measured, "depth", "profondeur"))
    summary = summary.join(mean_by_chip(measured, "separation", "separation"))
    summary = summary.join(pressure_by_player(chips))
    summary["nb_chips_mesures"] = summary["nb_chips_mesures"].fillna(0).astype(int)

    summary["cout_profondeur"] = summary["profondeur_sans_chip"] - summary["profondeur_chip"]
    summary["fiabilite"] = (summary["confiance"] / 100).map(reliability_label)
    summary["verdict"] = [verdict(n, c) for n, c in zip(summary["nb_chips_mesures"], summary["confiance"])]
    summary = summary.round(2)
    summary["explication"] = summary.apply(explain, axis=1)
    summary = summary.reset_index()
    return summary.sort_values(["nb_chips", "nflId"], ascending=[False, True], ignore_index=True)
