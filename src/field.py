#!/usr/bin/env python3
"""Rendu du terrain et des trajets pour le projet "Le coût du chip".

100 % Python / Plotly (plotly.graph_objects). Repère utilisé :
  - x = profondeur (yards au-delà de la ligne de mêlée), ligne de mêlée = x=0
  - y = écart latéral (yards) par rapport au point de départ du joueur

Pour rester lisible avec des dizaines d'actions, chaque trajet est recentré
latéralement sur son point de départ (tous les trajets partent de y=0) : on
compare ainsi la *forme* des routes avec et sans chip, comme un "route tree".
Le trajet moyen de chaque catégorie est tracé en trait épais.

Fonctions publiques :
  - terrain_vide() / creer_terrain() : terrain nu
  - dessiner_trajets(routes_df, nflId) : trajets d'un joueur sur le terrain
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- Constantes de terrain ---------------------------------------------------
# Cadre par défaut (yards). dessiner_trajets() l'adapte aux données du joueur.
X_MIN = -10.0
X_MAX = 25.0
Y_MIN = -15.0
Y_MAX = 15.0

# Largeur réglementaire d'un terrain NFL (yards), pour borner l'écart latéral.
LARGEUR_TERRAIN = 53.3

# Couleurs
COULEUR_PELOUSE = "#2f7d43"          # bande de gazon foncée
COULEUR_PELOUSE_CLAIRE = "#368a4b"   # bande de gazon claire (tonte alternée)
COULEUR_LIGNE = "rgba(255,255,255,0.45)"
COULEUR_MELEE = "#ffd400"            # ligne de mêlée en jaune vif
COULEUR_CHIP = "#e63946"             # rouge (avec chip)
COULEUR_SANS_CHIP = "#3a86ff"        # bleu (sans chip)
COULEUR_TEXTE = "#1f2328"
POLICE = "Inter, 'Source Sans 3', 'Segoe UI', sans-serif"

# Part des trajets que le cadre automatique doit contenir entièrement (les
# rares trajets extrêmes sortent du cadre, signalés par une note).
QUANTILE_CADRE = 0.95
# Nombre de points utilisés pour calculer le trajet moyen.
POINTS_TRAJET_MOYEN = 30


def creer_terrain(
    x_min: float = X_MIN,
    x_max: float = X_MAX,
    y_min: float = Y_MIN,
    y_max: float = Y_MAX,
) -> go.Figure:
    """Renvoie une Figure Plotly représentant un terrain nu.

    Bandes de gazon alternées tous les 5 yards, lignes de yard numérotées
    (+5, +10…), ligne de mêlée (x=0) en jaune. Ratio réel 1 yd = 1 yd.
    """
    fig = go.Figure()
    shapes: list[dict] = []

    # Fond (pelouse) couvrant toute la zone visible.
    shapes.append(
        dict(
            type="rect",
            x0=x_min, x1=x_max, y0=y_min, y1=y_max,
            fillcolor=COULEUR_PELOUSE,
            line=dict(width=0),
            layer="below",
        )
    )

    # Bandes claires alternées (effet tonte) entre les lignes de 5 yards.
    debut = math.floor(x_min / 5.0) * 5
    x = debut
    while x < x_max:
        if int(round(x / 5.0)) % 2 == 0:
            shapes.append(
                dict(
                    type="rect",
                    x0=max(x, x_min), x1=min(x + 5, x_max), y0=y_min, y1=y_max,
                    fillcolor=COULEUR_PELOUSE_CLAIRE,
                    line=dict(width=0),
                    layer="below",
                )
            )
        x += 5

    # Lignes de yard tous les 5 yards (x=0 réservé à la ligne de mêlée).
    annotations: list[dict] = []
    x = math.ceil(x_min / 5.0) * 5
    while x <= x_max:
        if abs(x) > 1e-9:
            shapes.append(
                dict(
                    type="line",
                    x0=x, x1=x, y0=y_min, y1=y_max,
                    line=dict(color=COULEUR_LIGNE, width=1),
                    layer="below",
                )
            )
        x += 5

    # Ligne de mêlée mise en évidence à x=0.
    shapes.append(
        dict(
            type="line",
            x0=0, x1=0, y0=y_min, y1=y_max,
            line=dict(color=COULEUR_MELEE, width=3),
            layer="below",
        )
    )

    # Bordure du terrain.
    shapes.append(
        dict(
            type="rect",
            x0=x_min, x1=x_max, y0=y_min, y1=y_max,
            fillcolor="rgba(0,0,0,0)",
            line=dict(color="white", width=2),
            layer="below",
        )
    )

    annotations.append(
        dict(
            x=0, y=y_max, xref="x", yref="y",
            text="<b>Ligne de mêlée</b>",
            showarrow=False,
            yanchor="top",
            xanchor="left",
            xshift=6,
            yshift=-4,
            font=dict(color=COULEUR_MELEE, size=12, family=POLICE),
        )
    )

    fig.update_layout(
        title=dict(
            text="Trajets du joueur, du snap au lancer",
            font=dict(size=18, color=COULEUR_TEXTE, family=POLICE),
            x=0, xanchor="left",
        ),
        shapes=shapes,
        annotations=annotations,
        plot_bgcolor=COULEUR_PELOUSE,
        paper_bgcolor="white",
        font=dict(family=POLICE, color=COULEUR_TEXTE, size=13),
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0, xanchor="left",
            y=-0.16, yanchor="top",
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=13),
        ),
        hoverlabel=dict(font=dict(family=POLICE)),
        margin=dict(l=70, r=20, t=90, b=100),
        height=600,
    )

    # Pas de ratio 1:1 imposé : le terrain occupe toute la largeur, ce qui
    # étire la profondeur (la mesure qui nous intéresse) et reste lisible.
    fig.update_xaxes(
        title_text="Profondeur par rapport à la ligne de mêlée (yards)",
        range=[x_min, x_max],
        showgrid=False,
        zeroline=False,
        showline=False,
        dtick=5,
        tickformat="+d",
        ticks="outside",
        tickcolor="#c9cdd2",
    )
    fig.update_yaxes(
        title_text="Écart latéral depuis le départ (yards)",
        range=[y_min, y_max],
        showgrid=False,
        zeroline=False,
        showline=False,
        dtick=5,
        ticks="outside",
        tickcolor="#c9cdd2",
    )

    return fig


def terrain_vide() -> go.Figure:
    """Alias de :func:`creer_terrain` (terrain nu)."""
    return creer_terrain()


def _normaliser_chip(valeur) -> bool:
    """Interprète ``chip`` qu'il soit booléen ou chaîne "True"/"False".

    Toute valeur non reconnue est considérée comme False.
    """
    if isinstance(valeur, str):
        return valeur.strip().lower() in {"true", "1", "yes", "oui", "vrai"}
    try:
        if pd.isna(valeur):
            return False
    except (TypeError, ValueError):
        pass
    try:
        return bool(valeur)
    except Exception:
        return False


def _annotation_vide(fig: go.Figure, message: str) -> go.Figure:
    """Ajoute un placeholder visuel centré sur le terrain."""
    x_min, x_max = fig.layout.xaxis.range
    fig.add_annotation(
        x=(x_min + x_max) / 2.0,
        y=0,
        xref="x", yref="y",
        text=message,
        showarrow=False,
        font=dict(color="white", size=16, family=POLICE),
        bgcolor="rgba(0,0,0,0.45)",
        borderpad=8,
    )
    return fig


def _arrondir_bas(v: float, pas: float = 5.0) -> float:
    return math.floor(v / pas) * pas


def _arrondir_haut(v: float, pas: float = 5.0) -> float:
    return math.ceil(v / pas) * pas


def _cadre(trajets: list[dict]) -> tuple[float, float, float, float, int]:
    """Calcule un cadre (x_min, x_max, y_min, y_max) adapté aux trajets.

    Le cadre contient au moins ``QUANTILE_CADRE`` des trajets en entier ;
    renvoie aussi le nombre de trajets qui en sortent partiellement.
    """
    x_bas = np.array([t["x"].min() for t in trajets])
    x_haut = np.array([t["x"].max() for t in trajets])
    y_abs = np.array([np.abs(t["y"]).max() for t in trajets])

    x_min = min(-5.0, _arrondir_bas(float(np.quantile(x_bas, 1 - QUANTILE_CADRE)) - 1.5))
    x_max = max(15.0, _arrondir_haut(float(np.quantile(x_haut, QUANTILE_CADRE)) + 1.5))
    y_lim = max(10.0, _arrondir_haut(float(np.quantile(y_abs, QUANTILE_CADRE)) + 1.5))
    y_lim = min(y_lim, LARGEUR_TERRAIN)

    hors_cadre = int(np.sum((x_bas < x_min) | (x_haut > x_max) | (y_abs > y_lim)))
    return x_min, x_max, -y_lim, y_lim, hors_cadre


def _concat_avec_coupures(trajets: list[dict]) -> tuple[list, list, list]:
    """Concatène plusieurs trajets en une seule trace (séparés par None)."""
    xs: list = []
    ys: list = []
    infos: list = []
    for t in trajets:
        xs.extend(t["x"].tolist() + [None])
        ys.extend(t["y"].tolist() + [None])
        infos.extend([t["label"]] * len(t["x"]) + [None])
    return xs, ys, infos


def _trajet_moyen(trajets: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Trajet moyen : chaque trajet est rééchantillonné du snap au lancer."""
    grille = np.linspace(0.0, 1.0, POINTS_TRAJET_MOYEN)
    xs, ys = [], []
    for t in trajets:
        temps = np.linspace(0.0, 1.0, len(t["x"]))
        xs.append(np.interp(grille, temps, t["x"]))
        ys.append(np.interp(grille, temps, t["y"]))
    return np.mean(xs, axis=0), np.mean(ys, axis=0)


def _extraire_trajets(sous: pd.DataFrame) -> list[dict]:
    """Découpe les frames d'un joueur en trajets ordonnés et recentrés."""
    a_chip = "chip" in sous.columns
    a_y = "y" in sous.columns
    a_frame = "frameId" in sous.columns

    cles = [c for c in ("gameId", "playId") if c in sous.columns]
    groupes = list(sous.groupby(cles, sort=True)) if cles else [((0,), sous)]

    trajets: list[dict] = []
    for cle, sub in groupes:
        if a_frame:
            sub = sub.sort_values("frameId")
        sub = sub[pd.to_numeric(sub["x"], errors="coerce").notna()]
        if sub.empty:
            continue

        x = pd.to_numeric(sub["x"], errors="coerce").to_numpy(dtype=float)
        if a_y:
            y = pd.to_numeric(sub["y"], errors="coerce").to_numpy(dtype=float)
            y = np.nan_to_num(y - (y[0] if not np.isnan(y[0]) else np.nanmean(y)))
        else:
            y = np.zeros_like(x)

        est_chip = _normaliser_chip(sub["chip"].iloc[0]) if a_chip else False
        cle = cle if isinstance(cle, tuple) else (cle,)
        label = " · ".join(
            f"{nom} {val}" for nom, val in zip(("match", "action"), cle)
        ) if cles else "trajet"

        trajets.append({"x": x, "y": y, "chip": est_chip, "label": label})
    return trajets


def _ajouter_categorie(fig: go.Figure, trajets: list[dict], est_chip: bool) -> None:
    """Trace une catégorie : trajets fins, positions au lancer, trajet moyen."""
    if not trajets:
        return

    couleur = COULEUR_CHIP if est_chip else COULEUR_SANS_CHIP
    libelle = "Avec chip" if est_chip else "Sans chip"

    # 1) Tous les trajets, fins et transparents (une seule trace par catégorie).
    xs, ys, infos = _concat_avec_coupures(trajets)
    fig.add_trace(
        go.Scatter(
            x=xs, y=ys,
            mode="lines",
            line=dict(color=couleur, width=1.3),
            opacity=0.35,
            name=f"{libelle} (actions)",
            legendgroup=libelle,
            showlegend=False,
            customdata=infos,
            hovertemplate=(
                f"<b>{libelle}</b> · %{{customdata}}<br>"
                "Profondeur : %{x:+.1f} yd<br>"
                "Écart latéral : %{y:+.1f} yd<extra></extra>"
            ),
        )
    )

    # 2) Position de chaque trajet au moment du lancer (dernier frame).
    fig.add_trace(
        go.Scatter(
            x=[t["x"][-1] for t in trajets],
            y=[t["y"][-1] for t in trajets],
            mode="markers",
            marker=dict(color=couleur, size=7, opacity=0.8,
                        line=dict(color="white", width=1)),
            name=libelle,
            legendgroup=libelle,
            showlegend=False,
            customdata=[t["label"] for t in trajets],
            hovertemplate=(
                f"<b>{libelle}</b> · %{{customdata}}<br>"
                "Au lancer : %{x:+.1f} yd<extra></extra>"
            ),
        )
    )

    # 3) Trajet moyen en trait épais, avec liseré blanc pour ressortir.
    mx, my = _trajet_moyen(trajets)
    fig.add_trace(
        go.Scatter(
            x=mx, y=my,
            mode="lines",
            line=dict(color="white", width=8),
            legendgroup=libelle,
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=mx, y=my,
            mode="lines",
            line=dict(color=couleur, width=4.5),
            # Entrée de légende unique de la catégorie (trait plein, lisible) ;
            # un clic masque toute la catégorie grâce au legendgroup.
            name=libelle,
            legendgroup=libelle,
            showlegend=True,
            hovertemplate=(
                f"<b>Trajet moyen {libelle.lower()}</b><br>"
                "Profondeur : %{x:+.1f} yd<extra></extra>"
            ),
        )
    )

    # Losange au bout du trajet moyen + badge "profondeur moyenne au lancer".
    prof_lancer = float(np.mean([t["x"][-1] for t in trajets]))
    fig.add_trace(
        go.Scatter(
            x=[mx[-1]], y=[my[-1]],
            mode="markers",
            marker=dict(color=couleur, size=15, symbol="diamond",
                        line=dict(color="white", width=2)),
            legendgroup=libelle,
            showlegend=False,
            hovertemplate=(
                f"<b>{libelle}</b><br>Profondeur moyenne au lancer : "
                f"{prof_lancer:+.1f} yd<extra></extra>"
            ),
        )
    )
    # Badge décalé (chip en dessous, sans chip au-dessus) pour ne jamais
    # recouvrir les trajets moyens.
    fig.add_annotation(
        x=mx[-1], y=my[-1], xref="x", yref="y",
        text=f"<b>{libelle} : {prof_lancer:+.1f} yd</b>",
        showarrow=True,
        arrowhead=0, arrowwidth=1.5, arrowcolor="white",
        ax=30, ay=34 if est_chip else -34,
        bgcolor=couleur,
        bordercolor="white", borderwidth=1.5, borderpad=5,
        font=dict(color="white", size=13, family=POLICE),
        xanchor="left",
    )


def dessiner_trajets(routes_df, nflId) -> go.Figure:
    """Trace les trajets d'un joueur sur le terrain.

    Filtre ``routes_df`` sur ``nflId``, groupe par (gameId, playId) et trace
    chaque trajet ordonné par ``frameId``, recentré latéralement sur son
    point de départ. Rouge = avec chip, bleu = sans chip. Le trajet moyen de
    chaque catégorie est en trait épais, terminé par la profondeur moyenne au
    lancer. Une seule entrée de légende par catégorie.

    Robustesse :
      - tolère l'absence de colonnes de contexte (down, yardsToGo, couverture) ;
      - tolère un DataFrame réduit (profondeur seule, sans ``y`` ni ``chip``) ;
      - ``chip`` booléen OU chaîne "True"/"False" ;
      - nflId inconnu / aucune donnée -> terrain avec placeholder, sans crash.
    """
    if routes_df is None or not isinstance(routes_df, pd.DataFrame) or routes_df.empty:
        return _annotation_vide(creer_terrain(), "Aucune donnée pour ce joueur")

    df = routes_df
    if "nflId" not in df.columns or "x" not in df.columns:
        return _annotation_vide(creer_terrain(), "Aucune donnée pour ce joueur")

    # Filtrage sur le joueur (tolérant aux types : 46206 vs 46206.0 vs "46206").
    sous = df[df["nflId"] == nflId]
    if sous.empty:
        try:
            cible = float(nflId)
            sous = df[pd.to_numeric(df["nflId"], errors="coerce") == cible]
        except (TypeError, ValueError):
            sous = df[df["nflId"].astype(str) == str(nflId)]

    trajets = _extraire_trajets(sous) if not sous.empty else []
    if not trajets:
        return _annotation_vide(creer_terrain(), "Aucune donnée pour ce joueur")

    x_min, x_max, y_min, y_max, hors_cadre = _cadre(trajets)
    fig = creer_terrain(x_min, x_max, y_min, y_max)

    sans = [t for t in trajets if not t["chip"]]
    avec = [t for t in trajets if t["chip"]]
    # Bleu d'abord, rouge par-dessus : le chip est le sujet principal.
    _ajouter_categorie(fig, sans, est_chip=False)
    _ajouter_categorie(fig, avec, est_chip=True)

    morceaux = [f"{len(avec)} actions avec chip", f"{len(sans)} sans chip"]
    if hors_cadre:
        morceaux.append(
            f"{hors_cadre} trajet{'s' if hors_cadre > 1 else ''} "
            f"dépasse{'nt' if hors_cadre > 1 else ''} du cadre"
        )
    fig.update_layout(
        title=dict(
            text=(
                "Trajets du joueur, du snap au lancer<br>"
                "<span style='font-size:13px;color:#57606a'>"
                f"{' · '.join(morceaux)} · traits fins = chaque action, "
                "trait épais = trajet moyen, point = position au lancer</span>"
            ),
        ),
    )
    return fig
