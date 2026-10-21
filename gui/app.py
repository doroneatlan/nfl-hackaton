#!/usr/bin/env python3
"""Fenêtre principale PySide6 — "Le coût du chip".

Parcours : l'utilisateur choisit son équipe ET l'adversaire de dimanche en
haut, puis explore quatre onglets :

  1. Mon équipe  : comparatif chip vs sans chip + tableau des joueurs
  2. Fiche joueur : trajets sur le terrain + chiffres clés chip/sans chip
  3. Adversaire   : rushers adverses à chipper (chippés vs non chippés)
  4. Situations   : coût du chip par distance x couverture

L'app lit uniquement les CSV légers de results/ (via gui/data.py) et dessine
avec matplotlib embarqué (gui/charts.py).

Lancement :
    python -m gui
"""

from __future__ import annotations

import sys

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui import charts, data


class Canvas(FigureCanvasQTAgg):
    """Toile matplotlib réutilisable embarquée dans Qt."""

    def __init__(self, width: float = 7.0, height: float = 4.5) -> None:
        self.figure = Figure(figsize=(width, height), layout=None)
        super().__init__(self.figure)

    def effacer(self) -> None:
        self.figure.clear()
        self.draw_idle()


# --- Onglet 1 : Mon équipe ---------------------------------------------------
class OngletEquipe(QWidget):
    """Comparatif d'équipe (graphique) + tableau de ses joueurs."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.canvas = Canvas(height=3.6)
        layout.addWidget(self.canvas, stretch=3)

        self.tableau = QTableWidget()
        self.tableau.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableau.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tableau, stretch=2)

    COLONNES = [
        ("nom", "Joueur"),
        ("poste", "Poste"),
        ("nb_chips", "Chips"),
        ("profondeur_chip", "Prof. chip"),
        ("profondeur_sans_chip", "Prof. sans"),
        ("pression_chip", "Pression chip"),
        ("pression_sans_chip", "Pression sans"),
        ("verdict", "Verdict"),
    ]

    def mettre_a_jour(self, summary: pd.DataFrame, equipe: str) -> None:
        charts.dessiner_equipe(self.canvas.figure, data.stats_equipe(summary, equipe), equipe)
        self.canvas.draw_idle()
        self._remplir_tableau(data.joueurs_de_equipe(summary, equipe))

    def _remplir_tableau(self, df: pd.DataFrame) -> None:
        colonnes = [(c, t) for c, t in self.COLONNES if df.empty or c in df.columns]
        self.tableau.setColumnCount(len(colonnes))
        self.tableau.setHorizontalHeaderLabels([t for _, t in colonnes])
        self.tableau.setRowCount(len(df))

        from PySide6.QtGui import QColor

        for i, (_, ligne) in enumerate(df.iterrows()):
            for j, (col, _) in enumerate(colonnes):
                valeur = ligne.get(col, "")
                if col in ("pression_chip", "pression_sans_chip") and pd.notna(valeur):
                    texte = f"{float(valeur):.0f}%"
                elif col in ("profondeur_chip", "profondeur_sans_chip") and pd.notna(valeur):
                    texte = f"{float(valeur):.1f}"
                else:
                    texte = "" if pd.isna(valeur) else str(valeur)
                item = QTableWidgetItem(texte)
                if col == "verdict":
                    couleur = data.COULEURS_VERDICT.get(str(valeur).strip().lower())
                    if couleur:
                        item.setForeground(QColor("white"))
                        item.setBackground(QColor(couleur))
                self.tableau.setItem(i, j, item)
        self.tableau.resizeColumnsToContents()


# --- Onglet 2 : Fiche joueur -------------------------------------------------
class OngletJoueur(QWidget):
    """Sélecteur de joueur + terrain avec trajets + chiffres clés."""

    def __init__(self) -> None:
        super().__init__()
        self._summary = pd.DataFrame()
        self._routes = pd.DataFrame()
        self._equipe = ""

        layout = QVBoxLayout(self)

        barre = QHBoxLayout()
        barre.addWidget(QLabel("Joueur :"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(240)
        self.combo.currentIndexChanged.connect(self._on_joueur)
        barre.addWidget(self.combo)
        barre.addStretch(1)
        self.cles = QLabel("")
        self.cles.setTextFormat(Qt.RichText)
        barre.addWidget(self.cles)
        layout.addLayout(barre)

        self.canvas = Canvas(height=4.2)
        layout.addWidget(self.canvas)

    def mettre_a_jour(self, summary: pd.DataFrame, routes: pd.DataFrame, equipe: str) -> None:
        self._summary = summary
        self._routes = routes
        self._equipe = equipe

        joueurs = data.joueurs_de_equipe(summary, equipe)
        self.combo.blockSignals(True)
        self.combo.clear()
        if not joueurs.empty and "nom" in joueurs.columns:
            for _, ligne in joueurs.iterrows():
                self.combo.addItem(str(ligne["nom"]), ligne.get("nflId"))
        self.combo.blockSignals(False)

        if self.combo.count():
            self.combo.setCurrentIndex(0)
            self._on_joueur(0)
        else:
            self.canvas.figure.clear()
            self.canvas.draw_idle()
            self.cles.setText("Aucun joueur pour cette équipe.")

    def _on_joueur(self, index: int) -> None:
        if index < 0 or self.combo.count() == 0:
            return
        nfl_id = self.combo.currentData()
        nom = self.combo.currentText()

        charts.dessiner_trajets(self.canvas.figure, self._routes, nfl_id, nom)
        self.canvas.draw_idle()
        self._afficher_cles(nfl_id)

    def _afficher_cles(self, nfl_id) -> None:
        df = self._summary
        if df.empty or "nflId" not in df.columns:
            self.cles.setText("")
            return
        ligne = df[df["nflId"] == nfl_id]
        if ligne.empty:
            self.cles.setText("")
            return
        r = ligne.iloc[0]

        def _val(col, suffixe="", pourcent=False):
            v = r.get(col)
            if pd.isna(v):
                return "—"
            if pourcent:
                return f"{float(v):.0f}%"
            return f"{v}{suffixe}"

        verdict = str(r.get("verdict", ""))
        couleur = data.COULEURS_VERDICT.get(verdict.strip().lower(), "#555")
        self.cles.setText(
            f"<b>Profondeur</b> chip {_val('profondeur_chip', ' yd')} / "
            f"sans {_val('profondeur_sans_chip', ' yd')} &nbsp;·&nbsp; "
            f"<b>Pression</b> chip {_val('pression_chip', pourcent=True)} / "
            f"sans {_val('pression_sans_chip', pourcent=True)} &nbsp;·&nbsp; "
            f"<b>Verdict</b> <span style='color:{couleur}'>{verdict}</span>"
        )


# --- Onglet 3 : Adversaire ---------------------------------------------------
class OngletAdversaire(QWidget):
    """Rushers de l'équipe adverse à chipper dimanche + effet du chip sur eux."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self.info = QLabel(
            "Sur qui faire le chip dimanche : les rushers adverses les plus "
            "menaçants et l'effet du chip sur chacun."
        )
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.canvas = Canvas(height=3.4)
        layout.addWidget(self.canvas, stretch=3)

        self.tableau = QTableWidget()
        self.tableau.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableau.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tableau, stretch=2)

    # Combien de rushers on met en avant (graphique + haut du tableau).
    TOP = 5
    # Chips minimum pour que la comparaison chippé/non soit crédible sur le graphe.
    MIN_CHIPS_GRAPHE = 5

    COLONNES = [
        ("nom", "Rusher"),
        ("poste", "Poste"),
        ("cote", "Côté"),
        ("nb_rush", "Rushs"),
        ("taux_pression", "Pression"),
        ("nb_chippe", "Chippé"),
        ("taux_pression_non_chippe", "Pression non chippé"),
        ("taux_pression_chippe", "Pression chippé"),
        ("pression_evitee", "Pression évitée"),
        ("fiabilite", "Fiabilité"),
    ]

    def mettre_a_jour(self, rushers: pd.DataFrame, equipe: str) -> None:
        # Graphique : rushers les plus menaçants ET assez chippés pour comparer.
        graphe = data.rushers_de_equipe(
            rushers, equipe, top=self.TOP, min_chips=self.MIN_CHIPS_GRAPHE
        )
        if graphe.empty:
            # Personne n'a été assez chippé : on retombe sur le top brut.
            graphe = data.rushers_de_equipe(rushers, equipe, top=self.TOP)
        charts.dessiner_rushers(self.canvas.figure, graphe, equipe)
        self.canvas.draw_idle()
        # Le tableau montre le top brut par pression, sans filtre de chips.
        self._remplir_tableau(data.rushers_de_equipe(rushers, equipe, top=12))

    def _remplir_tableau(self, df: pd.DataFrame) -> None:
        colonnes = [(c, t) for c, t in self.COLONNES if df.empty or c in df.columns]
        self.tableau.setColumnCount(len(colonnes))
        self.tableau.setHorizontalHeaderLabels([t for _, t in colonnes])
        self.tableau.setRowCount(len(df))

        pourcent = {
            "taux_pression", "taux_pression_non_chippe",
            "taux_pression_chippe", "pression_evitee",
        }
        for i, (_, ligne) in enumerate(df.iterrows()):
            for j, (col, _) in enumerate(colonnes):
                valeur = ligne.get(col, "")
                if col in pourcent and pd.notna(valeur):
                    signe = "+" if col == "pression_evitee" and float(valeur) > 0 else ""
                    texte = f"{signe}{float(valeur):.1f}%"
                else:
                    texte = "" if pd.isna(valeur) else str(valeur)
                self.tableau.setItem(i, j, QTableWidgetItem(texte))
        self.tableau.resizeColumnsToContents()


# --- Onglet 4 : Situations ---------------------------------------------------
class OngletSituations(QWidget):
    """Heatmap du coût du chip par distance x couverture (toutes équipes)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        info = QLabel(
            "Coût du chip = profondeur sans chip − profondeur avec chip. "
            "Vert = peu pénalisant, rouge = coûteux."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        self.canvas = Canvas(height=4.5)
        layout.addWidget(self.canvas)

    def mettre_a_jour(self, routes: pd.DataFrame) -> None:
        charts.dessiner_situations(self.canvas.figure, routes)
        self.canvas.draw_idle()


# --- Fenêtre principale ------------------------------------------------------
class FenetrePrincipale(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("🏈 Le coût du chip — NFL Big Data Bowl")
        self.resize(980, 760)

        self.summary = data.charger_summary()
        self.routes = data.charger_routes()
        self.rushers = data.charger_rushers()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Barre supérieure : sélecteurs mon équipe + adversaire (interactions
        # principales, toujours visibles).
        barre = QHBoxLayout()
        barre.addWidget(QLabel("<b>Mon équipe :</b>"))
        self.combo_equipe = QComboBox()
        self.combo_equipe.setMinimumWidth(120)
        self.combo_equipe.currentTextChanged.connect(self._on_equipe)
        barre.addWidget(self.combo_equipe)

        barre.addSpacing(24)
        barre.addWidget(QLabel("<b>Adversaire de dimanche :</b>"))
        self.combo_adversaire = QComboBox()
        self.combo_adversaire.setMinimumWidth(120)
        self.combo_adversaire.currentTextChanged.connect(self._on_adversaire)
        barre.addWidget(self.combo_adversaire)

        barre.addStretch(1)
        self.statut = QLabel("")
        barre.addWidget(self.statut)
        layout.addLayout(barre)

        trait = QFrame()
        trait.setFrameShape(QFrame.HLine)
        trait.setFrameShadow(QFrame.Sunken)
        layout.addWidget(trait)

        # Onglets.
        self.onglets = QTabWidget()
        self.onglet_equipe = OngletEquipe()
        self.onglet_joueur = OngletJoueur()
        self.onglet_adversaire = OngletAdversaire()
        self.onglet_situations = OngletSituations()
        self.onglets.addTab(self.onglet_equipe, "Mon équipe")
        self.onglets.addTab(self.onglet_joueur, "Fiche joueur")
        self.onglets.addTab(self.onglet_adversaire, "Adversaire")
        self.onglets.addTab(self.onglet_situations, "Situations")
        layout.addWidget(self.onglets)

        self._peupler_equipes()
        self._peupler_adversaires()

    def _peupler_equipes(self) -> None:
        equipes = data.liste_equipes(self.summary)
        self.combo_equipe.clear()
        if not equipes:
            self.statut.setText(
                "Aucune donnée dans results/. Lance d'abord : python src/fake_data.py"
            )
            self.onglet_situations.mettre_a_jour(self.routes)
            return
        self.combo_equipe.addItems(equipes)
        self.statut.setText(
            f"{len(equipes)} équipes · {len(self.summary)} joueurs · "
            f"{len(self.rushers)} rushers"
        )
        self.combo_equipe.setCurrentIndex(0)
        self._on_equipe(equipes[0])

    def _peupler_adversaires(self) -> None:
        equipes = data.liste_equipes_defense(self.rushers)
        self.combo_adversaire.clear()
        if not equipes:
            self.combo_adversaire.setEnabled(False)
            self.onglet_adversaire.info.setText(
                "rushers.csv absent : lance d'abord python -m src.compute."
            )
            return
        self.combo_adversaire.addItems(equipes)
        # Par défaut, un adversaire différent de l'équipe sélectionnée.
        mienne = self.combo_equipe.currentText()
        defaut = next((e for e in equipes if e != mienne), equipes[0])
        self.combo_adversaire.setCurrentText(defaut)
        self._on_adversaire(defaut)

    def _on_equipe(self, equipe: str) -> None:
        if not equipe:
            return
        self.onglet_equipe.mettre_a_jour(self.summary, equipe)
        self.onglet_joueur.mettre_a_jour(self.summary, self.routes, equipe)
        self.onglet_situations.mettre_a_jour(self.routes)

    def _on_adversaire(self, equipe: str) -> None:
        if not equipe:
            return
        self.onglet_adversaire.mettre_a_jour(self.rushers, equipe)


def main() -> int:
    app = QApplication(sys.argv)
    fenetre = FenetrePrincipale()
    fenetre.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
