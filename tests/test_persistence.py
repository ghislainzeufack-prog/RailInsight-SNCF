import numpy as np
import pandas as pd
import pytest

from projet_railinsight.persistence import (
    estimer_ar1,
    evaluer_previsions,
    prevoir_naif,
)


def test_prevoir_naif():
    serie = pd.Series([10.0, 12.0, 15.0])

    resultat = prevoir_naif(serie)

    attendu = pd.Series([np.nan, 10.0, 12.0])
    pd.testing.assert_series_equal(resultat, attendu)


def test_prevoir_naif_serie_vide():
    with pytest.raises(ValueError):
        prevoir_naif(pd.Series(dtype=float))


def test_estimer_ar1_serie_vide():
    with pytest.raises(ValueError):
        estimer_ar1(pd.Series(dtype=float))


def test_estimer_ar1_valeurs_manquantes():
    serie = pd.Series([10.0, np.nan, 12.0])

    with pytest.raises(ValueError):
        estimer_ar1(serie)


def test_evaluer_previsions():
    observations = pd.Series([10.0, 12.0, 14.0])
    predictions = pd.Series([11.0, 11.0, 13.0])

    resultat = evaluer_previsions(observations, predictions)

    assert resultat["MAE"] == pytest.approx(1.0)
    assert resultat["RMSE"] == pytest.approx(1.0)


def test_evaluer_previsions_longueurs_differentes():
    observations = pd.Series([10.0, 12.0])
    predictions = pd.Series([11.0])

    with pytest.raises(ValueError):
        evaluer_previsions(observations, predictions)


def test_evaluer_previsions_valeurs_manquantes():
    observations = pd.Series([10.0, np.nan])
    predictions = pd.Series([11.0, 12.0])

    with pytest.raises(ValueError):
        evaluer_previsions(observations, predictions)


def test_estimer_ar1_serie_valide():
    """Vérifie qu'un modèle AR(1) peut être estimé."""

    serie = pd.Series([10.0, 12.0, 11.0, 14.0, 13.0, 15.0, 14.0, 16.0])

    resultat = estimer_ar1(serie)

    assert len(resultat.params) == 2
    assert np.isfinite(resultat.params).all()


def test_evaluer_previsions_series_vides():
    """Vérifie le rejet de séries vides."""

    observations = pd.Series(dtype=float)
    predictions = pd.Series(dtype=float)

    with pytest.raises(ValueError, match="Aucune observation"):
        evaluer_previsions(observations, predictions)
