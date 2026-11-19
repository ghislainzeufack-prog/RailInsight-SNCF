"""Préparation des données de ponctualité TGV."""

from pathlib import Path

import numpy as np
import pandas as pd


def charger_donnees_tgv(chemin: str | Path) -> pd.DataFrame:
    """Charge les données SNCF et prépare la colonne Date."""
    donnees = pd.read_csv(chemin, sep=";")

    if "Date" not in donnees.columns:
        raise ValueError("Colonne manquante : Date")

    donnees["Date_parsed"] = pd.to_datetime(
        donnees["Date"],
        format="%Y-%m",
        errors="coerce",
    )

    return donnees


def preparer_donnees_retards(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule et valide le taux de retard supérieur à 15 minutes.

    Les observations invalides sont conservées, avec un taux NaN.
    Le DataFrame fourni en entrée n'est pas modifié.
    """
    colonnes = [
        "Nombre de circulations prévues",
        "Nombre de trains annulés",
        "Nombre trains en retard > 15min",
    ]

    manquantes = set(colonnes) - set(df.columns)
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {sorted(manquantes)}")

    resultat = df.copy()

    prevus = resultat["Nombre de circulations prévues"]
    annules = resultat["Nombre de trains annulés"]

    resultat["Trains réalisés"] = prevus - annules

    resultat["effectifs_coherents"] = (
        (prevus >= 0) & (annules >= 0) & (annules <= prevus)
    )

    resultat["taux_retard_valide"] = (
        resultat["effectifs_coherents"]
        & (resultat["Trains réalisés"] > 0)
        & (resultat["Nombre trains en retard > 15min"] >= 0)
        & (resultat["Nombre trains en retard > 15min"] <= resultat["Trains réalisés"])
    )

    resultat["taux_retard_15min"] = np.where(
        resultat["taux_retard_valide"],
        100
        * resultat["Nombre trains en retard > 15min"]
        / resultat["Trains réalisés"].replace(0, np.nan),
        np.nan,
    )

    return resultat


def calculer_taux_mensuel(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le taux mensuel pondéré des retards > 15 minutes.

    Les observations invalides sont exclues de l'agrégation.
    """
    donnees = preparer_donnees_retards(df)

    donnees = donnees.loc[donnees["taux_retard_valide"]].copy()

    if "Date_parsed" in donnees.columns:
        donnees["Date"] = donnees["Date_parsed"]
    else:
        donnees["Date"] = pd.to_datetime(
            donnees["Date"],
            format="%Y-%m",
            errors="coerce",
        )

    donnees = donnees.dropna(subset=["Date"])

    mensuel = (
        donnees.groupby("Date")
        .agg(
            trains_retardes=("Nombre trains en retard > 15min", "sum"),
            trains_realises=("Trains réalisés", "sum"),
        )
        .sort_index()
    )

    mensuel["taux_retard_15min"] = (
        100 * mensuel["trains_retardes"] / mensuel["trains_realises"]
    )

    return mensuel
