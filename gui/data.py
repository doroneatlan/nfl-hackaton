#!/usr/bin/env python3
"""Chargement et agrégation des CSV de results/ pour l'interface PySide6.

L'interface ne lit JAMAIS les 811 Mo bruts : elle s'appuie uniquement sur les
CSV légers produits par le pipeline (ou par src/fake_data.py) :

  - results/player_summary.csv : une ligne par joueur (verdict chip)
  - results/routes.csv         : trajets frame-par-frame (dessin terrain)

Toutes les fonctions sont tolérantes aux fichiers absents : elles renvoient des
DataFrames vides plutôt que de lever une exception, pour que l'app démarre même
sans données.
"""

from __future__ import annotations

import os

import pandas as pd

# results/ est à la racine du dépôt ; ce fichier est dans gui/.
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(GUI_DIR)
RESULTS_DIR = os.path.join(REPO_ROOT, "results")

SUMMARY_PATH = os.path.join(RESULTS_DIR, "player_summary.csv")
ROUTES_PATH = os.path.join(RESULTS_DIR, "routes.csv")

# Libellés de verdict connus (du contrat CSV).
VERDICT_RENTABLE = "rentable"
VERDICT_PAS_RENTABLE = "pas rentable"
VERDICT_PAS_ASSEZ = "pas assez de données"

# Couleurs partagées avec le reste du projet.
COULEUR_CHIP = "#d62728"       # rouge : avec chip
COULEUR_SANS_CHIP = "#1f77b4"  # bleu : sans chip

COULEURS_VERDICT = {
    VERDICT_RENTABLE: "#1a7f37",
    VERDICT_PAS_RENTABLE: "#cf222e",
    VERDICT_PAS_ASSEZ: "#9a6700",
}


def charger_summary() -> pd.DataFrame:
    """Charge player_summary.csv ; DataFrame vide si absent."""
    if not os.path.exists(SUMMARY_PATH):
        return pd.DataFrame()
    return pd.read_csv(SUMMARY_PATH)


def charger_routes() -> pd.DataFrame:
    """Charge routes.csv ; DataFrame vide si absent.

    Normalise la colonne ``chip`` en booléen (robuste au parsing CSV qui peut
    livrer "True"/"False" en chaînes).
    """
    if not os.path.exists(ROUTES_PATH):
        return pd.DataFrame()
    df = pd.read_csv(ROUTES_PATH)
    if "chip" in df.columns:
        df["chip"] = _normaliser_chip(df["chip"])
    return df


def _normaliser_chip(serie: pd.Series) -> pd.Series:
    """Normalise une colonne chip en booléen (accepte bool, "True"/"False", 1/0)."""
    if serie.dtype == bool:
        return serie
    vrais = {"true", "1", "oui", "yes", "vrai"}

    def _vers_bool(v):
        if isinstance(v, bool):
            return v
        if pd.isna(v):
            return False
        if isinstance(v, (int, float)):
            return bool(v)
        return str(v).strip().lower() in vrais

    return serie.map(_vers_bool).astype(bool)


def liste_equipes(summary: pd.DataFrame) -> list[str]:
    """Renvoie la liste triée des équipes présentes dans le résumé joueur."""
    if summary.empty or "equipe" not in summary.columns:
        return []
    return sorted(summary["equipe"].dropna().unique().tolist())


def joueurs_de_equipe(summary: pd.DataFrame, equipe: str) -> pd.DataFrame:
    """Filtre le résumé sur une équipe, verdicts rentables d'abord."""
    if summary.empty or "equipe" not in summary.columns:
        return summary
    df = summary[summary["equipe"] == equipe].copy()
    if "verdict" in df.columns:
        ordre = {
            VERDICT_RENTABLE: 0,
            VERDICT_PAS_RENTABLE: 1,
            VERDICT_PAS_ASSEZ: 2,
        }
        df["_o"] = df["verdict"].str.lower().map(ordre).fillna(3)
        df = df.sort_values(["_o", "nom"]).drop(columns="_o")
    return df.reset_index(drop=True)


def stats_equipe(summary: pd.DataFrame, equipe: str) -> dict:
    """Agrège des indicateurs d'équipe à partir du résumé joueur.

    Renvoie un dictionnaire avec le nombre de joueurs, les totaux de chips, les
    moyennes de profondeur/pression chip vs sans chip et le décompte des
    verdicts. Les moyennes sont pondérées par le nombre d'actions quand c'est
    pertinent, sinon par joueur. Dictionnaire vide si l'équipe est absente.
    """
    df = joueurs_de_equipe(summary, equipe)
    if df.empty:
        return {}

    def _moyenne(col: str) -> float | None:
        if col not in df.columns:
            return None
        valeurs = df[col].dropna()
        return float(valeurs.mean()) if not valeurs.empty else None

    verdicts = {}
    if "verdict" in df.columns:
        verdicts = df["verdict"].str.lower().value_counts().to_dict()

    return {
        "nb_joueurs": int(len(df)),
        "nb_chips": int(df["nb_chips"].sum()) if "nb_chips" in df.columns else 0,
        "nb_sans_chip": int(df["nb_sans_chip"].sum()) if "nb_sans_chip" in df.columns else 0,
        "profondeur_chip": _moyenne("profondeur_chip"),
        "profondeur_sans_chip": _moyenne("profondeur_sans_chip"),
        "pression_chip": _moyenne("pression_chip"),
        "pression_sans_chip": _moyenne("pression_sans_chip"),
        "separation_chip": _moyenne("separation_chip"),
        "separation_sans_chip": _moyenne("separation_sans_chip"),
        "verdicts": verdicts,
    }
