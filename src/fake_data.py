#!/usr/bin/env python3
"""Génère des faux CSV plausibles pour le projet "Le coût du chip".

Produit deux fichiers dans results/ :
  - routes.csv          : trajectoires frame-par-frame (coordonnées normalisées
                          relatives à la ligne de mêlée, x=0 = ligne de mêlée)
  - player_summary.csv  : synthèse par joueur (chip vs sans chip)

Le script est idempotent : il réécrit proprement les CSV à chaque exécution.

Usage :
    python src/fake_data.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

# --- Chemins -----------------------------------------------------------------
# results/ est à la racine du dépôt, src/fake_data.py est dans src/.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SRC_DIR)
RESULTS_DIR = os.path.join(REPO_ROOT, "results")

ROUTES_PATH = os.path.join(RESULTS_DIR, "routes.csv")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "player_summary.csv")

# --- Contrats CSV (ordre exact des colonnes) ---------------------------------
ROUTES_COLUMNS = [
    "gameId", "playId", "nflId", "frameId",
    "x", "y", "chip", "down", "yardsToGo", "couverture",
]

SUMMARY_COLUMNS = [
    "nflId", "nom", "poste", "equipe",
    "nb_chips", "nb_sans_chip",
    "profondeur_chip", "profondeur_sans_chip",
    "separation_chip", "separation_sans_chip",
    "pression_chip", "pression_sans_chip",
    "verdict",
]

# --- Joueurs factices --------------------------------------------------------
# Chaque joueur a un "profil" de chip :
#   - efficacite : facteur de récupération de profondeur après le chip
#                  (1.0 = récupère tout, <1 = perd de la profondeur).
#   Il module la profondeur du trajet chip pour produire des verdicts variés.
PLAYERS = [
    {"nflId": 40001, "nom": "Travis Kelsey", "poste": "TE", "equipe": "KC", "efficacite": 0.95},
    {"nflId": 40002, "nom": "Austin Eckler", "poste": "RB", "equipe": "LAC", "efficacite": 0.70},
    {"nflId": 40003, "nom": "Deebo Sampson", "poste": "WR", "equipe": "SF", "efficacite": 0.92},
    {"nflId": 40004, "nom": "George Kettle", "poste": "TE", "equipe": "SF", "efficacite": 0.78},
]

COUVERTURES = ["Cover-1", "Cover-3"]
YARDS_TO_GO = [2, 6, 10]

RNG = np.random.default_rng(42)


def _chip_route(n_frames: int, efficacite: float = 0.85) -> tuple[np.ndarray, np.ndarray]:
    """Trajet AVEC chip : petit crochet latéral vers un défenseur puis profondeur.

    Le crochet initial crée un retard : le joueur gagne du terrain en profondeur
    plus tard et moins loin que sur un trajet direct. ``efficacite`` module la
    profondeur finale récupérée (plus elle est haute, moins le chip coûte).
    """
    t = np.linspace(0.0, 1.0, n_frames)

    # Phase de crochet (~30 % du trajet) : part latéralement, peu de profondeur.
    hook_frac = 0.30
    lateral_amp = RNG.uniform(1.8, 2.6)  # amplitude du crochet en yards

    # Profondeur : lente au début (chip), puis accélère. L'efficacité du joueur
    # détermine jusqu'où il remonte après le crochet.
    max_depth = RNG.uniform(14.0, 18.0) * efficacite
    depth = max_depth * (t ** 1.8)  # courbe convexe -> départ lent

    # Latéral : crochet vers le défenseur puis retour et dérive.
    y = np.where(
        t < hook_frac,
        lateral_amp * np.sin(np.pi * t / hook_frac),      # bosse latérale
        lateral_amp * 0.3 * np.sin(np.pi * t / hook_frac),  # dérive résiduelle
    )
    noise = RNG.normal(0.0, 0.12, size=n_frames)
    return depth, y + noise


def _no_chip_route(n_frames: int) -> tuple[np.ndarray, np.ndarray]:
    """Trajet SANS chip : file plus directement et plus loin en profondeur."""
    t = np.linspace(0.0, 1.0, n_frames)

    max_depth = RNG.uniform(15.0, 19.0)   # va plus loin
    depth = max_depth * (t ** 1.1)        # quasi linéaire -> part tout de suite

    lateral_amp = RNG.uniform(0.6, 1.2)   # dérive latérale douce
    y = lateral_amp * t
    noise = RNG.normal(0.0, 0.10, size=n_frames)
    return depth, y + noise


def build_routes() -> pd.DataFrame:
    """Construit le DataFrame routes.csv (une ligne par frame)."""
    rows: list[dict] = []
    game_id = 2021091200
    play_counter = 0

    for player in PLAYERS:
        # Plusieurs trajets chip et sans chip par joueur. Le RB a un faible
        # volume (échantillon insuffisant -> verdict "pas assez de données").
        if player["poste"] == "RB":
            n_chip = int(RNG.integers(1, 3))
            n_plain = int(RNG.integers(1, 3))
        else:
            n_chip = int(RNG.integers(3, 6))
            n_plain = int(RNG.integers(3, 6))

        specs = [(True, n_chip), (False, n_plain)]
        for is_chip, n_routes in specs:
            for _ in range(n_routes):
                play_counter += 1
                play_id = 100 + play_counter
                n_frames = int(RNG.integers(15, 31))  # ~15 à 30 frames
                down = int(RNG.integers(1, 5))
                yards_to_go = int(RNG.choice(YARDS_TO_GO))
                couverture = str(RNG.choice(COUVERTURES))

                if is_chip:
                    depth, lateral = _chip_route(n_frames, player["efficacite"])
                else:
                    depth, lateral = _no_chip_route(n_frames)

                for frame_idx in range(n_frames):
                    rows.append({
                        "gameId": game_id,
                        "playId": play_id,
                        "nflId": player["nflId"],
                        "frameId": frame_idx + 1,
                        # x normalisé : ligne de mêlée = 0, profondeur en aval.
                        "x": round(float(depth[frame_idx]), 3),
                        "y": round(float(lateral[frame_idx]), 3),
                        "chip": bool(is_chip),
                        "down": down,
                        "yardsToGo": yards_to_go,
                        "couverture": couverture,
                    })

    df = pd.DataFrame(rows, columns=ROUTES_COLUMNS)
    return df


def build_summary(routes: pd.DataFrame) -> pd.DataFrame:
    """Construit player_summary.csv à partir des trajets générés."""
    rows: list[dict] = []

    for player in PLAYERS:
        pid = player["nflId"]
        sub = routes[routes["nflId"] == pid]

        chip_plays = sub[sub["chip"]].groupby("playId")
        plain_plays = sub[~sub["chip"]].groupby("playId")

        nb_chips = chip_plays.ngroups
        nb_sans_chip = plain_plays.ngroups

        # Profondeur = profondeur max atteinte (x) moyennée sur les trajets.
        prof_chip = round(float(chip_plays["x"].max().mean()), 2) if nb_chips else 0.0
        prof_plain = round(float(plain_plays["x"].max().mean()), 2) if nb_sans_chip else 0.0

        eff = player["efficacite"]

        # Séparation factice plausible : un peu plus faible après un chip,
        # d'autant plus récupérée que le joueur est efficace.
        sep_chip = round(float(RNG.uniform(1.8, 2.4) + 0.8 * eff), 2)
        sep_plain = round(float(RNG.uniform(2.6, 3.6)), 2)

        # Pression factice (taux 0-1) : chipper aide la protection -> moins de
        # pression côté chip. Un joueur efficace fait encore mieux baisser.
        pres_chip = round(float(RNG.uniform(0.08, 0.16) + 0.10 * (1 - eff)), 3)
        pres_plain = round(float(RNG.uniform(0.22, 0.34)), 3)

        # Verdict simple : le chip est "rentable" s'il réduit nettement la
        # pression sans trop sacrifier la profondeur ; sinon "pas rentable".
        # (seuils calibrés pour obtenir un mélange plausible de verdicts)
        gain_pression = pres_plain - pres_chip
        cout_profondeur = prof_plain - prof_chip
        if nb_chips < 3 or nb_sans_chip < 3:
            verdict = "pas assez de données"
        elif gain_pression >= 0.08 and cout_profondeur < 4.5:
            verdict = "rentable"
        else:
            verdict = "pas rentable"

        rows.append({
            "nflId": pid,
            "nom": player["nom"],
            "poste": player["poste"],
            "equipe": player["equipe"],
            "nb_chips": nb_chips,
            "nb_sans_chip": nb_sans_chip,
            "profondeur_chip": prof_chip,
            "profondeur_sans_chip": prof_plain,
            "separation_chip": sep_chip,
            "separation_sans_chip": sep_plain,
            "pression_chip": pres_chip,
            "pression_sans_chip": pres_plain,
            "verdict": verdict,
        })

    df = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    return df


def _validate(routes: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Contrôle que chaque colonne du contrat est présente et dans l'ordre."""
    assert list(routes.columns) == ROUTES_COLUMNS, (
        f"Colonnes routes.csv inattendues : {list(routes.columns)}"
    )
    assert list(summary.columns) == SUMMARY_COLUMNS, (
        f"Colonnes player_summary.csv inattendues : {list(summary.columns)}"
    )
    assert len(routes) > 0, "routes.csv est vide"
    assert len(summary) > 0, "player_summary.csv est vide"
    assert set(summary["verdict"]).issubset(
        {"rentable", "pas rentable", "pas assez de données"}
    ), "verdict hors contrat"


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    routes = build_routes()
    summary = build_summary(routes)

    # Contrôle du contrat CSV avant écriture.
    _validate(routes, summary)

    # Écriture idempotente (réécrit proprement à chaque exécution).
    routes.to_csv(ROUTES_PATH, index=False)
    summary.to_csv(SUMMARY_PATH, index=False)

    print("=== Génération des faux CSV terminée ===")
    print(f"routes.csv          -> {ROUTES_PATH}")
    print(f"  lignes : {len(routes):>5}  | colonnes : {len(routes.columns)}")
    print(f"  joueurs : {routes['nflId'].nunique()}  | trajets : {routes.groupby(['nflId', 'playId']).ngroups}")
    print(f"player_summary.csv  -> {SUMMARY_PATH}")
    print(f"  lignes : {len(summary):>5}  | colonnes : {len(summary.columns)}")
    print(f"  verdicts : {dict(summary['verdict'].value_counts())}")


if __name__ == "__main__":
    main()
