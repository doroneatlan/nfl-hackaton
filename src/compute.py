"""!
@file compute.py
@brief Point d'entrée : calcule toutes les mesures et écrit les CSV de results/.

Lancement depuis la racine du projet : python -m src.compute
"""

from pathlib import Path

import pandas as pd

from src.loading import load_pff, load_players, load_plays
from src.pressure import chip_pressure
from src.rushers import rushes_with_context, summarize_rushers
from src.selection import add_play_context, select_route_runners
from src.situation_stats import summarize_situations
from src.summary import VERDICT_UNKNOWN, summarize_players
from src.tracking import all_route_paths, measure_all_games

## Dossier des résultats lus par l'interface.
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

## Nombre maximal de routes directes tracées par joueur (garde routes.csv léger).
MAX_DIRECT_PATHS = 30


def routes_to_draw(runners: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Choisit les routes à tracer : tous les chips et un échantillon de routes directes.
    @param runners Routes sélectionnées (select_route_runners).
    @param summary Synthèse par joueur (summarize_players).
    @return Routes des joueurs jugés uniquement.
    @note L'échantillon est mélangé par une clé calculée (pas de tirage aléatoire) :
          le fichier est identique quelle que soit la version de pandas.
    """
    judged = summary.loc[summary["verdict"] != VERDICT_UNKNOWN, "nflId"]
    routes = runners[runners["nflId"].isin(judged)]
    chips = routes[routes["chip"]]
    direct = routes[~routes["chip"]]
    shuffle_key = (direct["gameId"] * 31 + direct["playId"]) % 997
    direct = direct.assign(shuffle_key=shuffle_key)
    direct = direct.sort_values(["nflId", "shuffle_key", "gameId", "playId"]).groupby("nflId").head(MAX_DIRECT_PATHS)
    return pd.concat([chips, direct.drop(columns="shuffle_key")], ignore_index=True)


def add_route_context(paths: pd.DataFrame, runners: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Ajoute aux trajets le contexte attendu par le graphique des situations.
    @param paths Trajets (all_route_paths).
    @param runners Routes sélectionnées avec contexte (add_play_context).
    @return Trajets avec down, yardsToGo et couverture (pff_passCoverage).
    """
    context = runners[["gameId", "playId", "nflId", "down", "yardsToGo", "pff_passCoverage"]]
    context = context.rename(columns={"pff_passCoverage": "couverture"})
    return paths.merge(context, on=["gameId", "playId", "nflId"], how="left")


def save(table: pd.DataFrame, name: str) -> None:
    """!
    @brief Écrit une table dans results/ et affiche sa taille.
    @param table Table à écrire.
    @param name Nom du fichier CSV.
    """
    table.to_csv(RESULTS_DIR / name, index=False)
    print(f"{name:<20} {len(table):>7} lignes")


def main() -> None:
    """!
    @brief Calcule et écrit player_summary.csv, rushers.csv, situations.csv et routes.csv.
    """
    pff, plays, players = load_pff(), load_plays(), load_players()
    runners = add_play_context(select_route_runners(pff, players), plays)
    measured = measure_all_games(runners)
    chips = chip_pressure(runners, pff)

    summary = summarize_players(runners, measured, chips)
    rushers = summarize_rushers(rushes_with_context(pff, plays, runners), players)
    situations = summarize_situations(chips, runners, measured)
    paths = add_route_context(all_route_paths(routes_to_draw(runners, summary)), runners)

    RESULTS_DIR.mkdir(exist_ok=True)
    save(summary, "player_summary.csv")
    save(rushers, "rushers.csv")
    save(situations, "situations.csv")
    save(paths, "routes.csv")
    print(summary["verdict"].value_counts().to_string())


if __name__ == "__main__":
    main()
