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

# Libellés lisibles des buckets sur l'axe.
BUCKETS_LIBELLES = {
    "court": "Courte<br>(1–3 yd)",
    "moyen": "Moyenne<br>(4–7 yd)",
    "long": "Longue<br>(8+ yd)",
    "inconnu": "Inconnue",
}

# En dessous de ce nombre de trajets (avec chip OU sans chip) dans une case,
# la moyenne n'est pas fiable : la case est grisée au lieu d'être colorée.
MIN_TRAJETS_PAR_CASE = 8

POLICE = "Inter, 'Source Sans 3', 'Segoe UI', sans-serif"
COULEUR_TEXTE = "#1f2328"
COULEUR_TEXTE_DOUX = "#57606a"
COULEUR_CASE_VIDE = "#eef0f2"

# Échelle séquentielle : vert = chip peu coûteux, rouge = chip coûteux.
ECHELLE_COUT = [
    [0.0, "#1a9850"],
    [0.25, "#91cf60"],
    [0.5, "#fee08b"],
    [0.75, "#fc8d59"],
    [1.0, "#d73027"],
]

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

    # Profondeur moyenne et nombre de trajets par (dimensions..., chip).
    pivot = (
        trajets.groupby(dims + ["chip"])["profondeur"]
        .agg(profondeur="mean", n="count")
        .reset_index()
    )

    # Sépare chip / sans chip puis fusionne pour calculer le coût.
    avec = pivot[pivot["chip"]].drop(columns="chip").rename(
        columns={"profondeur": "prof_chip", "n": "n_chip"}
    )
    sans = pivot[~pivot["chip"]].drop(columns="chip").rename(
        columns={"profondeur": "prof_sans", "n": "n_sans"}
    )
    fusion = pd.merge(avec, sans, on=dims, how="outer")
    fusion[["n_chip", "n_sans"]] = fusion[["n_chip", "n_sans"]].fillna(0).astype(int)

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


def _n_chips(n: int) -> str:
    """'1 chip', '8 chips' (accord du pluriel)."""
    return f"{n} chip" if n == 1 else f"{n} chips"


def _layout_commun(fig: go.Figure, titre: str, sous_titre: str) -> None:
    """Mise en forme partagée : police, titre + sous-titre, fond blanc."""
    fig.update_layout(
        title=dict(
            text=(
                f"{titre}<br><span style='font-size:13px;color:{COULEUR_TEXTE_DOUX}'>"
                f"{sous_titre}</span>"
            ),
            x=0, xanchor="left",
            font=dict(size=18, color=COULEUR_TEXTE, family=POLICE),
        ),
        font=dict(family=POLICE, color=COULEUR_TEXTE, size=13),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel=dict(font=dict(family=POLICE)),
    )


def _heatmap_2d(fusion: pd.DataFrame) -> go.Figure:
    """Heatmap couverture (y) × distance (x), couleur = coût du chip (yards).

    Les cases avec moins de ``MIN_TRAJETS_PAR_CASE`` trajets avec chip ou
    sans chip sont grisées ; les couvertures sans aucune case fiable sont
    retirées et listées en note. Les couvertures les plus fréquentes sont en
    haut.
    """
    fusion = fusion.copy()
    fusion["fiable"] = (
        (fusion["n_chip"] >= MIN_TRAJETS_PAR_CASE)
        & (fusion["n_sans"] >= MIN_TRAJETS_PAR_CASE)
        & fusion["cout"].notna()
    )

    buckets = _ordonner_buckets(fusion["bucket"].tolist())

    # Couvertures gardées : au moins une case fiable ; triées par volume de chips.
    volume = fusion.groupby("couverture")["n_chip"].sum()
    fiables = fusion.groupby("couverture")["fiable"].any()
    gardees = volume[fiables.reindex(volume.index, fill_value=False)]
    ecartees = sorted(set(volume.index) - set(gardees.index))

    if gardees.empty:
        return _figure_placeholder(
            "Pas assez de trajets par situation pour une comparaison fiable "
            f"(minimum {MIN_TRAJETS_PAR_CASE} avec et sans chip)."
        )

    # Plotly dessine la 1re ligne en bas : on inverse pour avoir la plus
    # fréquente en haut.
    couvertures = gardees.sort_values(ascending=True).index.tolist()

    def _grille(col: str) -> pd.DataFrame:
        return (
            fusion.pivot(index="couverture", columns="bucket", values=col)
            .reindex(index=couvertures, columns=buckets)
        )

    cout = _grille("cout")
    fiable = _grille("fiable").fillna(False).astype(bool)
    n_chip = _grille("n_chip").fillna(0).astype(int)
    n_sans = _grille("n_sans").fillna(0).astype(int)

    z = cout.where(fiable)  # cases non fiables -> NaN (non colorées)
    z_valeurs = z.to_numpy(dtype=float)
    valides = z_valeurs[~pd.isna(z_valeurs)]
    zmin = float(min(0.0, valides.min()))
    zmax = float(max(valides.max(), zmin + 1.0))

    texte = []
    for i in range(len(couvertures)):
        ligne = []
        for j in range(len(buckets)):
            nc, ns = n_chip.iat[i, j], n_sans.iat[i, j]
            if fiable.iat[i, j]:
                ligne.append(
                    f"<b>{cout.iat[i, j]:+.1f} yd</b><br>"
                    f"<span style='font-size:11px'>{_n_chips(nc)}</span>"
                )
            elif nc + ns > 0:
                ligne.append(
                    f"<span style='font-size:11px'>peu de données<br>{_n_chips(nc)}</span>"
                )
            else:
                ligne.append("<span style='font-size:11px'>aucune action</span>")
        texte.append(ligne)

    custom = [
        [[n_chip.iat[i, j], n_sans.iat[i, j]] for j in range(len(buckets))]
        for i in range(len(couvertures))
    ]

    libelles_x = [BUCKETS_LIBELLES.get(b, b) for b in buckets]

    fig = go.Figure()
    # Fond gris pour toutes les cases (visible là où la heatmap est vide).
    fig.add_trace(
        go.Heatmap(
            z=[[0] * len(buckets) for _ in couvertures],
            x=libelles_x,
            y=couvertures,
            colorscale=[[0, COULEUR_CASE_VIDE], [1, COULEUR_CASE_VIDE]],
            showscale=False,
            xgap=4, ygap=4,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Heatmap(
            z=z_valeurs,
            x=libelles_x,
            y=couvertures,
            zmin=zmin, zmax=zmax,
            colorscale=ECHELLE_COUT,
            colorbar=dict(
                title=dict(text="Yards perdus<br>avec un chip", side="top"),
                ticksuffix=" yd",
                thickness=14,
                len=0.8,
                outlinewidth=0,
            ),
            xgap=4, ygap=4,
            customdata=custom,
            hovertemplate=(
                "<b>%{y}</b> · distance %{x}<br>"
                "Coût du chip : %{z:+.1f} yards<br>"
                "%{customdata[0]} trajets avec chip · "
                "%{customdata[1]} sans chip<extra></extra>"
            ),
            hoverongaps=False,
        )
    )
    # Texte des cases (y compris les cases grisées) via une trace scatter.
    fig.add_trace(
        go.Scatter(
            x=[libelles_x[j] for i in range(len(couvertures)) for j in range(len(buckets))],
            y=[couvertures[i] for i in range(len(couvertures)) for _ in buckets],
            mode="text",
            text=[t for ligne in texte for t in ligne],
            textfont=dict(size=14, color=COULEUR_TEXTE, family=POLICE),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    note = (
        f"Cases grises : moins de {MIN_TRAJETS_PAR_CASE} trajets avec ou sans chip."
    )
    if ecartees:
        note += f" Couvertures retirées (trop rares) : {', '.join(ecartees)}."

    _layout_commun(
        fig,
        "Combien de yards de route le chip coûte, selon la situation",
        "Coût = profondeur moyenne sans chip − avec chip · "
        "vert = chip peu pénalisant, rouge = chip coûteux",
    )
    fig.update_layout(
        height=max(420, 230 + 62 * len(couvertures)),
        margin=dict(l=130, r=20, t=90, b=130),
        annotations=[
            dict(
                text=note,
                xref="paper", yref="paper",
                x=0, y=0, yanchor="top", xanchor="left",
                yshift=-100,
                showarrow=False,
                font=dict(size=12, color=COULEUR_TEXTE_DOUX),
            )
        ],
    )
    fig.update_xaxes(
        title_text="Distance à franchir pour le 1er down",
        title_standoff=14,
        side="bottom",
        showgrid=False, zeroline=False, ticks="",
        tickfont=dict(size=13),
        automargin=True,
    )
    fig.update_yaxes(
        title_text="Couverture défensive",
        title_standoff=12,
        showgrid=False, zeroline=False, ticks="",
        tickfont=dict(size=13),
        ticksuffix="   ",
        automargin=True,
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
        marker_color="#3a86ff",
        hovertemplate="Sans chip : %{y:.1f} yards<extra></extra>",
    )
    fig.add_bar(
        name="Avec chip",
        x=categories,
        y=fusion["prof_chip"],
        marker_color="#e63946",
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

    _layout_commun(
        fig,
        "Profondeur atteinte avec et sans chip, selon la situation",
        "Coût = profondeur moyenne sans chip − avec chip",
    )
    fig.update_layout(
        barmode="group",
        bargap=0.3,
        xaxis_title=titre_x,
        yaxis_title="Profondeur moyenne atteinte (yards)",
        legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"),
        margin=dict(l=20, r=20, t=90, b=40),
    )
    fig.update_yaxes(gridcolor="#eef0f2", zeroline=False)
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
            marker_color=["#3a86ff", "#e63946"],
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
