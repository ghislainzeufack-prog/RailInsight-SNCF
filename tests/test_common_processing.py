import pandas as pd
import pytest

from projet_railinsight.common_processing import (
    NOM_CONTROLE_SEUILS,
    charger_donnees,
    construire_incoherences,
    controler_qualite_donnees,
    get_masque_lignes_incoherentes,
)


def creer_donnees_test():
    """Construit un jeu de données synthétique pour les contrôles qualité."""
    return pd.DataFrame(
        {
            "Date_parsed": pd.to_datetime(["2026-01", "2026-02"]),
            "Durée moyenne du trajet": [120, -15],
            "Nombre de circulations prévues": [100, 100],
            "Nombre de trains annulés": [10, 10],
            "Nombre de trains en retard au départ": [20, -5],
            "Retard moyen des trains en retard au départ": [12, -3],
            "Retard moyen de tous les trains au départ": [4, 2],
            "Nombre de trains en retard à l'arrivée": [15, 110],
            "Retard moyen des trains en retard à l'arrivée": [20, 18],
            "Retard moyen de tous les trains à l'arrivée": [5, -2],
            "Nombre trains en retard > 15min": [12, 10],
            "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)": [
                25,
                30,
            ],
            "Nombre trains en retard > 30min": [6, 15],
            "Nombre trains en retard > 60min": [2, 5],
            "Prct retard pour causes externes": [20, 110],
        }
    )


def test_controler_qualite_donnees():
    """Vérifie les effectifs et la préservation du DataFrame original."""
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

    assert "Trains réalisés" not in df.columns
    assert "effectifs_coherents" not in df.columns


def test_charger_donnees(tmp_path):
    """Vérifie le chargement CSV et la conversion des dates."""
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

    assert len(resultat) == 2
    assert resultat["Date"].tolist() == ["2026-01", "2026-02"]
    assert pd.api.types.is_datetime64_any_dtype(resultat["Date_parsed"])

    assert resultat["Date_parsed"].dt.strftime("%Y-%m").tolist() == [
        "2026-01",
        "2026-02",
    ]

    assert resultat["Date_parsed"].min() == pd.Timestamp("2026-01-01")
    assert resultat["Date_parsed"].max() == pd.Timestamp("2026-02-01")
    assert resultat["Nombre de circulations prévues"].tolist() == [100, 200]


def test_construire_incoherences_seuils():
    """Vérifie la cohérence N60 <= N30 <= N15."""
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

    resultat = construire_incoherences(donnees)

    assert not resultat.loc[0, NOM_CONTROLE_SEUILS]
    assert resultat.loc[1, NOM_CONTROLE_SEUILS]


def test_get_masque_lignes_incoherentes():
    """Vérifie la sélection configurable des incohérences."""
    incoherences = pd.DataFrame(
        {
            "Effectifs négatifs": [False, True, False],
            NOM_CONTROLE_SEUILS: [False, False, True],
        }
    )

    masque = get_masque_lignes_incoherentes(incoherences, ["Effectifs négatifs"])
    assert masque.tolist() == [False, True, False]

    masque = get_masque_lignes_incoherentes(
        incoherences,
        ["Effectifs négatifs", NOM_CONTROLE_SEUILS],
    )
    assert masque.tolist() == [False, True, True]

    masque = get_masque_lignes_incoherentes(incoherences, [])
    assert masque.tolist() == [False, False, False]

    with pytest.raises(ValueError, match="inconnus"):
        get_masque_lignes_incoherentes(incoherences, ["Contrôle inexistant"])


def test_construire_incoherences_duree_negative():
    """Vérifie la détection des durées moyennes négatives."""
    resultat = construire_incoherences(creer_donnees_test())

    assert not resultat.loc[0, "Durée moyenne du trajet négative"]
    assert resultat.loc[1, "Durée moyenne du trajet négative"]


def test_construire_incoherences_effectifs_negatifs():
    """Vérifie les contrôles individuels des valeurs négatives."""
    resultat = construire_incoherences(creer_donnees_test())

    nom_effectif = "Nombre de trains en retard au départ négatif"
    nom_retard = "Retard moyen au départ négatif"

    assert not resultat.loc[0, nom_effectif]
    assert resultat.loc[1, nom_effectif]

    assert not resultat.loc[0, nom_retard]
    assert resultat.loc[1, nom_retard]

    # L'indicateur global ne porte que sur les effectifs
    # prévus, annulés et retardés aux seuils 15, 30 et 60 min.
    assert not resultat.loc[0, "Effectifs négatifs"]
    assert not resultat.loc[1, "Effectifs négatifs"]


def test_construire_incoherences_retards_superieurs_previsions():
    """Vérifie qu'un nombre de retards ne dépasse pas les prévisions."""
    resultat = construire_incoherences(creer_donnees_test())

    colonne = "Nombre de trains en retard à l'arrivée > Nombre de circulations prévues"

    assert not resultat.loc[0, colonne]
    assert resultat.loc[1, colonne]


def test_construire_incoherences_pourcentages():
    """Vérifie qu'un pourcentage reste entre 0 et 100."""
    resultat = construire_incoherences(creer_donnees_test())

    colonne = "Prct retard pour causes externes incohérent"

    assert not resultat.loc[0, colonne]
    assert resultat.loc[1, colonne]


def test_construire_incoherences_selection_seuils():
    """Vérifie la sélection des lignes incohérentes sur les seuils."""
    donnees = creer_donnees_test()
    incoherences = construire_incoherences(donnees)

    assert NOM_CONTROLE_SEUILS in incoherences.columns

    masque = get_masque_lignes_incoherentes(incoherences, [NOM_CONTROLE_SEUILS])

    assert masque.equals(incoherences[NOM_CONTROLE_SEUILS])
