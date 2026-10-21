#!/usr/bin/env python3
"""Interface Streamlit — "Le coût du chip" (NFL Big Data Bowl).

L'app lit UNIQUEMENT les CSV légers de results/ (jamais les 811 Mo bruts) :
  - results/player_summary.csv : une ligne par joueur (verdict chip)
  - results/routes.csv         : trajets frame-par-frame (dessin terrain)

Pages :
  1. Vue d'ensemble  : tableau des joueurs + verdict, filtres équipe / poste
  2. Fiche joueur    : chiffres clés chip vs sans chip + terrain (field.py)
  3. Situations      : rentabilité du chip par distance × couverture (situations.py)

Lancement :
    streamlit run app.py

NOTE DE COORDINATION : ce fichier est partagé avec la Personne 2 (interface).
Les graphiques (terrain + situations) sont branchés par la Personne 3 via les
modules src/field.py et src/situations.py.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st

# Rendre src/ importable sans installation (cohérent avec les tests).
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from field import dessiner_trajets  # noqa: E402
from situations import graphique_situations  # noqa: E402

RESULTS_DIR = os.path.join(REPO_ROOT, "results")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "player_summary.csv")
ROUTES_PATH = os.path.join(RESULTS_DIR, "routes.csv")

COULEURS_VERDICT = {
    "rentable": "#1a7f37",
    "pas rentable": "#cf222e",
    "pas assez de données": "#9a6700",
}


# --- Chargement des données --------------------------------------------------
@st.cache_data
def charger_summary() -> pd.DataFrame:
    """Charge player_summary.csv ; DataFrame vide si absent (tolérant)."""
    if not os.path.exists(SUMMARY_PATH):
        return pd.DataFrame()
    return pd.read_csv(SUMMARY_PATH)


@st.cache_data
def charger_routes() -> pd.DataFrame:
    """Charge routes.csv ; DataFrame vide si absent (tolérant)."""
    if not os.path.exists(ROUTES_PATH):
        return pd.DataFrame()
    return pd.read_csv(ROUTES_PATH)


def _style_verdict(valeur: str) -> str:
    """Couleur de fond de la cellule verdict (pour le tableau stylé)."""
    couleur = COULEURS_VERDICT.get(str(valeur).strip().lower(), "#6e7781")
    return f"background-color: {couleur}; color: white;"


# --- Page 1 : Vue d'ensemble -------------------------------------------------
def page_vue_ensemble(summary: pd.DataFrame) -> None:
    st.header("Vue d'ensemble")
    st.caption("Qui gagne à faire des chips, en un coup d'œil.")

    if summary.empty:
        st.warning(
            "Aucune donnée dans results/player_summary.csv. "
            "Lance `python src/fake_data.py` ou attends les vrais CSV."
        )
        return

    # Filtres équipe / poste (tolérants aux colonnes absentes).
    cols = st.columns(2)
    df = summary.copy()
    if "equipe" in df.columns:
        equipes = ["(toutes)"] + sorted(df["equipe"].dropna().unique().tolist())
        choix_equipe = cols[0].selectbox("Équipe", equipes)
        if choix_equipe != "(toutes)":
            df = df[df["equipe"] == choix_equipe]
    if "poste" in df.columns:
        postes = ["(tous)"] + sorted(df["poste"].dropna().unique().tolist())
        choix_poste = cols[1].selectbox("Poste", postes)
        if choix_poste != "(tous)":
            df = df[df["poste"] == choix_poste]

    # Tri : rentables d'abord.
    if "verdict" in df.columns:
        ordre = {"rentable": 0, "pas rentable": 1, "pas assez de données": 2}
        df = df.assign(_o=df["verdict"].str.lower().map(ordre).fillna(3))
        df = df.sort_values("_o").drop(columns="_o")

    if "verdict" in df.columns:
        st.dataframe(
            df.style.map(_style_verdict, subset=["verdict"]),
            width="stretch",
        )
    else:
        st.dataframe(df, width="stretch")


# --- Page 2 : Fiche joueur ---------------------------------------------------
def page_fiche_joueur(summary: pd.DataFrame, routes: pd.DataFrame) -> None:
    st.header("Fiche joueur")

    if summary.empty:
        st.warning("player_summary.csv absent ou vide.")
        return

    # Menu de sélection du joueur.
    if "nom" in summary.columns and "nflId" in summary.columns:
        options = summary[["nflId", "nom"]].drop_duplicates()
        label = options["nom"] + " (" + options["nflId"].astype(str) + ")"
        choix = st.selectbox("Joueur", options.index, format_func=lambda i: label.loc[i])
        ligne = summary.loc[choix]
        nfl_id = ligne["nflId"]
        st.subheader(str(ligne.get("nom", nfl_id)))
    else:
        nfl_id = st.selectbox("nflId", summary.get("nflId", pd.Series()).tolist())
        ligne = summary[summary["nflId"] == nfl_id].iloc[0]

    # Chiffres clés chip vs sans chip (tolérant aux colonnes vides, plan B).
    def _metric(col1, col2, titre, col_chip, col_sans, suffixe=""):
        v_chip = ligne.get(col_chip)
        v_sans = ligne.get(col_sans)
        txt_chip = "—" if pd.isna(v_chip) else f"{v_chip}{suffixe}"
        txt_sans = "—" if pd.isna(v_sans) else f"{v_sans}{suffixe}"
        col1.metric(f"{titre} — avec chip", txt_chip)
        col2.metric(f"{titre} — sans chip", txt_sans)

    if "verdict" in ligne:
        st.markdown(f"**Verdict : {ligne['verdict']}**")

    c1, c2 = st.columns(2)
    _metric(c1, c2, "Profondeur", "profondeur_chip", "profondeur_sans_chip", " yd")
    c3, c4 = st.columns(2)
    _metric(c3, c4, "Séparation", "separation_chip", "separation_sans_chip", " yd")
    c5, c6 = st.columns(2)
    _metric(c5, c6, "Pression QB", "pression_chip", "pression_sans_chip")

    # Terrain + trajets (module field.py de la Personne 3).
    st.subheader("Trajets sur le terrain")
    st.caption("🔵 sans chip · 🔴 avec chip")
    if routes.empty:
        st.info("routes.csv absent : le terrain ne peut pas être dessiné.")
    else:
        fig = dessiner_trajets(routes, nfl_id)
        st.plotly_chart(fig, width="stretch")


# --- Page 3 : Situations -----------------------------------------------------
def page_situations(routes: pd.DataFrame) -> None:
    st.header("Situations")
    st.caption("Dans quelles situations le chip coûte le moins de profondeur.")

    if routes.empty:
        st.warning("routes.csv absent ou vide.")
        return

    fig = graphique_situations(routes)
    st.plotly_chart(fig, width="stretch")


# --- App ---------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Le coût du chip", page_icon="🏈", layout="wide")
    st.title("🏈 Le coût du chip")

    summary = charger_summary()
    routes = charger_routes()

    page = st.sidebar.radio(
        "Navigation",
        ["Vue d'ensemble", "Fiche joueur", "Situations"],
    )

    if page == "Vue d'ensemble":
        page_vue_ensemble(summary)
    elif page == "Fiche joueur":
        page_fiche_joueur(summary, routes)
    else:
        page_situations(routes)


if __name__ == "__main__":
    main()
