# Analyse de la fiabilité des liaisons TGV

**Projet :** RailInsight-SNCF  
**Statut :** Cadrage initial — V0.2

## 1. Question de recherche

**Quelles sont les liaisons TGV les plus touchées par les retards à l'arrivée ?**

## 2. Problématique

### 2.1. Problématique générale du groupe

Quels facteurs expliquent les différences de régularité entre les liaisons TGV, et dans quelle mesure peut-on prévoir les retards et les annulations ?

### 2.2. Sous-problématique étudiée

Quelles sont les liaisons TGV les moins régulières, comment leurs taux de retard évoluent-ils dans le temps et peut-on anticiper leur évolution mensuelle ?

### 2.3. Objectifs

1. **Analyse descriptive :** identifier les liaisons présentant les taux de retard les plus élevés.
2. **Analyse temporelle :** étudier l'évolution mensuelle des retards.
3. **Analyse prédictive :** prévoir les taux mensuels de retard à partir des données historiques.


## 3. Données et préparation

L'analyse repose sur le jeu de données mensuel de régularité des TGV fourni par la SNCF, couvrant la période de janvier 2018 à septembre 2026.

Le préprocessing est réalisé dans `preprocessing_fiabilite.py` à partir du fichier CSV brut.

Les principales opérations sont :

- Conversion des dates.
- Calcul du nombre de trains circulés.
- Exclusion des observations incompatibles avec le calcul des taux.
- Remplacement par des valeurs manquantes des effectifs incohérents de retards supérieurs à 30 minutes.

Sur les 12 907 observations initiales, 12 834 sont conservées après nettoyage. La variable des retards supérieurs à 30 minutes contient 357 valeurs manquantes après traitement.

Le fichier source n'est pas modifié.

## 4. Indicateurs de fiabilité

### 4.1. Taux de retard à l'arrivée

Le taux de retard correspond à la proportion de trains en retard parmi les trains ayant effectivement circulé.

**Trains circulés = Trains prévus − Trains annulés**

**Taux de retard (%) = 100 × Trains en retard / Trains circulés**

### 4.2. Taux d'annulation

**Taux d'annulation (%) = 100 × Trains annulés / Trains prévus**

Pour une période comprenant plusieurs mois, les taux sont calculés à partir des sommes des effectifs, et non de la moyenne simple des taux mensuels.

## 5. Méthodologie d'analyse

Les liaisons sont définies par le service, la gare de départ et la gare d'arrivée. Les deux sens d'un trajet sont considérés séparément.

Le classement est réalisé selon le taux agrégé de retard à l'arrivée.

Pour l'analyse de référence de 2025, seules les liaisons présentant au moins 500 trains circulés et 10 mois d'observation sont retenues.

L'évolution temporelle est étudiée à partir des taux mensuels de retard de chaque liaison.

## 6. Résultats principaux — 2025

Les trois liaisons présentant les taux de retard les plus élevés parmi celles retenues sont :

| Liaison | Trains circulés | Trains en retard | Taux de retard |
|---|---:|---:|---:|
| Paris Est → Stuttgart | 1 429 | 808 | 56,54 % |
| Italie → Paris Lyon | 838 | 284 | 33,89 % |
| Paris Est → Francfort | 2 044 | 645 | 31,56 % |

La liaison Paris Est → Stuttgart présente le taux le plus élevé du classement étudié.

Ces résultats sont descriptifs et ne permettent pas, à eux seuls, d'identifier les causes des retards.

## 7. Implémentation Python

L'analyse repose sur les modules suivants :

- `preprocessing_fiabilite.py` : chargement et préparation autonome des données.
- `fiabilite.py` : calcul des indicateurs, classement des liaisons et évolution temporelle.
- `tests/test_fiabilite.py` : tests des calculs et des méthodes d'analyse.
- `tests/test_preprocessing_fiabilite.py` : tests de préparation des données.

La classe `AnalyseFiabilite` expose notamment :

- `calculer_indicateurs()`
- `classer_liaisons()`
- `evolution_temporelle()`

## 8. Tests et qualité du code

Les vérifications réalisées comprennent :

- 25 tests unitaires réussis avec pytest.
- Une couverture globale de 93 % pour les deux modules Python.
- Une analyse Ruff sans erreur.
- Un formatage conforme à Ruff.

## 9. Application Streamlit

La page `pages/05_Fiabilite.py` permet :

- De sélectionner une année et des seuils de représentativité.
- De visualiser le Top 10 des liaisons les plus touchées par les retards.
- De consulter l'évolution mensuelle d'une liaison.
- D'afficher le classement détaillé.

La préparation des données est exécutée automatiquement à partir du CSV brut.

## 10. Limites et perspectives

Les résultats dépendent de la période étudiée et des seuils de sélection retenus.

Les données de 2026 sont incomplètes, puisqu'elles s'arrêtent en septembre. Les observations de 2020 doivent également être interprétées dans leur contexte particulier.

Certaines incohérences concernant les seuils de retard et les pourcentages de causes nécessitent une analyse complémentaire.

Une extension Machine Learning est prévue pour prédire les taux mensuels de retard et intégrer ces prévisions dans une deuxième version de l'application Streamlit.
