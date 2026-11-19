"""Modélisation de la persistance des retards TGV."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.ar_model import AutoReg


def estimer_ar1(serie: pd.Series):
    """Estime un modèle autorégressif d'ordre 1."""

    if serie.empty:
        raise ValueError("La série temporelle est vide.")

    if serie.isna().any():
        raise ValueError("La série contient des valeurs manquantes.")

    modele = AutoReg(
        serie,
        lags=1,
        trend="c",
    )

    return modele.fit()


def prevoir_naif(serie: pd.Series) -> pd.Series:
    """Prévoit chaque mois à partir du taux du mois précédent."""

    if serie.empty:
        raise ValueError("La série temporelle est vide.")

    return serie.shift(1)


def evaluer_previsions(
    observations: pd.Series,
    predictions: pd.Series,
) -> dict[str, float]:
    """Calcule les erreurs MAE et RMSE des prévisions."""

    if len(observations) != len(predictions):
        raise ValueError(
            "Les observations et les prévisions doivent avoir la même longueur."
        )

    if observations.empty:
        raise ValueError("Aucune observation à évaluer.")

    if observations.isna().any() or predictions.isna().any():
        raise ValueError("Les séries contiennent des valeurs manquantes.")

    return {
        "MAE": float(mean_absolute_error(observations, predictions)),
        "RMSE": float(np.sqrt(mean_squared_error(observations, predictions))),
    }
