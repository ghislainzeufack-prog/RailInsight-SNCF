import pandas as pd

from projet_railinsight.common_processing import (
    controler_qualite_donnees,
)


def test_controler_qualite_donnees():
    df = pd.DataFrame(
        {
            "Nombre de circulations prévues": [100, 0, 50],
            "Nombre de trains annulés": [10, 8, 50],
        }
    )

    resultat = controler_qualite_donnees(df)

    assert len(resultat) == 3

    assert resultat["Trains réalisés"].tolist() == [90, -8, 0]

    assert resultat["effectifs_coherents"].tolist() == [True, False, True]

    # La fonction ne doit pas modifier le DataFrame original.
    assert "Trains réalisés" not in df.columns
    assert "effectifs_coherents" not in df.columns


def test_charger_donnees(tmp_path):
    """Vérifie le chargement et la conversion des dates."""

    from projet_railinsight.common_processing import charger_donnees

    chemin = tmp_path / "donnees_test.csv"

    donnees = pd.DataFrame(
        {
            "Date": ["2026-01", "2026-02"],
            "Nombre de circulations prévues": [100, 200],
            "Nombre de trains annulés": [10, 20],
        }
    )

    donnees.to_csv(chemin, sep=";", index=False)

    resultat = charger_donnees(chemin)

    # Vérifier le nombre de lignes
    assert len(resultat) == 2

    # Vérifier que la colonne Date originale est conservée
    assert resultat["Date"].tolist() == ["2026-01", "2026-02"]

    # Vérifier que Date_parsed est de type datetime
    assert pd.api.types.is_datetime64_any_dtype(resultat["Date_parsed"])

    # Vérifier la conversion des dates
    assert resultat["Date_parsed"].dt.strftime("%Y-%m").tolist() == [
        "2026-01",
        "2026-02",
    ]

    # Vérifier les dates minimale et maximale
    assert resultat["Date_parsed"].min() == pd.Timestamp("2026-01-01")
    assert resultat["Date_parsed"].max() == pd.Timestamp("2026-02-01")

    # Vérifier que les autres colonnes sont conservées
    assert resultat["Nombre de circulations prévues"].tolist() == [
        100,
        200,
    ]


def test_construire_incoherences_seuils():
    """Vérifie la détection des incohérences entre seuils de retard."""
    from projet_railinsight.common_processing import construire_incoherences

    donnees = pd.DataFrame(
        {
            "Date_parsed": pd.to_datetime(["2025-01", "2025-02"]),
            "Nombre de circulations prévues": [100, 100],
            "Nombre de trains annulés": [10, 10],
            "Nombre trains en retard > 15min": [20, 10],
            "Nombre trains en retard > 30min": [10, 15],
            "Nombre trains en retard > 60min": [5, 5],
        }
    )

    incoherences = construire_incoherences(donnees)

    assert not incoherences.loc[0, "Incohérence des seuils de retard"]
    assert incoherences.loc[1, "Incohérence des seuils de retard"]


def test_get_masque_lignes_incoherentes():
    """Vérifie la sélection configurable des incohérences."""
    import pytest

    from projet_railinsight.common_processing import (
        get_masque_lignes_incoherentes,
    )

    incoherences = pd.DataFrame(
        {
            "Effectifs négatifs": [False, True, False],
            "Incohérence des seuils de retard": [False, False, True],
        }
    )

    # Sélection d'un seul contrôle
    masque = get_masque_lignes_incoherentes(
        incoherences,
        ["Effectifs négatifs"],
    )
    assert masque.tolist() == [False, True, False]

    # Sélection de plusieurs contrôles
    masque = get_masque_lignes_incoherentes(
        incoherences,
        [
            "Effectifs négatifs",
            "Incohérence des seuils de retard",
        ],
    )
    assert masque.tolist() == [False, True, True]

    # Aucun contrôle sélectionné
    masque = get_masque_lignes_incoherentes(incoherences, [])
    assert masque.tolist() == [False, False, False]

    # Contrôle inexistant
    with pytest.raises(ValueError, match="inconnus"):
        get_masque_lignes_incoherentes(
            incoherences,
            ["Contrôle inexistant"],
        )
