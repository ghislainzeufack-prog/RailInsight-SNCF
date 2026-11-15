
import pandas as pd

from projet_railinsight.data_processing import preparer_donnees_retards


def test_preparer_donnees_retards():
    """Vérifie le calcul des taux et le traitement des cas invalides."""
    df = pd.DataFrame({
        "Nombre de circulations prévues": [100, 20, 10, 5],
        "Nombre de trains annulés": [10, 20, 0, 0],
        "Nombre trains en retard > 15min": [18, 0, 12, 0],
    })

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
    from projet_railinsight.data_processing import calculer_taux_mensuel

    df = pd.DataFrame({
        "Date": ["2026-01", "2026-01", "2026-02", "2026-02"],
        "Nombre de circulations prévues": [100, 200, 50, 10],
        "Nombre de trains annulés": [0, 0, 0, 10],
        "Nombre trains en retard > 15min": [10, 40, 5, 0],
    })

    resultat = calculer_taux_mensuel(df)

    # Janvier : 50 trains en retard sur 300 réalisés
    taux_janvier = 100 * 50 / 300
    assert abs(
        resultat.loc["2026-01-01", "taux_retard_15min"] - taux_janvier
    ) < 1e-10

    # Février : la ligne sans circulation réalisée est exclue
    assert resultat.loc["2026-02-01", "taux_retard_15min"] == 10.0

    # Deux mois distincts
    assert len(resultat) == 2
