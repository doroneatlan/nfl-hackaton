"""!
@file figures.py
@brief Figures statiques du README, générées depuis results/ (visibles sans lancer l'app).

Lancement depuis la racine du projet : python -m src.figures
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

## Dossier des CSV produits par src.compute.
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

## Dossier des images affichées dans le README.
FIGURES_DIR = Path(__file__).resolve().parent.parent / "figures"

## Couleur de chaque verdict.
VERDICT_COLORS = {"rentable": "#2e7d32", "incertain": "#9e9e9e", "pas rentable": "#c62828"}

## Couleurs des routes : bleu sans chip, rouge avec chip.
ROUTE_COLORS = {False: "#1f77b4", True: "#d62728"}

## Joueurs nommés sur le nuage de points.
HIGHLIGHTED_PLAYERS = ("Tyler Higbee", "Dawson Knox", "Noah Fant", "Austin Hooper",
                       "Travis Kelce", "Devin Singletary", "T.J. Hockenson")

## Joueurs comparés sur le dessin des trajets.
ROUTE_PLAYERS = ("Tyler Higbee", "Dawson Knox")


def plot_cost_vs_gain(summary: pd.DataFrame) -> plt.Figure:
    """!
    @brief Nuage de points : ce que le chip coûte (yards) contre ce qu'il rapporte (pression évitée).
    @param summary Synthèse par joueur (player_summary.csv).
    @return La figure.
    """
    judged = summary[summary["verdict"].isin(VERDICT_COLORS)]
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.axhline(0, color="black", linewidth=0.8)

    for verdict, color in VERDICT_COLORS.items():
        group = judged[judged["verdict"] == verdict]
        ax.scatter(group["cout_profondeur"], group["pression_evitee"], s=group["nb_chips_mesures"] * 12,
                   color=color, alpha=0.75, edgecolor="white", label=f"{verdict} ({len(group)})")

    for _, player in judged[judged["nom"].isin(HIGHLIGHTED_PLAYERS)].iterrows():
        ax.annotate(f"{player['nom']} ({player['confiance']:.0f} %)",
                    (player["cout_profondeur"], player["pression_evitee"]),
                    xytext=(6, 6), textcoords="offset points", fontsize=9)

    ax.set_xlabel("Coût du chip : yards de profondeur perdus au lancer")
    ax.set_ylabel("Gain : pression évitée sur le défenseur visé (points de %)")
    ax.set_title("Chaque joueur : ce que le chip coûte, ce qu'il rapporte\n"
                 "(taille = nombre de chips, % = confiance que le gain n'est pas dû au hasard)")
    ax.legend(title="Verdict", loc="lower right")
    fig.tight_layout()
    return fig


def plot_situations(situations: pd.DataFrame) -> plt.Figure:
    """!
    @brief Barres : pression attendue contre pression réelle des défenseurs bousculés, par situation.
    @param situations Table des situations (situations.csv).
    @return La figure.
    """
    table = situations.copy()
    table["label"] = table["situation"].str.capitalize() + " : " + table["valeur"]
    table["attendue"] = table["pressions_attendues"] / table["nb_chips"] * 100
    table["reelle"] = table["pressions_reelles"] / table["nb_chips"] * 100
    positions = range(len(table))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([p + 0.2 for p in positions], table["attendue"], height=0.4,
            color="#bdbdbd", label="Pression attendue (taux habituel des défenseurs)")
    ax.barh([p - 0.2 for p in positions], table["reelle"], height=0.4,
            color="#2e7d32", label="Pression réelle quand ils reçoivent un chip")

    for position, (_, row) in zip(positions, table.iterrows()):
        ax.text(max(row["attendue"], row["reelle"]) + 0.3, position,
                f"confiance {row['confiance']:.0f} % · n = {row['nb_chips']}", va="center", fontsize=9)

    ax.set_yticks(list(positions), table["label"])
    ax.invert_yaxis()
    ax.set_xlim(0, table[["attendue", "reelle"]].max().max() + 6)
    ax.set_xlabel("Pression sur le QB par le défenseur visé (%)")
    ax.set_title("Le chip freine-t-il le défenseur ? Surtout contre une défense en individuelle (Man)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    fig.tight_layout()
    return fig


def plot_routes(routes: pd.DataFrame, summary: pd.DataFrame) -> plt.Figure:
    """!
    @brief Trajets de deux joueurs du snap au lancer, chacun ramené à son point de départ.
    @param routes Trajets (routes.csv).
    @param summary Synthèse par joueur (player_summary.csv), pour les noms et les chiffres.
    @return La figure.
    """
    fig, axes = plt.subplots(1, len(ROUTE_PLAYERS), figsize=(11, 6.5), sharey=True)
    for ax, name in zip(axes, ROUTE_PLAYERS):
        player = summary[summary["nom"] == name].iloc[0]
        paths = routes[routes["nflId"] == player["nflId"]].sort_values("frameId")

        for (_, chip), path in paths.groupby(["playId", "chip"]):
            lateral = path["y"] - path["y"].iloc[0]
            ax.plot(lateral, path["x"], color=ROUTE_COLORS[chip], alpha=0.6 if chip else 0.3,
                    linewidth=1.6 if chip else 1)

        ax.axhline(0, color="black", linewidth=1, linestyle="--")
        ax.set_title(f"{name} : {player['verdict']}\n"
                     f"profondeur {player['profondeur_sans_chip']:.1f} yd sans chip, "
                     f"{player['profondeur_chip']:.1f} yd avec", fontsize=10)
        ax.set_xlabel("Déplacement latéral (yards)")
    axes[0].set_ylabel("Yards au-delà de la ligne de mêlée")
    axes[0].plot([], [], color=ROUTE_COLORS[False], label="sans chip")
    axes[0].plot([], [], color=ROUTE_COLORS[True], label="avec chip")
    axes[0].legend(loc="upper left")
    fig.suptitle("Le chip raccourcit la route : trajets du snap au lancer")
    fig.tight_layout()
    return fig


def main() -> None:
    """!
    @brief Génère les trois figures du README dans figures/.
    """
    summary = pd.read_csv(RESULTS_DIR / "player_summary.csv")
    situations = pd.read_csv(RESULTS_DIR / "situations.csv")
    routes = pd.read_csv(RESULTS_DIR / "routes.csv")

    FIGURES_DIR.mkdir(exist_ok=True)
    figures = {
        "cout_vs_gain.png": plot_cost_vs_gain(summary),
        "situations.png": plot_situations(situations),
        "trajets_higbee_knox.png": plot_routes(routes, summary),
    }
    for name, fig in figures.items():
        fig.savefig(FIGURES_DIR / name, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"figures/{name}")


if __name__ == "__main__":
    main()
