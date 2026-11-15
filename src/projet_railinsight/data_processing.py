
"""Préparation des données de ponctualité TGV."""

import numpy as np
import pandas as pd

from projet_railinsight.common_processing import controler_qualite_donnees


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

    resultat = controler_qualite_donnees(df)

    resultat["taux_retard_valide"] = (
        (resultat["Trains réalisés"] > 0)
        & (resultat["Nombre trains en retard > 15min"] >= 0)
        & (
            resultat["Nombre trains en retard > 15min"]
            <= resultat["Trains réalisés"]
        )
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

    donnees["Date"] = pd.to_datetime(
        donnees["Date"], format="%Y-%m"
    )

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
