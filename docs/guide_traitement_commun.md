
# Guide d'utilisation du traitement commun SNCF

## Objectif

Le module `common_processing.py` fournit des fonctions communes
pour charger les données SNCF, contrôler leur qualité et identifier
les observations incohérentes.

Il permet aux membres de l'équipe RailInsight-SNCF de réutiliser
les mêmes contrôles dans leurs analyses.

**Principe :** le module signale les incohérences, mais ne supprime
pas automatiquement les observations concernées.

## 1. Importer les fonctions

```python
from projet_railinsight.common_processing import (
    NOM_CONTROLE_SEUILS,
    charger_donnees,
    construire_incoherences,
    controler_qualite_donnees,
    get_masque_lignes_incoherentes,
)
```

## 2. Charger les données SNCF

```python
df = charger_donnees()
```

Cette fonction :
- lit le fichier CSV SNCF ;
- conserve la colonne `Date` originale ;
- crée une colonne `Date_parsed` au format datetime.

## 3. Contrôler les effectifs

```python
df_controle = controler_qualite_donnees(df)
```

Cette fonction ajoute :
- `Trains réalisés` : circulations prévues moins trains annulés ;
- `effectifs_coherents` : indique si les prévisions et annulations
  sont cohérentes.

Elle ne modifie pas le DataFrame original.

## 4. Construire les indicateurs d'incohérence

```python
incoherences = construire_incoherences(df)
```

Le résultat est un DataFrame de booléens, avec les mêmes index
que les données initiales.

Chaque colonne représente un contrôle :
- `True` : une incohérence est détectée ;
- `False` : aucune incohérence détectée par ce contrôle.

Les contrôles portent notamment sur :
- les dates invalides ;
- certaines valeurs négatives ;
- les annulations supérieures aux prévisions ;
- les retards supérieurs aux effectifs de trains ;
- la cohérence des seuils 15, 30 et 60 minutes ;
- les pourcentages de retard hors de l'intervalle [0, 100].

## 5. Sélectionner les contrôles souhaités

Par exemple, pour identifier les observations dont les seuils
de retard sont incohérents :

```python
masque = get_masque_lignes_incoherentes(
    incoherences,
    [NOM_CONTROLE_SEUILS],
)
```

La fonction renvoie une série booléenne :
- `True` : ligne présentant au moins une incohérence sélectionnée ;
- `False` : ligne ne présentant aucune incohérence sélectionnée.

Plusieurs contrôles peuvent être combinés :

```python
masque = get_masque_lignes_incoherentes(
    incoherences,
    [
        "Date incorrecte",
        NOM_CONTROLE_SEUILS,
        "Annulations supérieures aux prévisions",
    ],
)
```

Une ligne est signalée dès qu'au moins un contrôle est positif.

## 6. Filtrer les observations, si nécessaire

Pour conserver uniquement les lignes qui ne présentent
aucune des incohérences sélectionnées :

```python
df_filtre = df.loc[~masque].copy()
```

Pour examiner au contraire les observations signalées :

```python
df_anomalies = df.loc[masque].copy()
```

**Attention :** une incohérence détectée ne signifie pas
nécessairement qu'une observation doit être supprimée.

Chaque analyse doit justifier ses critères d'exclusion.

## 7. Exemple complet

```python
from projet_railinsight.common_processing import (
    NOM_CONTROLE_SEUILS,
    charger_donnees,
    construire_incoherences,
    get_masque_lignes_incoherentes,
)

# Chargement
df = charger_donnees()

# Identification des incohérences
incoherences = construire_incoherences(df)

# Sélection d'un contrôle
masque = get_masque_lignes_incoherentes(
    incoherences,
    [NOM_CONTROLE_SEUILS],
)

# Nombre d'observations concernées
print("Observations incohérentes :", masque.sum())

# Conservation des observations non signalées
df_filtre = df.loc[~masque].copy()

print("Observations conservées :", len(df_filtre))
```

## 8. Pourquoi deux arguments pour le masque ?

La fonction possède la signature suivante :

```python
get_masque_lignes_incoherentes(
    df_incoherences,
    colonnes,
)
```

Le premier argument contient les indicateurs calculés.

Le second précise les contrôles à sélectionner.

Cette interface évite de dépendre d'un DataFrame global et permet
d'utiliser la même fonction avec différents jeux de données.

## 9. Tests

Pour vérifier le fonctionnement du module :

```bash
uv run pytest -q tests/test_common_processing.py
```

Les tests vérifient notamment le chargement, les contrôles
d'incohérence et la construction des masques.
