# Datasheet — Régularité mensuelle TGV par liaisons (SNCF)

Cette fiche documente le jeu de données utilisé dans le projet **RailInsight-SNCF** selon le cadre *Datasheets for Datasets* : provenance, composition, qualité, prétraitements, conventions de calcul, usages et limites d'interprétation.

---

## 1. Provenance et motivation

- **Nom officiel :** Régularité mensuelle TGV par liaisons (`regularite-mensuelle-tgv-aqst.csv`)
- **Producteur :** SNCF Voyageurs (indicateurs publiés dans le cadre du suivi de l'Autorité de la Qualité de Service dans les Transports — AQST)
- **Source :** Portail Open Data SNCF (`data.sncf.com`)
- **Licence :** Licence Ouverte / Open Licence 2.0 (Etalab)
- **Objectif initial :** Publier chaque mois les indicateurs de ponctualité, d'annulation et de causes de retard des liaisons TGV nationales et internationales à des fins de transparence publique.
- **Usage dans RailInsight-SNCF :** Alimenter les modules d'analyse exploratoire et l'application Streamlit du projet (circulations et annulations, causes de retard, saisonnalité, persistance des retards et fiabilité des liaisons).

---

## 2. Composition du jeu de données

### 2.1 Vue d'ensemble (version analysée)

| Caractéristique | Valeur |
| --- | --- |
| Nom du fichier local | `data/raw/regularite-mensuelle-tgv-aqst.csv` |
| Format et encodage | CSV, séparateur `;`, UTF-8 |
| Taille du fichier | 2,77 Mo |
| Dimensions | 12 907 lignes × 26 colonnes |
| Granularité | 1 ligne = 1 liaison orientée (`Gare de départ` -> `Gare d'arrivée`) pour 1 mois et 1 type de service |
| Période couverte | `2018-01` à `2026-09` (105 mois) |
| Types de service | `National` : 11 339 lignes (87,9 %) ; `International` : 1 568 lignes (12,1 %) |
| Couverture géographique | 59 gares de départ, 59 gares d'arrivée, 130 liaisons orientées uniques |
| Clé d'unicité | `(Date, Service, Gare de départ, Gare d'arrivée)` — 0 doublon exact ou sur la clé |

### 2.2 Dictionnaire des 26 colonnes

| Colonne | Type brut | Unité / Format | Description |
| --- | --- | --- | --- |
| `Date` | `str` | `AAAA-MM` | Mois d'observation |
| `Service` | `str` | Catégorie | Type de desserte (`National` ou `International`) |
| `Gare de départ` | `str` | Texte | Nom de la gare d'origine |
| `Gare d'arrivée` | `str` | Texte | Nom de la gare de destination |
| `Durée moyenne du trajet` | `int64` | Minutes | Temps de parcours moyen théorique sur la liaison |
| `Nombre de circulations prévues` | `int64` | Trains | Nombre de trains programmés au plan de transport mensuel |
| `Nombre de trains annulés` | `int64` | Trains | Nombre de trains supprimés |
| `Commentaire annulations` | `float64` | Texte (vide) | Champ commentaire sur les annulations (100 % vide) |
| `Nombre de trains en retard au départ` | `int64` | Trains | Trains partis en retard |
| `Retard moyen des trains en retard au départ` | `float64` | Minutes | Retard moyen calculé uniquement sur les trains en retard au départ |
| `Retard moyen de tous les trains au départ` | `float64` | Minutes | Écart moyen au départ sur l'ensemble des trains circulés (peut être négatif en cas d'avance) |
| `Commentaire retards au départ` | `float64` | Texte (vide) | Champ commentaire sur les retards au départ (100 % vide) |
| `Nombre de trains en retard à l'arrivée` | `int64` | Trains | Trains arrivés en retard selon le seuil AQST |
| `Retard moyen des trains en retard à l'arrivée` | `float64` | Minutes | Retard moyen calculé uniquement sur les trains en retard à l'arrivée |
| `Retard moyen de tous les trains à l'arrivée` | `float64` | Minutes | Écart moyen à l'arrivée sur l'ensemble des trains circulés (peut être négatif en cas d'avance) |
| `Commentaire retards à l'arrivée` | `str` | Texte | Commentaires ponctuels sur les retards à l'arrivée (renseigné sur 5,4 % des lignes) |
| `Nombre trains en retard > 15min` | `int64` | Trains | Trains arrivés avec plus de 15 minutes de retard |
| `Retard moyen trains en retard > 15 (si liaison concurrencée par vol)` | `float64` | Minutes | Retard moyen des trains dépassant 15 minutes de retard |
| `Nombre trains en retard > 30min` | `int64` | Trains | Trains arrivés avec plus de 30 minutes de retard |
| `Nombre trains en retard > 60min` | `int64` | Trains | Trains arrivés avec plus de 60 minutes de retard |
| `Prct retard pour causes externes` | `float64` | % | Part des retards imputables aux causes externes (météo, obstacles, malveillance, etc.) |
| `Prct retard pour cause infrastructure` | `float64` | % | Part des retards liés à l'infrastructure ferroviaire (voies, signalisation, travaux) |
| `Prct retard pour cause gestion trafic` | `float64` | % | Part des retards liés à la gestion des circulations et sillons |
| `Prct retard pour cause matériel roulant` | `float64` | % | Part des retards liés aux rames (pannes, maintenance) |
| `Prct retard pour cause gestion en gare et réutilisation de matériel` | `float64` | % | Part des retards liés aux opérations en gare et à la réutilisation des rames |
| `Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)` | `float64` | % | Part des retards liés à l'affluence, l'assistance PSH ou l'attente de correspondances |

---

## 3. Qualité des données et anomalies constatées

L'audit exploratoire mené sur les 12 907 observations met en évidence les points suivants :

### 3.1 Valeurs manquantes

Seules les trois colonnes textuelles de commentaires comportent des valeurs manquantes :

| Colonne | Valeurs manquantes | Part manquante |
| --- | --- | --- |
| `Commentaire annulations` | 12 907 | 100,0 % |
| `Commentaire retards au départ` | 12 907 | 100,0 % |
| `Commentaire retards à l'arrivée` | 12 209 | 94,6 % (698 textes présents) |

Les 23 autres colonnes ne présentent aucune valeur manquante (`0 %`).

### 3.2 Valeurs négatives : avances normales vs anomalies

Cinq colonnes numériques contiennent des valeurs strictement négatives, qui ne relèvent pas toutes d'erreurs :

| Colonne | Nombre de valeurs négatives | Interprétation |
| --- | --- | --- |
| `Retard moyen de tous les trains au départ` | 170 | **Normal** (trains partis en avance en moyenne) |
| `Retard moyen de tous les trains à l'arrivée` | 122 | **Normal** (trains arrivés en avance en moyenne) |
| `Nombre trains en retard > 30min` | 43 | **Anomalie** (un effectif ne peut pas être négatif) |
| `Retard moyen trains en retard > 15 (si liaison concurrencée par vol)` | 8 | **Anomalie** (retard moyen négatif sur un sous-ensemble de trains en retard) |
| `Retard moyen des trains en retard à l'arrivée` | 2 | **Anomalie** (retard moyen négatif sur un sous-ensemble de trains en retard) |

### 3.3 Incohérences métier sur les volumes et les causes

| Contrôle métier | Lignes concernées | Conséquence |
| --- | --- | --- |
| `Nombre de circulations prévues <= 0` | 73 | Division par zéro ou volume incohérent pour le calcul de taux |
| `Durée moyenne du trajet <= 0` | 73 | Durée de parcours non exploitable |
| `Nombre de trains annulés > Nombre de circulations prévues` | 63 | Nombre de trains circulés négatif et taux d'annulation supérieur à 100 % |
| `Nombre de trains en retard au départ > trains circulés` | 1 | Taux de retard au départ supérieur à 100 % |
| `Nombre de trains en retard à l'arrivée > trains circulés` | 0 | Aucune incohérence détectée |
| `Nombre de trains annulés < 0` | 0 | Aucune incohérence détectée |
| Retards à l'arrivée > 0 avec somme des 6 causes égale à 0 % | 80 | Répartition des causes absente malgré des retards constatés |
| Somme des 6 causes de retard > 100,5 % | 0 | Aucun dépassement détecté |

---

## 4. Prétraitement et conventions de calcul

Les traitements mis en œuvre dans `src/projet_railinsight/` (notamment via `data_processing.py`, `preprocessing_fiabilite.py`, les modules SQL `db_init.py` / `moteur_sql.py` et les modules métier) reposent sur les règles suivantes :

1. **Suppression des colonnes non exploitables :** les trois colonnes de commentaires textuels sont écartées des analyses quantitatives.
2. **Traitement différencié des valeurs négatives :** les valeurs négatives des trois colonnes aberrantes (`Nombre trains en retard > 30min`, `Retard moyen trains en retard > 15...`, `Retard moyen des trains en retard à l'arrivée`) sont remplacées par `NaN`. Les valeurs négatives des retards moyens sur *tous* les trains sont conservées car elles représentent des avances.
3. **Filtrage des incohérences de volumes :** les observations présentant des circulations prévues nulles ou négatives, des annulations supérieures aux circulations prévues, ou un nombre de trains en retard supérieur aux trains circulés sont exclues avant calcul des taux.
4. **Construction des indicateurs clés :**
   - **Trains circulés :** `trains_circules = Nombre de circulations prévues - Nombre de trains annulés`
   - **Taux d'annulation pondéré (%) :** `sum(Nombre de trains annulés) / sum(Nombre de circulations prévues) * 100`
   - **Taux de retard à l'arrivée pondéré (%) :** `sum(Nombre de trains en retard à l'arrivée) / sum(trains_circules) * 100`
   - **Liaison orientée :** concaténation `Gare de départ -> Gare d'arrivée` (les sens aller et retour restent distincts).
5. **Choix de la pondération :** pour les agrégations par liaison, par année ou par service, les taux sont pondérés par les volumes réels (trains prévus ou circulés) plutôt que calculés par moyenne simple des taux mensuels, afin d'éviter qu'une liaison peu fréquentée ne pèse autant qu'un grand axe.
6. **Analyse des causes de retard :** les 80 lignes présentant des retards sans ventilation de causes (somme des 6 pourcentages nulle) sont filtrées avant l'étude de la répartition des causes.

---

## 5. Usages et limites d'interprétation

### 5.1 Usages couverts par RailInsight-SNCF

- Comparaison des volumes de circulation, des taux d'annulation et des retards par liaison (`circulations.py`).
- Analyse de la répartition des six grandes familles de causes de retard (`causes.py`).
- Étude de la saisonnalité mensuelle et des tendances pluriannuelles (`saisonnalite.py`).
- Mesure de la persistance temporelle des retards d'un mois sur l'autre (`persistence.py`).
- Évaluation de la fiabilité globale des liaisons (`fiabilite.py`).

### 5.2 Limites et biais d'interprétation

- **Granularité mensuelle agrégée :** les données ne permettent pas d'analyser un train individuel, un jour de la semaine, une tranche horaire ni un événement ponctuel isolé.
- **Absence de volume voyageurs :** les indicateurs comptent des *trains*, pas des *passagers*. Un retard sur un TGV en unité multiple aux heures de pointe pèse autant qu'un train peu rempli.
- **Définition réglementaire du retard :** le jeu de données reflète les seuils de comptabilisation SNCF/AQST (qui tiennent compte de la durée du trajet pour qualifier un train « en retard ») et exclut mécaniquement les trains annulés des indicateurs de retard à l'arrivée.
- **Corrélation n'est pas causalité :** un lien statistique entre volume de desserte, durée de trajet, annulations et retards ne suffit pas à établir une relation causale sans données externes (météo, travaux planifiés, mouvements sociaux, saturation des nœuds ferroviaires).
- **Effet de taille sur les petites liaisons :** sur les liaisons à faible nombre de circulations mensuelles, un petit nombre d'incidents suffit à faire fortement varier les taux relatifs.
- **Ruptures historiques :** la période 2018–2026 inclut des épisodes atypiques (crise sanitaire Covid-19 en 2020–2021, grèves majeures, grands travaux d'infrastructure) qui créent des valeurs extrêmes dans les séries temporelles.

---

## 6. Distribution, confidentialité et maintenance

- **Données personnelles (RGPD) :** le jeu de données est entièrement agrégé au niveau mensuel et par liaison ; il ne contient aucune donnée personnelle identifiable ni aucune information sur les voyageurs ou les agents.
- **Stockage dans le dépôt :** conformément aux bonnes pratiques du projet, le fichier CSV brut n'est pas versionné sur GitHub (exclu via `.gitignore`). Chaque utilisateur place sa copie dans `data/raw/regularite-mensuelle-tgv-aqst.csv`.
- **Mise à jour :** SNCF Open Data actualise ce jeu de données mensuellement. Les chiffres de la section 2 et de la section 3 correspondent à l'extraction couvrant `2018-01` à `2026-09` ; ils doivent être réactualisés si une version plus récente du CSV est chargée.
