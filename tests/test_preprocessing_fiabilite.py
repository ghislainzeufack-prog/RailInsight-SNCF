
import pandas as pd
import pytest

from projet_railinsight.preprocessing_fiabilite import (
    charger_et_preparer_donnees,
)


@pytest.fixture
def fichier_test(tmp_path):
    """Crée un fichier SNCF simplifié pour les tests."""

    # Données de test
    donnees = pd.DataFrame({
        "Date": ["2025-01", "2025-02", "2025-03"],
        "Nombre de circulations prévues": [100, 0, 100],
        "Nombre de trains annulés": [10, 0, 5],
        "Nombre de trains en retard à l'arrivée": [20, 0, 15],
        "Nombre trains en retard > 15min": [15, 0, 10],
        "Nombre trains en retard > 30min": [8, 0, -3],
        "Nombre trains en retard > 60min": [2, 0, 1],
    })

    chemin = tmp_path / "sncf_test.csv"
    donnees.to_csv(chemin, sep=";", index=False)

    return chemin


def test_exclusion_observations_invalides(fichier_test):
    # Vérification du filtrage des observations
    resultat = charger_et_preparer_donnees(fichier_test)

    assert len(resultat) == 2
    assert (resultat["Trains circulés"] > 0).all()


def test_traitement_retards_30_minutes(fichier_test):
    # Vérification des valeurs incohérentes
    resultat = charger_et_preparer_donnees(fichier_test)

    assert resultat["Nombre trains en retard > 30min"].isna().sum() == 1


def test_conversion_dates(fichier_test):
    # Vérification du format des dates
    resultat = charger_et_preparer_donnees(fichier_test)

    assert pd.api.types.is_datetime64_any_dtype(resultat["Date"])


def test_fichier_introuvable(tmp_path):
    # Vérification de l'absence du fichier
    with pytest.raises(FileNotFoundError):
        charger_et_preparer_donnees(tmp_path / "absent.csv")
