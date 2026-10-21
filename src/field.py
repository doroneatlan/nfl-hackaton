#!/usr/bin/env python3
"""Rendu du terrain et des trajets pour le projet "Le coût du chip".

100 % Python / Plotly (plotly.graph_objects). Les coordonnées attendues sont
NORMALISÉES par rapport à la ligne de mêlée :
  - x = profondeur (yards au-delà de la ligne de mêlée), ligne de mêlée = x=0
  - y = largeur du terrain (latéral)

Fonctions publiques :
  - terrain_vide() / creer_terrain() : terrain nu (Task 3)
  - dessiner_trajets(routes_df, nflId) : trajets d'un joueur sur le terrain
                                         (Tasks 4 et 5, robuste)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# --- Constantes de terrain ---------------------------------------------------
# Largeur réglementaire d'un terrain NFL : 53.3 yards. Centré sur y=0.
DEMI_LARGEUR = 53.3 / 2.0          # ≈ 26.65
Y_MIN = -DEMI_LARGEUR
Y_MAX = DEMI_LARGEUR

# Profondeur affichée (en yards) de part et d'autre de la ligne de mêlée.
X_MIN = -5.0
X_MAX = 30.0

# Couleurs
COULEUR_PELOUSE = "#2e7d32"       # vert gazon
COULEUR_LIGNE = "rgba(255,255,255,0.55)"  # lignes de yard blanches discrètes
COULEUR_MELEE = "#ffd400"         # ligne de mêlée en jaune vif
COULEUR_CHIP = "#d62728"          # rouge (avec chip)
COULEUR_SANS_CHIP = "#1f77b4"     # bleu (sans chip)


def creer_terrain() -> go.Figure:
    """Renvoie une Figure Plotly représentant un terrain nu (Task 3).

    Fond vert, lignes de yard tous les 5 yards, ligne de mêlée (x=0) mise en
    évidence. Ratio d'aspect réaliste via ``yaxis.scaleanchor``. Les gridlines
    Plotly par défaut sont masquées pour un rendu net.
    """
    fig = go.Figure()

    shapes: list[dict] = []

    # Fond (pelouse) couvrant toute la zone visible.
    shapes.append(
        dict(
            type="rect",
            x0=X_MIN, x1=X_MAX, y0=Y_MIN, y1=Y_MAX,
            fillcolor=COULEUR_PELOUSE,
            line=dict(width=0),
            layer="below",
        )
    )

    # Lignes de yard verticales (perpendiculaires à la profondeur), tous les 5 yd.
    x = X_MIN - (X_MIN % 5)
    while x <= X_MAX:
        if abs(x) > 1e-9:  # on réserve x=0 à la ligne de mêlée.
            shapes.append(
                dict(
                    type="line",
                    x0=x, x1=x, y0=Y_MIN, y1=Y_MAX,
                    line=dict(color=COULEUR_LIGNE, width=1),
                    layer="below",
                )
            )
        x += 5

    # Ligne de mêlée mise en évidence à x=0.
    shapes.append(
        dict(
            type="line",
            x0=0, x1=0, y0=Y_MIN, y1=Y_MAX,
            line=dict(color=COULEUR_MELEE, width=3),
            layer="below",
        )
    )

    # Bordures du terrain.
    shapes.append(
        dict(
            type="rect",
            x0=X_MIN, x1=X_MAX, y0=Y_MIN, y1=Y_MAX,
            fillcolor="rgba(0,0,0,0)",
            line=dict(color="white", width=2),
            layer="below",
        )
    )

    # Annotation discrète pour la ligne de mêlée.
    annotations = [
        dict(
            x=0, y=Y_MAX,
            xref="x", yref="y",
            text="Ligne de mêlée",
            showarrow=False,
            yanchor="bottom",
            font=dict(color=COULEUR_MELEE, size=12),
        )
    ]

    fig.update_layout(
        title="Terrain de football américain — trajets relatifs à la ligne de mêlée",
        shapes=shapes,
        annotations=annotations,
        plot_bgcolor=COULEUR_PELOUSE,
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            title="Type de trajet",
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor="gray",
            borderwidth=1,
        ),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    # Axe x = profondeur, axe y = largeur. Ratio réaliste : 1 yd en x = 1 yd en y.
    fig.update_xaxes(
        title_text="Profondeur (yards au-delà de la ligne de mêlée)",
        range=[X_MIN, X_MAX],
        showgrid=False,
        zeroline=False,
        showline=False,
    )
    fig.update_yaxes(
        title_text="Largeur du terrain (yards)",
        range=[Y_MIN, Y_MAX],
        showgrid=False,
        zeroline=False,
        showline=False,
        scaleanchor="x",
        scaleratio=1,
    )

    return fig


# Alias demandé par l'énoncé.
def terrain_vide() -> go.Figure:
    """Alias de :func:`creer_terrain` (terrain nu)."""
    return creer_terrain()


def _normaliser_chip(valeur) -> bool:
    """Interprète ``chip`` qu'il soit booléen ou chaîne "True"/"False".

    Robuste au parsing CSV : accepte True/False, "true"/"false", "1"/"0", etc.
    Toute valeur non reconnue est considérée comme False.
    """
    if isinstance(valeur, str):
        return valeur.strip().lower() in {"true", "1", "yes", "oui", "vrai"}
    try:
        return bool(valeur)
    except Exception:
        return False


def _annotation_vide(fig: go.Figure, message: str) -> go.Figure:
    """Ajoute un placeholder visuel centré sur le terrain."""
    fig.add_annotation(
        x=(X_MIN + X_MAX) / 2.0,
        y=0,
        xref="x", yref="y",
        text=message,
        showarrow=False,
        font=dict(color="white", size=16),
        bgcolor="rgba(0,0,0,0.45)",
        borderpad=6,
    )
    return fig


def dessiner_trajets(routes_df, nflId) -> go.Figure:
    """Trace les trajets d'un joueur sur le terrain (Tasks 4 & 5).

    Part du terrain nu, filtre ``routes_df`` sur ``nflId``, groupe par
    (gameId, playId) et trace chaque trajet comme une ligne ordonnée par
    ``frameId``. Trajets avec chip en ROUGE, sans chip en BLEU. Une seule
    entrée de légende par catégorie. Marqueur au point de départ (snap).

    Robustesse (Task 5) :
      - tolère l'absence de colonnes de contexte (down, yardsToGo, couverture) ;
      - tolère un DataFrame réduit (profondeur seule) ;
      - ``chip`` booléen OU chaîne "True"/"False" ;
      - nflId inconnu / aucune donnée -> terrain avec placeholder, sans crash.
    """
    fig = creer_terrain()

    # Entrée invalide ou vide : placeholder, pas d'exception.
    if routes_df is None or not isinstance(routes_df, pd.DataFrame) or routes_df.empty:
        return _annotation_vide(fig, "Aucune donnée pour ce joueur")

    df = routes_df

    # Il faut au minimum une colonne nflId et une profondeur x pour tracer.
    if "nflId" not in df.columns or "x" not in df.columns:
        return _annotation_vide(fig, "Aucune donnée pour ce joueur")

    # Filtrage sur le joueur (tolérant aux types : compare en chaîne si besoin).
    sous = df[df["nflId"] == nflId]
    if sous.empty:
        try:
            sous = df[df["nflId"].astype(str) == str(nflId)]
        except Exception:
            sous = df.iloc[0:0]

    if sous.empty:
        return _annotation_vide(fig, "Aucune donnée pour ce joueur")

    # Colonnes optionnelles : on fournit des valeurs de repli sûres.
    a_chip = "chip" in sous.columns
    a_y = "y" in sous.columns
    a_frame = "frameId" in sous.columns

    # Clés de regroupement disponibles ; au pire, tout dans un seul trajet.
    cles = [c for c in ("gameId", "playId") if c in sous.columns]
    if cles:
        groupes = list(sous.groupby(cles, sort=True))
    else:
        groupes = [((0,), sous)]

    # Pour n'afficher qu'une seule entrée de légende par catégorie.
    legende_affichee = {True: False, False: False}

    def _ajouter_trace(sub: pd.DataFrame) -> None:
        if sub.empty:
            return

        # Ordonner par frameId si dispo, sinon conserver l'ordre d'origine.
        if a_frame and "frameId" in sub.columns:
            sub = sub.sort_values("frameId")

        xs = sub["x"].tolist()
        ys = sub["y"].tolist() if a_y and "y" in sub.columns else [0.0] * len(xs)

        # Déterminer la catégorie chip de ce trajet (robuste au type).
        if a_chip and "chip" in sub.columns:
            est_chip = _normaliser_chip(sub["chip"].iloc[0])
        else:
            est_chip = False

        couleur = COULEUR_CHIP if est_chip else COULEUR_SANS_CHIP
        libelle = "Avec chip" if est_chip else "Sans chip"

        montrer_legende = not legende_affichee[est_chip]
        legende_affichee[est_chip] = True

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=couleur, width=2),
                name=libelle,
                legendgroup=libelle,
                showlegend=montrer_legende,
                opacity=0.85,
                hoverinfo="x+y+name",
            )
        )

        # Marqueur discret au point de départ (snap = premier frame).
        fig.add_trace(
            go.Scatter(
                x=[xs[0]],
                y=[ys[0]],
                mode="markers",
                marker=dict(color=couleur, size=7, symbol="circle",
                            line=dict(color="white", width=1)),
                name=libelle,
                legendgroup=libelle,
                showlegend=False,
                hoverinfo="skip",
            )
        )

    for _, sub in groupes:
        _ajouter_trace(sub)

    return fig
