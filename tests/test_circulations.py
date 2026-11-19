"""Tests unitaires complets pour le module projet_railinsight.circulations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from projet_railinsight.circulations import (
    AnalyseCirculations,
    CompteurObservations,
    ErreurValidationCirculations,
)


@pytest.fixture
def df_exemple_sncf() -> pd.DataFrame:
    """Fixture reproduisant le cas de test officiel du TP (2 mois, 1 liaison + autres cas)."""
    return pd.DataFrame(
        {
            "date": ["2024-01", "2024-02", "2024-01", "2024-02", "2024-03"],
            "gare_depart": [
                "PARIS LYON",
                "PARIS LYON",
                "PARIS EST",
                "PARIS MONTPARNASSE",
                "LILLE",
            ],
            "gare_arrivee": [
                "LYON PART DIEU",
                "LYON PART DIEU",
                "STRASBOURG",
                "BORDEAUX",
                "MARSEILLE",
            ],
            "nb_train_prevu": [100, 20, 200, 50, 300],
            "nb_annulation": [10, 0, 5, 5, 30],
            "nb_train_retard_arrivee": [9, 2, 19, 4, 27],
            "duree_moyenne": [120.0, 120.0, 110.0, 130.0, 280.0],
        }
    )


def test_compteur_observations_independance_et_erreurs() -> None:
    """Verifie le mini-TP POO : independance des instances et refus des negatifs."""
    c1 = CompteurObservations(10)
    c2 = CompteurObservations(0)
    c1.augmenter(5)
    assert c1.total == 15
    assert c2.total == 0

    with pytest.raises(ValueError, match="negatif"):
        CompteurObservations(-1)

    with pytest.raises(ValueError, match="negative"):
        c1.augmenter(-3)


def test_non_mutation_dataframe_source(df_exemple_sncf: pd.DataFrame) -> None:
    """Verifie que le DataFrame passe au constructeur n'est jamais modifie en place."""
    colonnes_avant = list(df_exemple_sncf.columns)
    copie_temoin = df_exemple_sncf.copy(deep=True)

    analyse = AnalyseCirculations(df_exemple_sncf)
    _ = analyse.donnees
    _ = analyse.agreger_par_liaison()

    assert list(df_exemple_sncf.columns) == colonnes_avant
    pd.testing.assert_frame_equal(df_exemple_sncf, copie_temoin)


def test_agregation_ponderee_et_non_moyenne_simple(
    df_exemple_sncf: pd.DataFrame,
) -> None:
    """Verifie la regle d'or du TP : 10/120 (8.333%) et non la moyenne simple (5%)."""
    analyse = AnalyseCirculations(df_exemple_sncf)
    agg = analyse.agreger_par_liaison()
    ligne_lyon = agg[agg["liaison"] == "PARIS LYON -> LYON PART DIEU"].iloc[0]

    taux_attendu = (10.0 / 120.0) * 100.0
    assert np.isclose(ligne_lyon["taux_annulation"], taux_attendu)
    assert not np.isclose(ligne_lyon["taux_annulation"], 5.0)
    assert np.isclose(ligne_lyon["taux_retard_arrivee"], 10.0)


def test_lignes_invalides_et_denominateur_nul() -> None:
    """Verifie le rejet des lignes ou nb_train_prevu <= 0 ou nb_annulation > nb_train_prevu."""
    df_anomalies = pd.DataFrame(
        {
            "date": ["2024-01", "2024-02", "2024-03"],
            "gare_depart": ["A", "B", "C"],
            "gare_arrivee": ["B", "C", "D"],
            "nb_train_prevu": [0, 50, 100],
            "nb_annulation": [0, 60, 10],
            "nb_train_retard_arrivee": [0, 5, 9],
            "duree_moyenne": [60.0, 90.0, 120.0],
        }
    )
    analyse = AnalyseCirculations(df_anomalies)
    diag = analyse.diagnostic_qualite()
    assert diag["total_lignes"] == 3
    assert diag["lignes_valides"] == 1
    assert diag["lignes_invalides"] == 2

    filtre_valide = analyse.filtrer(exclure_invalides=True)
    assert len(filtre_valide) == 1
    assert filtre_valide.iloc[0]["gare_depart"] == "C"


def test_exceptions_entrees_invalides(df_exemple_sncf: pd.DataFrame) -> None:
    """Verifie que les erreurs metier explicites sont bien levees."""
    with pytest.raises(ErreurValidationCirculations, match="DataFrame"):
        AnalyseCirculations("pas_un_dataframe")  # type: ignore[arg-type]

    df_incomplet = df_exemple_sncf.drop(columns=["nb_annulation"])
    with pytest.raises(ErreurValidationCirculations, match="nb_annulation"):
        AnalyseCirculations(df_incomplet)

    analyse = AnalyseCirculations(df_exemple_sncf)
    with pytest.raises(ErreurValidationCirculations, match="volume minimal"):
        analyse.filtrer(volume_min=-5)

    with pytest.raises(ErreurValidationCirculations, match="date de debut"):
        analyse.filtrer(date_debut="2024-05", date_fin="2024-01")

    with pytest.raises(ErreurValidationCirculations, match="min_mois"):
        analyse.agreger_par_liaison(min_mois=0)

    with pytest.raises(ErreurValidationCirculations, match="Indicateur cible"):
        analyse.calculer_correlations_volume(cible="colonne_inexistante")

    with pytest.raises(
        ErreurValidationCirculations, match="volume minimal par liaison"
    ):
        analyse.construire_groupes_volume(volume_min_liaison=-1.0)


def test_analyses_a_b_c_et_cas_limites(df_exemple_sncf: pd.DataFrame) -> None:
    """Verifie les methodes des volets A, B, C ainsi que les filtres et cas vides."""
    analyse = AnalyseCirculations(df_exemple_sncf)

    # Filtrage avec criteres
    sous_df = analyse.filtrer(
        date_debut="2024-01",
        date_fin="2024-02",
        liaisons=["PARIS LYON -> LYON PART DIEU"],
        volume_min=10,
    )
    assert len(sous_df) == 2
    res_normal = analyse.resume(sous_df)
    assert res_normal.loc[0, "total_trains_prevus"] == 120

    # Volet A : correlations (normal + echantillon trop petit)
    corr = analyse.calculer_correlations_volume(cible="taux_annulation")
    assert corr["n"] == 4
    assert -1.0 <= float(corr["spearman"]) <= 1.0

    corr_petit = analyse.calculer_correlations_volume(
        donnees_table=sous_df, cible="taux_annulation"
    )
    assert np.isnan(corr_petit["pearson"])

    # Volet B : groupes de volume (normal + volume homogene + vide)
    groupes = analyse.construire_groupes_volume()
    assert "groupe_volume" in groupes.columns
    groupes_homogenes = analyse.construire_groupes_volume(donnees_filtrees=sous_df)
    assert groupes_homogenes.loc[0, "groupe_volume"] == "Volume homogene"
    groupes_vides = analyse.construire_groupes_volume(volume_min_liaison=999999)
    assert groupes_vides.empty

    # Volet C : duree et IQR (normal + vide)
    durees = analyse.analyser_duree_et_robustesse(exclure_extremes_iqr=True)
    assert "categorie_duree" in durees.columns

    # Selection vide distinguee d'un vrai zero
    vide = analyse.filtrer(liaisons=["LIAISON_INEXISTANTE"])
    res_vide = analyse.resume(vide)
    assert res_vide.loc[0, "nb_observations"] == 0
    assert np.isnan(res_vide.loc[0, "taux_annulation_pondere"])
    assert analyse.agreger_par_liaison(vide).empty
    assert analyse.agreger_par_liaison(min_mois=99).empty
    assert analyse.analyser_duree_et_robustesse(vide).empty
    corr_vide = analyse.calculer_correlations_volume(donnees_table=vide)
    assert corr_vide["n"] == 0
