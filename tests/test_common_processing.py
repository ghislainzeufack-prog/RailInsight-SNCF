
import pandas as pd

from projet_railinsight.common_processing import (
    controler_qualite_donnees,
)


def test_controler_qualite_donnees():
    df = pd.DataFrame({
        "Nombre de circulations prévues": [100, 0, 50],
        "Nombre de trains annulés": [10, 8, 50],
    })

    resultat = controler_qualite_donnees(df)

    assert len(resultat) == 3

    assert resultat["Trains réalisés"].tolist() == [
        90, -8, 0
    ]

    assert resultat["effectifs_coherents"].tolist() == [
        True, False, True
    ]

    # La fonction ne doit pas modifier le DataFrame original.
    assert "Trains réalisés" not in df.columns
    assert "effectifs_coherents" not in df.columns


def test_charger_donnees(tmp_path):
    """Vérifie le chargement et la conversion des dates."""

    from projet_railinsight.common_processing import charger_donnees

    chemin = tmp_path / "donnees_test.csv"

    donnees = pd.DataFrame({
        "Date": ["2026-01", "2026-02"],
        "Nombre de circulations prévues": [100, 200],
        "Nombre de trains annulés": [10, 20],
    })

    donnees.to_csv(chemin, sep=";", index=False)

    resultat = charger_donnees(chemin)

    assert len(resultat) == 2
    assert pd.api.types.is_datetime64_any_dtype(resultat["Date"])
    assert resultat["Date"].min() == pd.Timestamp("2026-01-01")
    assert resultat["Date"].max() == pd.Timestamp("2026-02-01")
    assert resultat["Nombre de circulations prévues"].tolist() == [
        100, 200
    ]

