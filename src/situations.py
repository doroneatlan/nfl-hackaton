#!/usr/bin/env python3
"""Graphique de rentabilité du chip par situation ("Le coût du chip").

Croise la **distance à franchir** (``yardsToGo`` bucketisée) et la
**couverture défensive** pour montrer dans quelles situations le chip coûte
peu de profondeur — donc reste intéressant — et dans lesquelles il pénalise
le receveur.

Le "coût du chip" d'une situation est défini comme :

    coût = profondeur_moyenne_SANS_chip - profondeur_moyenne_AVEC_chip   (yards)

Un coût faible (voire négatif) = le chip ne sacrifie quasiment pas de
profondeur dans cette situation : il y est plutôt rentable. Un coût élevé =
le chip coûte cher en profondeur.

La profondeur d'un trajet est la coordonnée ``x`` maximale atteinte (x
normalisé, ligne de mêlée = 0).

Usage :
    import pandas as pd
    from src.situations import graphique_situations
    fig = graphique_situations(pd.read_csv("results/routes.csv"))
    fig.show()
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# Ordre d'affichage des buckets yardsToGo (du plus court au plus long).
BUCKETS_ORDRE = ["court", "moyen", "long"]

# Noms de colonne acceptés pour la couverture défensive. Le contrat du projet
# utilise "couverture" ; le jeu de données NFL d'origine utilise
# "pff_passCoverage". On accepte les deux.
COLONNES_COUVERTURE = ["couverture", "pff_passCoverage"]


def bucket_yards(y) -> str:
    """Bucketise une valeur ``yardsToGo`` en catégorie de distance.

    - "court" : <= 3 yards
    - "moyen" : 4 à 7 yards
    - "long"  : >= 8 yards

    Les valeurs non numériques ou manquantes renvoient ``"inconnu"``.
    """
    if y is None:
        return "inconnu"
    try:
        v = float(y)
    except (TypeError, ValueError):
        return "inconnu"
    if pd.isna(v):
        return "inconnu"
    if v <= 3:
        return "court"
    if v <= 7:
        return "moyen"
    return "long"


def _normaliser_chip(serie: pd.Series) -> pd.Series:
    """Normalise la colonne ``chip`` en booléen.

    Accepte les booléens natifs ainsi que les chaînes "True"/"False"
    (insensibles à la casse et aux espaces), "1"/"0", "oui"/"non".
    """
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


def _trouver_colonne_couverture(df: pd.DataFrame) -> str | None:
    """Renvoie le nom de la colonne de couverture présente, sinon ``None``."""
    for col in COLONNES_COUVERTURE:
        if col in df.columns:
            return col
    return None


def _figure_placeholder(message: str) -> go.Figure:
    """Figure vide portant une annotation explicative (aucune donnée exploitable)."""
    fig = go.Figure()
    fig.update_layout(
        title="Coût du chip par situation",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16},
            }
        ],
    )
    return fig


def profondeurs_par_trajet(routes_df: pd.DataFrame) -> pd.DataFrame:
    """Réduit les frames en un enregistrement par trajet.

    Groupe par (gameId, playId, nflId) et calcule la profondeur atteinte
    (``x`` max) ainsi que le statut chip et, si disponibles, le bucket
    yardsToGo et la couverture.

    Renvoie un DataFrame avec au moins les colonnes ``profondeur`` et
    ``chip``, plus ``bucket`` et/ou ``couverture`` quand les données le
    permettent.
    """
    df = routes_df.copy()

    cles = [c for c in ("gameId", "playId", "nflId") if c in df.columns]
    if not cles:
        # Sans clé de regroupement, on traite chaque ligne comme un trajet.
        df["_trajet"] = range(len(df))
        cles = ["_trajet"]

    df["chip"] = _normaliser_chip(df["chip"])

    agg = {"x": "max", "chip": "first"}
    col_couv = _trouver_colonne_couverture(df)
    if "yardsToGo" in df.columns:
        agg["yardsToGo"] = "first"
    if col_couv is not None:
        agg[col_couv] = "first"

    groupe = df.groupby(cles, as_index=False).agg(agg)
    groupe = groupe.rename(columns={"x": "profondeur"})

    if "yardsToGo" in groupe.columns:
        groupe["bucket"] = groupe["yardsToGo"].map(bucket_yards)
    if col_couv is not None:
        groupe = groupe.rename(columns={col_couv: "couverture"})
        groupe["couverture"] = groupe["couverture"].fillna("inconnue").astype(str)

    return groupe


def graphique_situations(routes_df: pd.DataFrame) -> go.Figure:
    """Construit la heatmap du coût du chip par situation.

    Axes : bucket yardsToGo (x) × couverture (y).
    Couleur : coût du chip en yards (sans chip − avec chip). Plus c'est froid
    (bas), moins le chip pénalise ; plus c'est chaud (haut), plus il coûte.

    Robuste : regroupe sur les dimensions disponibles ; si rien n'est
    exploitable, renvoie une figure placeholder annotée plutôt que de crasher.
    """
    if routes_df is None or len(routes_df) == 0 or "chip" not in routes_df.columns:
        return _figure_placeholder(
            "Aucune donnée exploitable pour analyser le coût du chip."
        )

    trajets = profondeurs_par_trajet(routes_df)

    a_bucket = "bucket" in trajets.columns
    a_couv = "couverture" in trajets.columns

    # Dimensions de regroupement effectivement disponibles.
    dims = []
    if a_couv:
        dims.append("couverture")
    if a_bucket:
        dims.append("bucket")

    if not dims:
        # Ni couverture ni yardsToGo : on retombe sur un comparatif global.
        return _cout_global(trajets)

    # Profondeur moyenne par (dimensions..., chip).
    pivot = (
        trajets.groupby(dims + ["chip"])["profondeur"].mean().reset_index()
    )

    # Sépare chip / sans chip puis fusionne pour calculer le coût.
    avec = pivot[pivot["chip"]].drop(columns="chip").rename(
        columns={"profondeur": "prof_chip"}
    )
    sans = pivot[~pivot["chip"]].drop(columns="chip").rename(
        columns={"profondeur": "prof_sans"}
    )
    fusion = pd.merge(avec, sans, on=dims, how="outer")

    if fusion.empty:
        return _figure_placeholder(
            "Pas de trajets exploitables pour comparer chip vs sans chip."
        )

    fusion["cout"] = fusion["prof_sans"] - fusion["prof_chip"]

    # Cas 2D : couverture × bucket -> heatmap.
    if a_couv and a_bucket:
        return _heatmap_2d(fusion)

    # Cas 1D : une seule dimension disponible -> barres.
    dim = dims[0]
    return _barres_1d(fusion, dim)


def _ordonner_buckets(valeurs) -> list[str]:
    """Ordonne les buckets selon BUCKETS_ORDRE, les inconnus à la fin."""
    presents = list(dict.fromkeys(valeurs))
    connus = [b for b in BUCKETS_ORDRE if b in presents]
    autres = [b for b in presents if b not in BUCKETS_ORDRE]
    return connus + autres


def _heatmap_2d(fusion: pd.DataFrame) -> go.Figure:
    """Heatmap couverture (y) × bucket yardsToGo (x), couleur = coût (yards)."""
    buckets = _ordonner_buckets(fusion["bucket"].tolist())
    couvertures = sorted(fusion["couverture"].unique().tolist())

    grille = fusion.pivot(index="couverture", columns="bucket", values="cout")
    grille = grille.reindex(index=couvertures, columns=buckets)

    z = grille.values
    texte = [
        [
            "n/a" if pd.isna(val) else f"{val:+.1f} yd"
            for val in ligne
        ]
        for ligne in z
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=buckets,
            y=couvertures,
            colorscale="RdYlGn_r",  # vert = coût faible (bon), rouge = coût élevé
            colorbar={"title": "Coût du chip<br>(yards perdus)"},
            text=texte,
            texttemplate="%{text}",
            textfont={"size": 14},
            hovertemplate=(
                "Couverture : %{y}<br>"
                "Distance : %{x}<br>"
                "Coût du chip : %{z:+.1f} yards<extra></extra>"
            ),
            zmid=0,
        )
    )
    fig.update_layout(
        title=(
            "Coût du chip par situation — profondeur sacrifiée (yards)<br>"
            "<sub>Vert = chip peu pénalisant (intéressant) · "
            "Rouge = chip coûteux en profondeur</sub>"
        ),
        xaxis_title="Distance à franchir (yardsToGo)",
        yaxis_title="Couverture défensive",
    )
    return fig


def _barres_1d(fusion: pd.DataFrame, dim: str) -> go.Figure:
    """Barres groupées profondeur chip vs sans chip le long d'une dimension."""
    if dim == "bucket":
        ordre = _ordonner_buckets(fusion["bucket"].tolist())
        fusion = fusion.set_index("bucket").reindex(ordre).reset_index()
        titre_x = "Distance à franchir (yardsToGo)"
    else:
        fusion = fusion.sort_values(dim)
        titre_x = "Couverture défensive"

    categories = fusion[dim].tolist()

    fig = go.Figure()
    fig.add_bar(
        name="Sans chip",
        x=categories,
        y=fusion["prof_sans"],
        marker_color="#1f77b4",
        hovertemplate="Sans chip : %{y:.1f} yards<extra></extra>",
    )
    fig.add_bar(
        name="Avec chip",
        x=categories,
        y=fusion["prof_chip"],
        marker_color="#ff7f0e",
        hovertemplate="Avec chip : %{y:.1f} yards<extra></extra>",
    )
    # Annoter le coût au-dessus de chaque situation.
    for _, row in fusion.iterrows():
        if pd.notna(row.get("cout")):
            fig.add_annotation(
                x=row[dim],
                y=max(
                    v for v in (row.get("prof_chip"), row.get("prof_sans"))
                    if pd.notna(v)
                ),
                text=f"coût {row['cout']:+.1f} yd",
                showarrow=False,
                yshift=14,
                font={"size": 12},
            )

    fig.update_layout(
        barmode="group",
        title=(
            "Coût du chip par situation — profondeur atteinte (yards)<br>"
            "<sub>Coût = profondeur sans chip − profondeur avec chip</sub>"
        ),
        xaxis_title=titre_x,
        yaxis_title="Profondeur moyenne atteinte (yards)",
        legend_title="Trajet",
    )
    return fig


def _cout_global(trajets: pd.DataFrame) -> go.Figure:
    """Comparatif global chip vs sans chip (aucune dimension de situation)."""
    moyennes = trajets.groupby("chip")["profondeur"].mean()
    prof_chip = float(moyennes.get(True, float("nan")))
    prof_sans = float(moyennes.get(False, float("nan")))

    if pd.isna(prof_chip) or pd.isna(prof_sans):
        return _figure_placeholder(
            "Impossible de comparer chip vs sans chip (une catégorie manque)."
        )

    cout = prof_sans - prof_chip
    fig = go.Figure(
        data=go.Bar(
            x=["Sans chip", "Avec chip"],
            y=[prof_sans, prof_chip],
            marker_color=["#1f77b4", "#ff7f0e"],
            text=[f"{prof_sans:.1f} yd", f"{prof_chip:.1f} yd"],
            textposition="auto",
        )
    )
    fig.update_layout(
        title=(
            "Coût du chip (vue globale) — profondeur atteinte (yards)<br>"
            f"<sub>Coût moyen du chip : {cout:+.1f} yards "
            "(données de situation indisponibles)</sub>"
        ),
        xaxis_title="Type de trajet",
        yaxis_title="Profondeur moyenne atteinte (yards)",
    )
    return fig
