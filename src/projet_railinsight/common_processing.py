
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

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%Y-%m",
        errors="raise",
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

