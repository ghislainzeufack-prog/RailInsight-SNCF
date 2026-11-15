
"""Chargement et préparation commune des données SNCF."""

from pathlib import Path

import pandas as pd

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "regularite-mensuelle-tgv-aqst.csv"
)


def charger_donnees(chemin: str | Path = DATA_PATH) -> pd.DataFrame:
    """Charge les données SNCF sans modifier le fichier original.

    Args:
        chemin: Chemin du fichier CSV à charger.

    Returns:
        DataFrame contenant les observations SNCF.

    Raises:
        FileNotFoundError: Si le fichier est introuvable.
        ValueError: Si le fichier ne contient pas la colonne Date.
    """
    chemin = Path(chemin)

    if not chemin.is_file():
        raise FileNotFoundError(
            f"Fichier de données introuvable : {chemin}"
        )

    df = pd.read_csv(chemin, sep=";")

    if "Date" not in df.columns:
        raise ValueError("La colonne 'Date' est absente du CSV.")

    df["Date_parsed"] = pd.to_datetime(
        df["Date"],
        format="%Y-%m",
        errors="coerce",
    )

    return df


def controler_qualite_donnees(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute des indicateurs de qualité sans supprimer d'observations.

    Le DataFrame original n'est pas modifié.
    """
    donnees = df.copy()

    prevus = donnees["Nombre de circulations prévues"]
    annules = donnees["Nombre de trains annulés"]

    donnees["Trains réalisés"] = prevus - annules

    donnees["effectifs_coherents"] = (
        (prevus >= 0)
        & (annules >= 0)
        & (annules <= prevus)
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

    incoherences["Date incorrecte"] = donnees["Date_parsed"].isna()

    incoherences["Effectifs négatifs"] = (
        (prevus < 0)
        | (annules < 0)
        | (retard_15 < 0)
        | (retard_30 < 0)
        | (retard_60 < 0)
    )

    incoherences["Annulations supérieures aux prévisions"] = (
        annules > prevus
    )

    incoherences["Retards supérieurs aux trains réalisés"] = (
        (retard_15 > realises)
        | (retard_30 > realises)
        | (retard_60 > realises)
    )

    incoherences["Incohérence des seuils de retard"] = (
        (retard_60 > retard_30)
        | (retard_30 > retard_15)
    )

    
    # Vérifier les pourcentages associés aux causes de retard
    colonnes_pourcentages = [
        colonne
        for colonne in donnees.columns
        if colonne.startswith("Prct retard")
    ]

    for colonne in colonnes_pourcentages:
        incoherences[f"{colonne} incohérent"] = (
            (donnees[colonne] < 0)
            | (donnees[colonne] > 100)
        )

    
    return incoherences

 
def get_masque_lignes_incoherentes(
    df_incoherences: pd.DataFrame,
    colonnes: list[str],
) -> pd.Series:
    """Retourne un masque identifiant les lignes incohérentes sélectionnées.

    True : la ligne présente au moins une incohérence sélectionnée.
    False : aucune incohérence sélectionnée.
    """
    colonnes_absentes = [
        colonne
        for colonne in colonnes
        if colonne not in df_incoherences.columns
    ]

    if colonnes_absentes:
        raise ValueError(
            f"Contrôles d'incohérence inconnus : {colonnes_absentes}"
        )

    if not colonnes:
        return pd.Series(False, index=df_incoherences.index, dtype=bool)

    return df_incoherences[colonnes].any(axis=1)


