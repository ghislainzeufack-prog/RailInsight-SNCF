# RailInsight - Analyse de la régularité des TGV

## Présentation

**RailInsigth** est un projet collectif d'analyse exploratoire de données et de développement Python. Notre objectif est de créer une application Web **Streamlit** interactive, accessible au grand public, pour explorer les différences de régularité entre les liaisons TGV françaises à partir des données ouvertes de la SNCF.

Nous souhaitons présenter des résultats chiffrés, des visualisations compréhensibles et des limites d'interprétation explicites.

## Problématique

**Comment la fiabilité des liaisons TGV varie-t-elle, et quels facteurs sont associés aux retards et aux annulations au fil du temps ?**

Le travail est réparti en cinq analyses complémentaires :

| Membre | Axe d'analyse
| --- | --- |
| Ghislain ZEUFACK | Comprendre les causes des retards |
| Romain VALLÉE | Saisonnalité des retards |
| Manganaw N'DAAM | Persistance des retards dans le temps |
| Emmanuel TAGAE | Comparaison de la fiabilité des liaisons |
| Jonathan RAKOTOVAO | Volume de circulation et annulations |

Chaque membre a développé progressivement son module Python, ses tests, ses visualisations et sa page Streamlit, et les contributions ont été réunies dans **une seule application**

## Données utilisées

**Source:** [SNCF Open Data - Régularité mensuelle TGV](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/information/)

Le jeu de données décrit des indicateurs mensuels par liason, notamment les circulations prévues, les annulations, les retards et la répartition des causes de retard.

Les données brutes ne sont pas incluses par défaut dans le dépôt. Les conventions de calcul, la qualité des données et les limites d'interprétation sont détaillées dans la **datasheet** commune, dans `docs/datasheet_sncf.md` (à venir)

# Technologies prévues

- **Python 3.14** et **uv** : environnement et dépendances du projet.
- **Pandas** : préparation et analyse exploratoire des données.
- **Plotly** et **Streamlit** : visualisations interactives et application web.
- **pytest** et **pytest-cov** : tests unitaires et mesure de couverture.
- **Ruff** : contrôles de style et formatage du code
- **Sphinx** : documentation technique.
- **Git, GitHub et GitHub Actions** : collaboration et intégration continue.

## Installation locale

## Prérequis

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/)


## Récupérer le projet

Ouvrir un terminal adapté à son système : **PowerShell** sous Windows, un **terminal** sous macOS/Linux.

Cloner le dépôt GitHub :

```text
git clone https://github.com/ghislainzeufack-prog/RailInsight-SNCF.git
cd RailInsight-SNCF
```

Se placer dans le dossier du projet :

```text
cd RailInsight
```

Installer les dépendances du projet :

```text
uv sync
```

`uv sync` prépare un environnement virtuel `.venv` adapté au système d'exploitation et installe les dépendances définies dans le projet.

**Ne pas exécuter `uv init` après avoir cloné le dépôt.**

## Organisation du projet

Structure prévue (certains fichiers et dossiers seront créés progressivement) :

```text
railinsight-sncf/
├── app.py                         # Accueil et point d'entrée Streamlit
├── pages/                         # Pages des cinq analyses
├── src/
│   └── railinsight_sncf/          # Code Python métier réutilisable
│       ├── __init__.py
│       ├── causes.py              # Ghislain
│       ├── circulations.py        # Jonathan
│       ├── saisonnalite.py        # Romain
│       ├── persistance.py         # Nelson
│       └── fiabilite.py           # Emmanuel
├── tests/                         # Tests unitaires et d'intégration
├── docs/                          # Sphinx, datasheet et analyses
├── data/                          # Données locales non publiées par défaut
├── logs/                          # Journaux locaux
├── pyproject.toml                 # Configuration et dépendances
├── uv.lock                        # Verrouillage des versions
├── .gitignore                     # Fichiers exclus du dépôt
└── README.md
```

**Principe d'architecture :** les traitements et calculs sont placés dans `src/projet_railinsight/`. Le fichier `app.py` et les fichiers de `pages/` présentent les résultats dans Streamlit, sans dupliquer la logique d'analyse.

## Lancer l'application

```text
uv run streamlit run app.py
```

## Appeler les fonctions

Après clonage et `uv sync`, la connexion est prête : le compte de lecture est inclus dans le projet. Aucun fichier est à créer.

### Exécuter une requête SQL

```python
from projet_railinsight.moteur_sql import creer_connexion, executer_requete

engine = creer_connexion()

# Entrée exemple
requete = "SELECT COUNT(*) AS nombre_lignes FROM regularite_tgv WHERE service = ?"
data = executer_requete(engine, requete, ["National"])

# Sortie : un DataFrame Pandas (valeur illustrative)
#    nombre_lignes
# 0          12000
```

### Analyser la saisonnalité

```python
from projet_railinsight.saisonnalite import analyser_saisonnalite

# Entrée : tous les paramètres
resultats = analyser_saisonnalite(
    engine=engine,
    nettoyage=True,       # False pour les données brutes
    service="National",  # None pour tous les services, International pour les trains internationaux
    annee_debut=2024,     # None pour aucune borne de début
    annee_fin=2025,       # None pour aucune borne de fin
)

# Sortie : un dictionnaire
# {
#     "mensuel": DataFrame des totaux et taux par mois,
#     "description": {"apercu": DataFrame, "statistiques": DataFrame},
#     "saisonnalite": DataFrame des moyennes par mois,
#     "correlations": DataFrame des corrélations,
#     "regression": dictionnaire des résultats du modèle,
# }

```

## Tests et qualité

```text
uv run pytest
uv run pytest --cov=railinsight_sncf --cov-report=term-missing
```

La cible du projet est une **couverture d'au moins 90 %** du code applicatif mesuré. Les contrôles de style, la présence de docstrings, les tests et la couverture sont automatisés avec **GitHub Actions**.

## Documentation

- **README (ce fichier)** : comprendre, installer, lancer et utiliser l'application.
- **Datasheet** (`docs/datasheet_sncf.md`, à venir) : provenance, composition, traitements, usages et limites des données.
- **Sphinx** (`docs/`, à configurer) : documentation des fonctions, méthodes et classes Python.

## Application en ligne et déploiement

**Lien Streamlit :** (à ajouter après le premier déploiement public.)

(Les étapes de déploiement seront documentées ici une fois vérifiées sur l'application réelle)