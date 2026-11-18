from pathlib import Path

import pandas as pd


def charger_et_preparer_donnees(chemin: str | Path) -> pd.DataFrame:
    """Charge et nettoie les données SNCF pour l'analyse de fiabilité."""

    # Chargement du fichier CSV
    donnees = pd.read_csv(chemin, sep=";")

    # Vérification des colonnes nécessaires
    colonnes = [
        "Date",
        "Nombre de circulations prévues",
        "Nombre de trains annulés",
        "Nombre de trains en retard à l'arrivée",
        "Nombre trains en retard > 15min",
        "Nombre trains en retard > 30min",
        "Nombre trains en retard > 60min",
    ]

    manquantes = [col for col in colonnes if col not in donnees.columns]

    if manquantes:
        raise ValueError(f"Colonnes manquantes : {manquantes}")

    # Conversion des dates
    donnees["Date"] = pd.to_datetime(
        donnees["Date"],
        format="%Y-%m",
        errors="coerce",
    )

    # Calcul des trains circulés
    prevus = donnees["Nombre de circulations prévues"]
    annules = donnees["Nombre de trains annulés"]
    retards = donnees["Nombre de trains en retard à l'arrivée"]

    donnees["Trains circulés"] = prevus - annules

    # Identification des observations invalides
    anomalies = (
        donnees["Date"].isna()
        | prevus.isna()
        | annules.isna()
        | retards.isna()
        | (prevus < 0)
        | (annules < 0)
        | (donnees["Trains circulés"] <= 0)
        | (retards < 0)
        | (retards > donnees["Trains circulés"])
    )

    # Exclusion des observations invalides
    donnees = donnees.loc[~anomalies].copy()

    # Vérification des retards supérieurs à 30 minutes
    retard_15 = donnees["Nombre trains en retard > 15min"]
    retard_30 = donnees["Nombre trains en retard > 30min"]
    retard_60 = donnees["Nombre trains en retard > 60min"]

    incoherences_30 = (
        (retard_30 < 0) | (retard_30 > retard_15) | (retard_30 < retard_60)
    )

    # Remplacement des valeurs incohérentes
    donnees.loc[
        incoherences_30,
        "Nombre trains en retard > 30min",
    ] = float("nan")

    return donnees
