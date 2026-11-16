
"""Tests du chargement, de la validation et de l'agrégation des données TGV."""

import pandas as pd
import pytest

from projet_railinsight.data_processing import (
    calculer_taux_mensuel,
    charger_donnees_tgv,
    preparer_donnees_retards,
)


def test_preparer_donnees_retards():
    """Vérifie le calcul des taux et le traitement des cas invalides."""
    df = pd.DataFrame(
        {
            "Nombre de circulations prévues": [100, 20, 10, 5],
            "Nombre de trains annulés": [10, 20, 0, 0],
            "Nombre trains en retard > 15min": [18, 0, 12, 0],
        }
    )

    resultat = preparer_donnees_retards(df)

    # Cas valide : 18 retards parmi 90 trains réalisés
    assert resultat.loc[0, "Trains réalisés"] == 90
    assert resultat.loc[0, "taux_retard_15min"] == 20.0

    # Cas invalide : aucun train réalisé
    assert not resultat.loc[1, "taux_retard_valide"]
    assert pd.isna(resultat.loc[1, "taux_retard_15min"])

    # Cas invalide : plus de retards que de trains réalisés
    assert not resultat.loc[2, "taux_retard_valide"]
    assert pd.isna(resultat.loc[2, "taux_retard_15min"])

    # Cas valide : aucun retard
    assert resultat.loc[3, "taux_retard_15min"] == 0.0

    # La fonction conserve toutes les observations
    assert len(resultat) == len(df)

    # Le DataFrame original n'est pas modifié
    assert "Trains réalisés" not in df.columns


def test_calculer_taux_mensuel():
    """Vérifie l'agrégation pondérée des retards mensuels."""
    df = pd.DataFrame(
        {
            "Date": ["2026-01", "2026-01", "2026-02", "2026-02"],
            "Nombre de circulations prévues": [100, 200, 50, 10],
            "Nombre de trains annulés": [0, 0, 0, 10],
            "Nombre trains en retard > 15min": [10, 40, 5, 0],
        }
    )

    resultat = calculer_taux_mensuel(df)

    # Janvier : 50 trains en retard sur 300 réalisés
    taux_janvier = 100 * 50 / 300
    assert (
        abs(resultat.loc["2026-01-01", "taux_retard_15min"] - taux_janvier)
        < 1e-10
    )

    # Février : la ligne sans circulation réalisée est exclue
    assert resultat.loc["2026-02-01", "taux_retard_15min"] == 10.0

    # Deux mois distincts
    assert len(resultat) == 2


def test_calculer_taux_mensuel_avec_date_parsed():
    """Vérifie Date_parsed et l'exclusion des dates invalides."""
    df = pd.DataFrame(
        {
            "Date": ["2026-01", "date-invalide", "2026-01"],
            "Date_parsed": pd.to_datetime(
                ["2026-01", None, "2026-01"]
            ),
            "Nombre de circulations prévues": [100, 200, 50],
            "Nombre de trains annulés": [0, 0, 0],
            "Nombre trains en retard > 15min": [10, 40, 10],
        }
    )

    resultat = calculer_taux_mensuel(df)

    # Seules les deux observations avec une date valide sont retenues
    assert len(resultat) == 1

    # Janvier : 20 retards parmi 150 trains réalisés
    taux_attendu = 100 * 20 / 150
    assert (
        abs(resultat.loc["2026-01-01", "taux_retard_15min"] - taux_attendu)
        < 1e-10
    )

    # Le DataFrame original reste inchangé
    assert df.loc[1, "Date"] == "date-invalide"


def test_charger_donnees_tgv_csv_valide(tmp_path):
    """Vérifie le chargement du CSV et la conversion des dates."""
    chemin = tmp_path / "tgv.csv"

    chemin.write_text(
        "Date;Nombre de circulations prévues\n"
        "2026-01;100\n"
        "2026-02;120\n"
        "date-invalide;80\n",
        encoding="utf-8",
    )

    resultat = charger_donnees_tgv(chemin)

    assert len(resultat) == 3
    assert resultat["Date_parsed"].iloc[0] == pd.Timestamp("2026-01-01")
    assert resultat["Date_parsed"].iloc[1] == pd.Timestamp("2026-02-01")
    assert pd.isna(resultat["Date_parsed"].iloc[2])


def test_charger_donnees_tgv_sans_date(tmp_path):
    """Vérifie qu'un CSV sans colonne Date est rejeté."""
    chemin = tmp_path / "tgv_sans_date.csv"

    chemin.write_text(
        "Nombre de circulations prévues;Nombre de trains annulés\n"
        "100;5\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Colonne manquante : Date"):
        charger_donnees_tgv(chemin)


def test_preparer_donnees_retards_colonne_manquante():
    """Vérifie qu'une colonne obligatoire manquante est signalée."""
    donnees = pd.DataFrame(
        {
            "Nombre de circulations prévues": [100],
            "Nombre de trains annulés": [5],
        }
    )

    with pytest.raises(ValueError, match="Colonnes manquantes"):
        preparer_donnees_retards(donnees)
