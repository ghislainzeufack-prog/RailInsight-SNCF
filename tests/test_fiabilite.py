import pandas as pd
import pytest

from projet_railinsight.fiabilite import (
    AnalyseFiabilite,
    calculer_taux_annulation,
    calculer_taux_retard,
)


def test_taux_retard_normal():
    # Vérification du calcul classique
    resultat = calculer_taux_retard(200, 10, 38)
    assert resultat == pytest.approx(20.0)


def test_taux_retard_sans_retard():
    # Vérification du taux nul
    resultat = calculer_taux_retard(100, 5, 0)
    assert resultat == pytest.approx(0.0)


def test_taux_retard_sans_circulation():
    # Vérification du dénominateur nul
    with pytest.raises(ValueError):
        calculer_taux_retard(10, 10, 0)


def test_taux_retard_incoherent():
    # Vérification des effectifs incohérents
    with pytest.raises(ValueError):
        calculer_taux_retard(100, 5, 110)


def test_taux_retard_negatif():
    # Vérification des effectifs négatifs
    with pytest.raises(ValueError):
        calculer_taux_retard(100, 5, -3)


def test_taux_annulation_normal():
    # Vérification du calcul classique
    resultat = calculer_taux_annulation(200, 10)
    assert resultat == pytest.approx(5.0)


def test_taux_annulation_sans_annulation():
    # Vérification du taux nul
    resultat = calculer_taux_annulation(100, 0)
    assert resultat == pytest.approx(0.0)


def test_taux_annulation_sans_train_prevu():
    # Vérification du dénominateur nul
    with pytest.raises(ValueError):
        calculer_taux_annulation(0, 0)


def test_taux_annulation_incoherent():
    # Vérification des annulations supérieures aux prévisions
    with pytest.raises(ValueError):
        calculer_taux_annulation(100, 110)


def test_taux_annulation_negatif():
    # Vérification des effectifs négatifs
    with pytest.raises(ValueError):
        calculer_taux_annulation(100, -5)


def test_initialisation_analyse():
    # Création d'un DataFrame de test
    donnees = pd.DataFrame(
        {
            "Gare de départ": ["Paris"],
            "Gare d'arrivée": ["Lyon"],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    assert isinstance(analyse.donnees, pd.DataFrame)
    assert len(analyse.donnees) == 1


def test_initialisation_type_invalide():
    # Vérification du type des données
    with pytest.raises(TypeError):
        AnalyseFiabilite([1, 2, 3])


def test_initialisation_copie_independante():
    # Vérification de l'indépendance des données
    donnees = pd.DataFrame({"valeur": [10]})
    analyse = AnalyseFiabilite(donnees)

    analyse.donnees.loc[0, "valeur"] = 20

    assert donnees.loc[0, "valeur"] == 10


def test_calculer_indicateurs():
    # Création d'un DataFrame de test
    donnees = pd.DataFrame(
        {
            "Nombre de circulations prévues": [200, 100],
            "Nombre de trains annulés": [10, 0],
            "Nombre de trains en retard à l'arrivée": [38, 15],
        }
    )

    analyse = AnalyseFiabilite(donnees)
    resultat = analyse.calculer_indicateurs()

    assert resultat["Taux de retard (%)"].tolist() == pytest.approx([20.0, 15.0])
    assert resultat["Taux d'annulation (%)"].tolist() == pytest.approx([5.0, 0.0])
    assert resultat["Trains circulés"].tolist() == [190, 100]


def test_calculer_indicateurs_colonne_manquante():
    # Vérification des colonnes obligatoires
    donnees = pd.DataFrame(
        {
            "Nombre de circulations prévues": [100],
            "Nombre de trains annulés": [5],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    with pytest.raises(ValueError, match="Colonnes manquantes"):
        analyse.calculer_indicateurs()


def test_calculer_indicateurs_donnees_invalides():
    # Vérification des effectifs incohérents
    donnees = pd.DataFrame(
        {
            "Nombre de circulations prévues": [100],
            "Nombre de trains annulés": [10],
            "Nombre de trains en retard à l'arrivée": [95],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    with pytest.raises(ValueError, match="Effectifs invalides"):
        analyse.calculer_indicateurs()


def test_classement_liaisons():
    # Création de données sur deux mois
    donnees = pd.DataFrame(
        {
            "Date": ["2025-01", "2025-02", "2025-01"],
            "Service": ["National", "National", "National"],
            "Gare de départ": ["Paris", "Paris", "Lyon"],
            "Gare d'arrivée": ["Lyon", "Lyon", "Paris"],
            "Nombre de circulations prévues": [100, 300, 200],
            "Nombre de trains annulés": [0, 0, 0],
            "Nombre de trains en retard à l'arrivée": [30, 30, 40],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    classement = analyse.classer_liaisons(
        annee=2025,
        min_circulations=0,
        min_mois=1,
    )

    # Vérification de l'agrégation et du classement
    assert len(classement) == 2
    assert classement.iloc[0]["Gare de départ"] == "Lyon"
    assert classement.iloc[0]["taux_retard"] == pytest.approx(20.0)
    assert classement.iloc[1]["taux_retard"] == pytest.approx(15.0)
    assert classement.iloc[1]["nombre_mois"] == 2


def test_classement_filtre_annee():
    # Vérification de la sélection temporelle
    donnees = pd.DataFrame(
        {
            "Date": ["2024-01", "2025-01"],
            "Service": ["National", "National"],
            "Gare de départ": ["Paris", "Paris"],
            "Gare d'arrivée": ["Lyon", "Lyon"],
            "Nombre de circulations prévues": [100, 100],
            "Nombre de trains annulés": [0, 0],
            "Nombre de trains en retard à l'arrivée": [50, 10],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    classement = analyse.classer_liaisons(
        annee=2025,
        min_circulations=0,
        min_mois=1,
    )

    assert len(classement) == 1
    assert classement.iloc[0]["taux_retard"] == pytest.approx(10.0)


def test_classement_seuil_circulations():
    # Vérification du filtre de volume
    donnees = pd.DataFrame(
        {
            "Date": ["2025-01"],
            "Service": ["National"],
            "Gare de départ": ["Paris"],
            "Gare d'arrivée": ["Lyon"],
            "Nombre de circulations prévues": [100],
            "Nombre de trains annulés": [0],
            "Nombre de trains en retard à l'arrivée": [20],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    classement = analyse.classer_liaisons(
        annee=2025,
        min_circulations=500,
        min_mois=1,
    )

    assert classement.empty


def test_evolution_temporelle():
    # Création des observations mensuelles
    donnees = pd.DataFrame(
        {
            "Date": ["2025-02", "2025-01", "2025-01"],
            "Service": ["National", "National", "National"],
            "Gare de départ": ["Paris", "Paris", "Paris"],
            "Gare d'arrivée": ["Lyon", "Lyon", "Lyon"],
            "Nombre de circulations prévues": [300, 100, 100],
            "Nombre de trains annulés": [0, 0, 0],
            "Nombre de trains en retard à l'arrivée": [30, 20, 40],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    resultat = analyse.evolution_temporelle(
        gare_depart="Paris",
        gare_arrivee="Lyon",
        service="National",
        annee=2025,
    )

    assert len(resultat) == 2
    assert resultat["taux_retard"].tolist() == pytest.approx([30.0, 10.0])
    assert resultat["trains_circules"].tolist() == [200, 300]


def test_evolution_temporelle_liaison_absente():
    # Vérification d'une liaison inexistante
    donnees = pd.DataFrame(
        {
            "Date": ["2025-01"],
            "Service": ["National"],
            "Gare de départ": ["Paris"],
            "Gare d'arrivée": ["Lyon"],
            "Nombre de circulations prévues": [100],
            "Nombre de trains annulés": [0],
            "Nombre de trains en retard à l'arrivée": [20],
        }
    )

    analyse = AnalyseFiabilite(donnees)

    resultat = analyse.evolution_temporelle(
        gare_depart="Lille",
        gare_arrivee="Lyon",
        service="National",
    )

    assert resultat.empty
