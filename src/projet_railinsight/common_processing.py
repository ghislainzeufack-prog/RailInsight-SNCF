"""Chargement et préparation commune des données SNCF."""

from pathlib import Path

import pandas as pd

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "regularite-mensuelle-tgv-aqst.csv"
)

NOM_CONTROLE_SEUILS = (
    "Incohérence des effectifs de trains en retard (seuils 15, 30 et 60 min)"
)


def charger_donnees(chemin: str | Path = DATA_PATH) -> pd.DataFrame:
    """Charge les données SNCF sans modifier le fichier original."""
    chemin = Path(chemin)

    if not chemin.is_file():
        raise FileNotFoundError(f"Fichier de données introuvable : {chemin}")

    df = pd.read_csv(chemin, sep=";")

    if "Date" not in df.columns:
        raise ValueError("La colonne 'Date' est absente du CSV.")

    df["Date_parsed"] = pd.to_datetime(df["Date"], format="%Y-%m", errors="coerce")

    return df


def controler_qualite_donnees(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute des indicateurs de qualité sans supprimer d'observations."""
    donnees = df.copy()

    prevus = donnees["Nombre de circulations prévues"]
    annules = donnees["Nombre de trains annulés"]

    donnees["Trains réalisés"] = prevus - annules

    donnees["effectifs_coherents"] = (
        (prevus >= 0) & (annules >= 0) & (annules <= prevus)
    )

    return donnees


def construire_incoherences(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les indicateurs d'incohérence sans supprimer de lignes."""
    donnees = df.copy()

    prevus = donnees["Nombre de circulations prévues"]
    annules = donnees["Nombre de trains annulés"]
    realises = prevus - annules

    retard_15 = donnees["Nombre trains en retard > 15min"]
    retard_30 = donnees["Nombre trains en retard > 30min"]
    retard_60 = donnees["Nombre trains en retard > 60min"]

    incoherences = pd.DataFrame(index=donnees.index)

    # 1. Validité des dates
    incoherences["Date incorrecte"] = donnees["Date_parsed"].isna()

    # 2. Contrôles individuels des valeurs négatives
    # Clé : nom de la colonne SNCF
    # Valeur : nom du contrôle qualité
    controles_negatifs = {
        "Durée moyenne du trajet": "Durée moyenne du trajet négative",
        "Nombre de circulations prévues": ("Nombre de circulations prévues négatif"),
        "Nombre de trains annulés": "Nombre de trains annulés négatif",
        "Nombre de trains en retard au départ": (
            "Nombre de trains en retard au départ négatif"
        ),
        "Retard moyen des trains en retard au départ": (
            "Retard moyen au départ négatif"
        ),
        "Retard moyen de tous les trains au départ": (
            "Retard moyen de tous les trains au départ négatif"
        ),
        "Nombre de trains en retard à l'arrivée": (
            "Nombre de trains en retard à l'arrivée négatif"
        ),
        "Retard moyen des trains en retard à l'arrivée": (
            "Retard moyen des trains en retard à l'arrivée négatif"
        ),
        "Retard moyen de tous les trains à l'arrivée": (
            "Retard moyen de tous les trains à l'arrivée négatif"
        ),
        "Nombre trains en retard > 15min": ("Nombre trains en retard > 15min négatif"),
        "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)": (
            "Retard moyen trains en retard > 15 "
            "(si liaison concurrencée par vol) négatif"
        ),
        "Nombre trains en retard > 30min": ("Nombre trains en retard > 30min négatif"),
        "Nombre trains en retard > 60min": ("Nombre trains en retard > 60min négatif"),
    }

    for colonne, nom_controle in controles_negatifs.items():
        if colonne in donnees.columns:
            incoherences[nom_controle] = donnees[colonne] < 0

    # 3. Contrôle global des effectifs
    incoherences["Effectifs négatifs"] = (
        (prevus < 0)
        | (annules < 0)
        | (retard_15 < 0)
        | (retard_30 < 0)
        | (retard_60 < 0)
    )

    # 4. Cohérence des annulations
    incoherences["Annulations supérieures aux prévisions"] = annules > prevus

    # 5. Cohérence par rapport aux trains réellement effectués
    incoherences["Retards supérieurs aux trains réalisés"] = (
        (retard_15 > realises) | (retard_30 > realises) | (retard_60 > realises)
    )

    # 6. Retards supérieurs aux circulations prévues
    colonnes_retards = [
        "Nombre de trains en retard au départ",
        "Nombre de trains en retard à l'arrivée",
        "Nombre trains en retard > 15min",
        "Nombre trains en retard > 30min",
        "Nombre trains en retard > 60min",
    ]

    for colonne in colonnes_retards:
        if colonne in donnees.columns:
            nom_controle = f"{colonne} > Nombre de circulations prévues"
            incoherences[nom_controle] = donnees[colonne] > prevus

    # 7. Cohérence des seuils : N60 <= N30 <= N15
    incoherences[NOM_CONTROLE_SEUILS] = (retard_60 > retard_30) | (
        retard_30 > retard_15
    )

    # 8. Pourcentages compris entre 0 et 100
    colonnes_pourcentages = [
        colonne for colonne in donnees.columns if colonne.startswith("Prct retard")
    ]

    for colonne in colonnes_pourcentages:
        incoherences[f"{colonne} incohérent"] = (donnees[colonne] < 0) | (
            donnees[colonne] > 100
        )

    return incoherences


def get_masque_lignes_incoherentes(
    df_incoherences: pd.DataFrame,
    colonnes: list[str],
) -> pd.Series:
    """Retourne le masque des lignes présentant les incohérences choisies.

    True : au moins une incohérence sélectionnée.
    False : aucune incohérence sélectionnée.
    """
    colonnes_absentes = [
        colonne for colonne in colonnes if colonne not in df_incoherences.columns
    ]

    if colonnes_absentes:
        raise ValueError(f"Contrôles d'incohérence inconnus : {colonnes_absentes}")

    if not colonnes:
        return pd.Series(False, index=df_incoherences.index, dtype=bool)

    return df_incoherences[colonnes].any(axis=1)
