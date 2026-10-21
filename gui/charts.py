#!/usr/bin/env python3
"""Graphiques matplotlib pour l'interface PySide6 — "Le coût du chip".

Chaque fonction DESSINE sur une Figure matplotlib fournie (pour pouvoir
l'embarquer dans un FigureCanvasQTAgg). Toutes sont tolérantes aux données
absentes : elles affichent un message centré plutôt que de crasher.

Quatre vues :
  - dessiner_equipe  : comparatif d'équipe chip vs sans chip (barres)
  - dessiner_trajets : trajets d'un joueur sur un terrain (profondeur/largeur)
  - dessiner_situations : coût du chip par distance x couverture (heatmap)
  - dessiner_rushers : pression des rushers adverses, chippés vs non (barres)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from gui.data import COULEUR_CHIP, COULEUR_SANS_CHIP

# --- Terrain -----------------------------------------------------------------
# y dans routes.csv est la largeur normalisée du terrain (0 à 53.3), pas centrée.
LARGEUR = 53.3
Y_MIN, Y_MAX = 0.0, LARGEUR
X_MIN, X_MAX = -5.0, 30.0

COULEUR_PELOUSE = "#2e7d32"
COULEUR_LIGNE = (1, 1, 1, 0.45)
COULEUR_MELEE = "#ffd400"

# Ordre des buckets de distance.
BUCKETS_ORDRE = ["court", "moyen", "long"]
COLONNES_COUVERTURE = ["couverture", "pff_passCoverage"]


def _message_vide(fig: Figure, message: str) -> None:
    """Efface la figure et affiche un message centré."""
    fig.clear()
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.text(0.5, 0.5, message, ha="center", va="center",
            fontsize=13, color="#555", wrap=True, transform=ax.transAxes)


# --- Vue d'équipe ------------------------------------------------------------
def dessiner_equipe(fig: Figure, stats: dict, equipe: str) -> None:
    """Barres comparant profondeur et pression, chip vs sans chip, pour l'équipe."""
    fig.clear()
    if not stats:
        _message_vide(fig, "Aucune donnée pour cette équipe.")
        return

    ax_prof = fig.add_subplot(121)
    ax_pres = fig.add_subplot(122)

    # Profondeur moyenne (yards).
    pc = stats.get("profondeur_chip")
    ps = stats.get("profondeur_sans_chip")
    if pc is not None and ps is not None:
        barres = ax_prof.bar(
            ["Sans chip", "Avec chip"], [ps, pc],
            color=[COULEUR_SANS_CHIP, COULEUR_CHIP],
        )
        ax_prof.bar_label(barres, fmt="%.1f yd", padding=3)
        ax_prof.set_ylabel("Profondeur moyenne (yards)")
        ax_prof.set_title("Profondeur de route")
        ax_prof.set_ylim(0, max(ps, pc) * 1.2)
    else:
        ax_prof.set_axis_off()
        ax_prof.text(0.5, 0.5, "Profondeur\nindisponible",
                     ha="center", va="center", color="#777")

    # Pression QB : déjà en pourcentage (0-100) dans le contrat results/.
    rc = stats.get("pression_chip")
    rs = stats.get("pression_sans_chip")
    if rc is not None and rs is not None:
        barres = ax_pres.bar(
            ["Sans chip", "Avec chip"], [rs, rc],
            color=[COULEUR_SANS_CHIP, COULEUR_CHIP],
        )
        ax_pres.bar_label(barres, fmt="%.0f%%", padding=3)
        ax_pres.set_ylabel("Pression sur le QB (%)")
        ax_pres.set_title("Pression subie par le QB")
        ax_pres.set_ylim(0, max(rs, rc) * 1.25)
    else:
        ax_pres.set_axis_off()
        ax_pres.text(0.5, 0.5, "Pression\nindisponible",
                     ha="center", va="center", color="#777")

    fig.suptitle(
        f"{equipe} — effet du chip  ({stats.get('nb_chips', 0)} chips, "
        f"{stats.get('nb_sans_chip', 0)} routes directes)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))


# --- Terrain + trajets d'un joueur ------------------------------------------
def _fond_terrain(ax) -> None:
    """Dessine le fond de terrain (pelouse, lignes de yard, ligne de mêlée)."""
    ax.add_patch(
        Rectangle(
            (X_MIN, Y_MIN), X_MAX - X_MIN, Y_MAX - Y_MIN,
            facecolor=COULEUR_PELOUSE, edgecolor="white", linewidth=1.5, zorder=0,
        )
    )
    x = X_MIN - (X_MIN % 5)
    while x <= X_MAX:
        if abs(x) > 1e-9:
            ax.plot([x, x], [Y_MIN, Y_MAX], color=COULEUR_LIGNE, linewidth=1, zorder=1)
        x += 5
    ax.plot([0, 0], [Y_MIN, Y_MAX], color=COULEUR_MELEE, linewidth=2.5, zorder=2)
    ax.text(0, Y_MAX - 1, "Ligne de mêlée", color=COULEUR_MELEE,
            fontsize=9, ha="center", va="top", zorder=3)

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal")
    ax.set_xlabel("Profondeur (yards au-delà de la ligne de mêlée)")
    ax.set_ylabel("Largeur du terrain (yards)")


def dessiner_trajets(fig: Figure, routes: pd.DataFrame, nfl_id, nom: str = "") -> None:
    """Trace les trajets d'un joueur : bleu sans chip, rouge avec chip."""
    fig.clear()

    if routes is None or routes.empty or "nflId" not in routes.columns or "x" not in routes.columns:
        _message_vide(fig, "Aucun trajet disponible (routes.csv absent ou vide).")
        return

    sous = routes[routes["nflId"] == nfl_id]
    if sous.empty:
        try:
            sous = routes[routes["nflId"].astype(str) == str(nfl_id)]
        except Exception:
            sous = routes.iloc[0:0]
    if sous.empty:
        _message_vide(fig, f"Aucun trajet pour {nom or nfl_id}.")
        return

    ax = fig.add_subplot(111)
    _fond_terrain(ax)

    a_y = "y" in sous.columns
    a_frame = "frameId" in sous.columns
    a_chip = "chip" in sous.columns
    cles = [c for c in ("gameId", "playId") if c in sous.columns]
    groupes = sous.groupby(cles) if cles else [((0,), sous)]

    deja = {True: False, False: False}
    for _, sub in (groupes if cles else groupes):
        if a_frame:
            sub = sub.sort_values("frameId")
        xs = sub["x"].to_numpy()
        ys = sub["y"].to_numpy() if a_y else np.full(len(xs), LARGEUR / 2.0)
        est_chip = bool(sub["chip"].iloc[0]) if a_chip else False
        couleur = COULEUR_CHIP if est_chip else COULEUR_SANS_CHIP
        libelle = "Avec chip" if est_chip else "Sans chip"
        label = libelle if not deja[est_chip] else None
        deja[est_chip] = True
        ax.plot(xs, ys, color=couleur, linewidth=2, alpha=0.85, zorder=4, label=label)
        ax.scatter(xs[0], ys[0], color=couleur, s=35, edgecolor="white",
                   linewidth=1, zorder=5)

    ax.legend(loc="upper right", framealpha=0.85)
    ax.set_title(f"Trajets de {nom or nfl_id}  (bleu = sans chip · rouge = avec chip)")
    fig.tight_layout()


# --- Situations --------------------------------------------------------------
def _bucket_yards(v) -> str:
    """Bucketise yardsToGo : court (<=3), moyen (4-7), long (>=8)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "inconnu"
    if pd.isna(v):
        return "inconnu"
    if v <= 3:
        return "court"
    if v <= 7:
        return "moyen"
    return "long"


def _colonne_couverture(df: pd.DataFrame):
    for col in COLONNES_COUVERTURE:
        if col in df.columns:
            return col
    return None


def dessiner_situations(fig: Figure, routes: pd.DataFrame) -> None:
    """Heatmap du coût du chip (profondeur sans chip - avec chip) par situation."""
    fig.clear()

    if routes is None or routes.empty or "chip" not in routes.columns:
        _message_vide(fig, "Aucune donnée exploitable pour les situations.")
        return

    cles = [c for c in ("gameId", "playId", "nflId") if c in routes.columns]
    df = routes.copy()
    if not cles:
        df["_trajet"] = range(len(df))
        cles = ["_trajet"]

    agg = {"x": "max", "chip": "first"}
    col_couv = _colonne_couverture(df)
    if "yardsToGo" in df.columns:
        agg["yardsToGo"] = "first"
    if col_couv:
        agg[col_couv] = "first"

    trajets = df.groupby(cles, as_index=False).agg(agg).rename(columns={"x": "profondeur"})
    a_bucket = "yardsToGo" in trajets.columns
    a_couv = col_couv is not None
    if a_bucket:
        trajets["bucket"] = trajets["yardsToGo"].map(_bucket_yards)
    if a_couv:
        trajets["couverture"] = trajets[col_couv].fillna("inconnue").astype(str)

    if not a_bucket and not a_couv:
        _dessiner_situations_global(fig, trajets)
        return

    dims = []
    if a_couv:
        dims.append("couverture")
    if a_bucket:
        dims.append("bucket")

    pivot = trajets.groupby(dims + ["chip"])["profondeur"].mean().reset_index()
    avec = pivot[pivot["chip"]].drop(columns="chip").rename(columns={"profondeur": "prof_chip"})
    sans = pivot[~pivot["chip"]].drop(columns="chip").rename(columns={"profondeur": "prof_sans"})
    fusion = pd.merge(avec, sans, on=dims, how="outer")
    if fusion.empty:
        _message_vide(fig, "Pas de trajets pour comparer chip vs sans chip.")
        return
    fusion["cout"] = fusion["prof_sans"] - fusion["prof_chip"]

    if a_couv and a_bucket:
        _heatmap(fig, fusion)
    else:
        _barres_1d(fig, fusion, dims[0])


def _ordonner_buckets(valeurs) -> list[str]:
    presents = list(dict.fromkeys(valeurs))
    connus = [b for b in BUCKETS_ORDRE if b in presents]
    autres = [b for b in presents if b not in BUCKETS_ORDRE]
    return connus + autres


def _heatmap(fig: Figure, fusion: pd.DataFrame) -> None:
    buckets = _ordonner_buckets(fusion["bucket"].tolist())
    couvertures = sorted(fusion["couverture"].unique().tolist())
    grille = fusion.pivot(index="couverture", columns="bucket", values="cout")
    grille = grille.reindex(index=couvertures, columns=buckets)
    z = grille.to_numpy(dtype=float)

    ax = fig.add_subplot(111)
    vmax = np.nanmax(np.abs(z)) if np.isfinite(z).any() else 1.0
    im = ax.imshow(z, cmap="RdYlGn_r", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(buckets)))
    ax.set_xticklabels(buckets)
    ax.set_yticks(range(len(couvertures)))
    ax.set_yticklabels(couvertures)
    ax.set_xlabel("Distance à franchir (yardsToGo)")
    ax.set_ylabel("Couverture défensive")

    for i in range(len(couvertures)):
        for j in range(len(buckets)):
            val = z[i, j]
            texte = "n/a" if np.isnan(val) else f"{val:+.1f}"
            ax.text(j, i, texte, ha="center", va="center",
                    color="black", fontsize=10)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Coût du chip (yards perdus)")
    ax.set_title("Coût du chip par situation\nvert = peu pénalisant · rouge = coûteux")
    fig.tight_layout()


def _barres_1d(fig: Figure, fusion: pd.DataFrame, dim: str) -> None:
    if dim == "bucket":
        ordre = _ordonner_buckets(fusion["bucket"].tolist())
        fusion = fusion.set_index("bucket").reindex(ordre).reset_index()
        titre_x = "Distance à franchir (yardsToGo)"
    else:
        fusion = fusion.sort_values(dim)
        titre_x = "Couverture défensive"

    cats = fusion[dim].tolist()
    x = np.arange(len(cats))
    largeur = 0.38
    ax = fig.add_subplot(111)
    ax.bar(x - largeur / 2, fusion["prof_sans"], largeur,
           label="Sans chip", color=COULEUR_SANS_CHIP)
    ax.bar(x + largeur / 2, fusion["prof_chip"], largeur,
           label="Avec chip", color=COULEUR_CHIP)
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.set_xlabel(titre_x)
    ax.set_ylabel("Profondeur moyenne atteinte (yards)")
    ax.set_title("Coût du chip par situation")
    ax.legend()
    fig.tight_layout()


def _dessiner_situations_global(fig: Figure, trajets: pd.DataFrame) -> None:
    moyennes = trajets.groupby("chip")["profondeur"].mean()
    pc = float(moyennes.get(True, np.nan))
    ps = float(moyennes.get(False, np.nan))
    if np.isnan(pc) or np.isnan(ps):
        _message_vide(fig, "Impossible de comparer chip vs sans chip.")
        return
    ax = fig.add_subplot(111)
    barres = ax.bar(["Sans chip", "Avec chip"], [ps, pc],
                    color=[COULEUR_SANS_CHIP, COULEUR_CHIP])
    ax.bar_label(barres, fmt="%.1f yd", padding=3)
    ax.set_ylabel("Profondeur moyenne atteinte (yards)")
    ax.set_title(f"Coût du chip (vue globale) : {ps - pc:+.1f} yards")
    fig.tight_layout()


# --- Rushers adverses (page Adversaire) --------------------------------------
def dessiner_rushers(fig: Figure, rushers: pd.DataFrame, equipe: str) -> None:
    """Barres horizontales : pression de chaque rusher adverse, chippé vs non.

    Pour chaque défenseur (le plus menaçant en haut), deux barres :
      - taux de pression quand il N'EST PAS chippé (bleu)
      - taux de pression quand il EST chippé (rouge)
    Un chip "utile" fait chuter la barre rouge sous la bleue. Le côté
    d'alignement (cote) est rappelé dans l'étiquette du joueur.

    Tolère l'absence de colonnes de détail : retombe sur le taux global.
    """
    fig.clear()

    if rushers is None or rushers.empty or "nom" not in rushers.columns:
        _message_vide(fig, f"Aucun rusher pour {equipe} (rushers.csv absent ?).")
        return

    df = rushers.iloc[::-1].reset_index(drop=True)  # barh : le 1er en haut
    noms = df["nom"].tolist()
    cotes = df["cote"].tolist() if "cote" in df.columns else [""] * len(df)
    chippes = (
        df["nb_chippe"].tolist() if "nb_chippe" in df.columns else [None] * len(df)
    )

    def _etiquette(nom, cote, n_chip) -> str:
        texte = str(nom)
        if isinstance(cote, str) and cote:
            texte += f"  ({cote})"
        if n_chip is not None and not pd.isna(n_chip):
            texte += f"\nchippé {int(n_chip)}×"
        return texte

    etiquettes = [_etiquette(n, c, k) for n, c, k in zip(noms, cotes, chippes)]

    a_detail = (
        "taux_pression_non_chippe" in df.columns
        and "taux_pression_chippe" in df.columns
    )

    ax = fig.add_subplot(111)
    y = np.arange(len(df))

    if a_detail:
        hauteur = 0.38
        non = df["taux_pression_non_chippe"].to_numpy(dtype=float)
        chip = df["taux_pression_chippe"].to_numpy(dtype=float)
        b_non = ax.barh(y + hauteur / 2, non, hauteur,
                        label="Non chippé", color=COULEUR_SANS_CHIP)
        b_chip = ax.barh(y - hauteur / 2, chip, hauteur,
                         label="Chippé", color=COULEUR_CHIP)
        ax.bar_label(b_non, fmt="%.0f%%", padding=2, fontsize=8)
        ax.bar_label(b_chip, fmt="%.0f%%", padding=2, fontsize=8)
        ax.set_xlabel("Taux de pression sur le QB (%)")
        ax.legend(loc="lower right")
        titre = (f"{equipe} — pression des rushers, chippés vs non\n"
                 "le chip est utile quand la barre rouge passe sous la bleue")
    else:
        taux = df.get("taux_pression", pd.Series([np.nan] * len(df))).to_numpy(dtype=float)
        barres = ax.barh(y, taux, color=COULEUR_SANS_CHIP)
        ax.bar_label(barres, fmt="%.0f%%", padding=2, fontsize=8)
        ax.set_xlabel("Taux de pression sur le QB (%)")
        titre = f"{equipe} — rushers les plus menaçants"

    ax.set_yticks(y)
    ax.set_yticklabels(etiquettes, fontsize=9)
    ax.set_title(titre)
    fig.tight_layout()
