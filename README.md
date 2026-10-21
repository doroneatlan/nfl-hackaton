# 🏈 Le coût du chip

## L'idée

Sur une action de passe, un receveur (TE, RB ou WR) a le choix : courir directement sa route pour recevoir le ballon, ou faire un **chip** — bousculer au passage un défenseur qui fonce sur le quarterback avant de partir courir. Le chip protège le QB, mais il retarde le receveur et creuse son retard sur la défense. Jusqu'ici, personne ne mesurait vraiment si cet échange valait le coup. Notre outil le quantifie, **joueur par joueur et situation par situation**, pour dire au coach quand le chip est rentable.

> *Un chip coûte X yards de route au receveur et évite Y % de pression au QB. Voici les joueurs et les situations où l'échange est rentable.*

## ✨ Ce que montre l'outil

- **Vue d'ensemble** : tableau de tous les joueurs qui font des chips, avec un verdict ✅ rentable / ❌ pas rentable pour chacun, en un coup d'œil.
- **Fiche joueur** : le terrain avec ses trajets réels, 🔵 sans chip et 🔴 avec chip, pour *voir* le retard, accompagné des chiffres clés comparés.
- **Graphique situations** : la rentabilité du chip selon la distance à faire et le type de couverture défensive, pour savoir *quand* le déclencher.

## 🚀 Comment lancer

```shell
pip install -r requirements.txt
streamlit run app.py
```

L'application lit **uniquement** les CSV légers du dossier `results/`. Pas besoin de télécharger les 811 Mo de données brutes pour la faire tourner.

## 🖼️ Captures d'écran

<!-- captures à ajouter avant soumission -->

![Vue d'ensemble](screenshots/vue_ensemble.png)

![Fiche joueur](screenshots/fiche_joueur.png)

![Situations](screenshots/situations.png)

## 📊 Les données

NFL Big Data Bowl 2022 : tracking Next Gen Stats (position de chaque joueur image par image) combiné au scouting PFF (rôles et types de bloc). Périmètre : semaines 1 à 8 de la saison 2021.

## ⚠️ Limites

1. **Peu d'actions par joueur** : le chip reste rare, donc on ne juge que les joueurs avec au moins **10 chips**.
2. **Le chip n'est pas appelé au hasard** : le coach le déclenche quand il attend de la pression. On compare donc des situations proches (même down, même distance, même couverture) plutôt que tout mélanger.
3. **Le tracking s'arrête au lancer** : on mesure la route jusqu'au lancer du QB, pas ce qui se passe après la réception.

## 🏗️ Architecture

```
data brutes  →  src/compute.py  →  results/*.csv  →  app.py (Streamlit)
                  (calculs)         le "contrat"       l'interface
```

`src/compute.py` transforme les données brutes en petits CSV dans `results/`, qui constituent le « contrat » du projet. L'interface `app.py` lit **uniquement** ces CSV de `results/` : elle reste rapide et peut être mise en ligne pour le jury.
