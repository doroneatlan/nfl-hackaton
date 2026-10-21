# 🏈 Roadmap équipe – "Le coût du chip"

NFL Big Data Bowl – Paris Side Quest · Epitech · 21 octobre 2026 · **13:00 → 16:00**

---

## 🎯 L'idée en 30 secondes

Sur une action de passe, un receveur (TE, RB ou WR) peut :
- 🏃 **courir direct** sa route pour recevoir le ballon
- 🛡️ **faire un chip** : bousculer rapidement un défenseur qui fonce sur le lanceur (QB), **puis** partir courir

Le chip protège le QB mais retarde le receveur. **Personne ne mesure aujourd'hui si l'échange est rentable.**

**Notre outil** : une interface pour le coach qui dit, **joueur par joueur et situation par situation**, si le chip vaut le coup.

> Phrase du README : *"Un chip coûte X yards de route au receveur et évite Y % de pression au QB. Voici les joueurs et les situations où l'échange est rentable."*

---

## 🧭 Parcours du coach dans l'interface

| Étape | Ce qu'il voit | Ce qu'il en tire |
|---|---|---|
| 1. Vue d'ensemble | Tableau de tous les joueurs qui font des chips + verdict ✅/❌ | Qui est bon, en 10 secondes |
| 2. Fiche joueur | Terrain avec ses trajets : 🔵 sans chip / 🔴 avec chip | Il **voit** le retard |
| 3. Situations | Rentabilité selon distance à faire et type de défense | *Quand* faire le chip |
| 4. Décision | — | Son plan de jeu pour dimanche |

**Priorité** : étapes 1 et 2 à fond. Étape 3 si on a le temps.

---

## 🏗️ Architecture

```
nfl-data/data (811 Mo)  →  src/compute.py  →  results/*.csv (petits)  →  app.py (Streamlit)
       Personne 1                                  le "contrat"               Personne 2 + 3
```

L'interface lit **uniquement** les CSV de `results/`. Elle reste rapide et peut être mise en ligne pour le jury.

### Structure du dépôt

```
nfl-hackaton/
├── README.md            ← lu en premier par le jury
├── requirements.txt
├── app.py               ← interface Streamlit
├── src/
│   ├── compute.py       ← calculs (données → CSV)
│   └── field.py         ← dessin du terrain + trajets
├── results/             ← CSV produits par compute.py
├── screenshots/         ← captures pour le README
└── nfl-data/            ← données fournies (ne pas pousser sur GitHub si trop lourd)
```

---

## 📜 Le contrat CSV (à valider ensemble à 13:15, puis on n'y touche plus)

### `results/player_summary.csv` : une ligne par joueur

| Colonne | Description |
|---|---|
| `nflId` | identifiant joueur |
| `nom` | `displayName` |
| `poste` | TE / RB / WR |
| `equipe` | équipe en attaque |
| `nb_chips` / `nb_sans_chip` | nombre d'actions de chaque type |
| `profondeur_chip` / `profondeur_sans_chip` | yards moyens au-delà de la ligne au moment du lancer |
| `separation_chip` / `separation_sans_chip` | distance moyenne (yards) au défenseur le plus proche au lancer |
| `pression_chip` / `pression_sans_chip` | % d'actions avec hit/hurry/sack sur le QB |
| `verdict` | `rentable` / `pas rentable` / `pas assez de données` |

### `results/routes.csv` : les trajets, pour le dessin

| Colonne | Description |
|---|---|
| `gameId`, `playId`, `nflId`, `frameId` | clés |
| `x`, `y` | position **normalisée**, relative à la ligne de mêlée |
| `chip` | `True` / `False` |
| `down`, `yardsToGo`, `couverture` | contexte (`pff_passCoverage`) |

---

## 👥 Répartition

### 👤 Personne 1 : données et calculs (`src/compute.py`)

C'est le chemin critique : à confier au plus à l'aise avec pandas.

- [ ] Charger le tracking avec seulement les colonnes utiles (`usecols`)
- [ ] Garder les actions des TE / RB / WR avec `pff_role == "Pass Route"`
  - **Avec chip** : `pff_blockType == "CH"` (~1 500 actions)
  - **Sans chip** : `pff_blockType` vide
- [ ] Normaliser le sens : si `playDirection == "left"` → `x = 120 - x`, `y = 53.3 - y`
- [ ] Repère : ligne de mêlée = `x` du ballon (`nflId` vide) à l'événement `ball_snap`
- [ ] Au frame `pass_forward` (ou `autoevent_passforward`), calculer :
  - **profondeur** = `x_joueur - x_ligne`
  - **séparation** = distance au défenseur le plus proche
- [ ] **Pression** : l'action a-t-elle un `pff_hit`, `pff_hurry` ou `pff_sack` = 1 ?
- [ ] Agréger par joueur → `player_summary.csv`
- [ ] Exporter les trajets (snap → lancer) → `routes.csv`
- [ ] **Verdict** : minimum **10 chips** pour juger, sinon `pas assez de données`

⚠️ **Plan B à 14:30** : si séparation ou pression ne sont pas prêtes, livrer le CSV avec **la profondeur seule**. Les colonnes manquantes restent vides, l'interface doit le supporter.

### 👤 Personne 2 : interface (`app.py`)

- [ ] **Dès 13:15**, créer un faux `player_summary.csv` de 10 lignes au bon format
- [ ] Page **Vue d'ensemble** : tableau trié, filtres équipe / poste, verdict en couleur
- [ ] Page **Fiche joueur** : menu de sélection, chiffres clés avec chip et sans chip, intégration du terrain de la Personne 3
- [ ] (bonus) Page **Situations**
- [ ] **15:00** : remplacer les faux CSV par les vrais
- [ ] Lancement : `streamlit run app.py`

### 👤 Personne 3 : graphiques, README, soumission

- [ ] `src/field.py` : fonction `dessiner_trajets(routes_df, nflId)` qui renvoie une figure Plotly (terrain vert, ligne de mêlée, 🔵 sans chip, 🔴 avec chip)
- [ ] Graphique situations : rentabilité du chip selon `yardsToGo` (court / moyen / long) et `couverture`
- [ ] Créer le dépôt GitHub **public** dès 13:15 et vérifier le lien en navigation privée
- [ ] README final : 3 à 5 phrases + "comment lancer" + captures + limites
- [ ] Captures d'écran dans `screenshots/`
- [ ] (bonus) Déploiement sur Streamlit Community Cloud
- [ ] ⏰ **Gardien de l'horloge** : annonce 14:00, 15:00, 15:30, 15:45
- [ ] **Soumission** sur le formulaire Pulse

---

## ⏱️ Planning

| Heure | Tous | P1 – Données | P2 – Interface | P3 – Graphiques / README |
|---|---|---|---|---|
| **13:00** | Lancement, lecture du sujet | | | |
| **13:00–13:15** | ✅ Valider l'idée, le **contrat CSV**, créer le dépôt | | | |
| **13:15–14:00** | | Chargement + normalisation | Faux CSV + page vue d'ensemble | Dépôt + fonction terrain |
| **14:00** | 🗣️ **Point 5 min** : qui est bloqué ? | | | |
| **14:00–15:00** | | Métriques + export CSV | Page fiche joueur | Graphique situations + brouillon README |
| **14:30** | | ⚠️ Décision plan B si besoin | | |
| **15:00–15:30** | 🔧 **Assemblage** : vrais CSV dans l'app | | | |
| **15:30** | 🧊 **GEL DU CODE** | | | |
| **15:30–15:45** | | Vérifier les chiffres | Captures d'écran | README final, push |
| **15:45** | 📤 **SOUMISSION** (15 min de marge) | | | |
| **16:00** | ⛔ Clôture | | | |

---

## ⚠️ Limites à assumer dans le README

1. **Peu d'actions par joueur** : on ne juge que les joueurs avec au moins 10 chips.
2. **Le chip n'est pas fait au hasard** : le coach l'appelle quand il s'attend à de la pression. On compare donc des situations proches (même `down`, même distance, même couverture) plutôt que tout mélangé.
3. **Le tracking s'arrête au lancer** : on mesure la route jusqu'au lancer, pas ce qui se passe après la réception.

---

## ✅ Checklist de soumission (Personne 3, à 15:40)

- [ ] Le dépôt est **public** et le lien marche en navigation privée
- [ ] Le README commence par l'idée en 3 à 5 phrases
- [ ] Le README contient une ligne "comment lancer" : `pip install -r requirements.txt` puis `streamlit run app.py`
- [ ] Des captures d'écran sont visibles directement dans le README
- [ ] L'insight porte clairement sur **TE / RB / WR**
- [ ] Le dossier `results/` est poussé, pour que l'app tourne sans les 811 Mo de données
- [ ] Le formulaire Pulse est envoyé avant **15:45**
