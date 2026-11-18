"""Ce module permet de tester les differentes fonctions implementees dans causes.py"""

import pandas as pd
import pytest

from projet_railinsight.causes import (
    COLONNES_CAUSES,
    AnalyseCauses,
    AnalyseCausesErreur,
    ColonnesManquantesErreur,
)


@pytest.fixture
def df_sncf() -> pd.DataFrame:
    """Cree trois observations valides et deux profils non exploitables."""
    df = pd.DataFrame(
        {
            "Date": ["2026-01", "2026-02", "2026-02", "2026-03", "2026-03"],
            "Gare de départ": ["Yaoundé", "Yaoundé", "Douala", "Yaoundé", "Yaoundé"],
            "Gare d'arrivée": ["Douala", "Douala", "Yaoundé", "Douala", "Douala"],
            "Nombre de trains en retard à l'arrivée": [5, 10, 40, 0, 12],
            "Nombre de circulations prévues": [30, 80, 100, 10, 40],
            "Nombre de trains annulés": [2, 5, 0, 0, 3],
        }
    )
    for cause in COLONNES_CAUSES:
        df[cause] = 0.0
    df.loc[:, COLONNES_CAUSES[0]] = [20, 35, 30, 0, 15]
    df.loc[:, COLONNES_CAUSES[1]] = [80, 65, 70, 0, 20]
    return df


def test_colonne_manquante(df_sncf: pd.DataFrame) -> None:
    """Le test reussi s'il manque une colonne obligatoire et que notre
    programme detecte correctement cette absence
    """

    # On retire volontairement la colonne 'Date'
    df_incomplet = df_sncf.drop(columns="Date")

    # On verifie que notre classe 'ColonnesManquantesErreur' detecte
    # l'exception levee dont le message contient 'Date'
    with pytest.raises(ColonnesManquantesErreur, match="Date"):
        # On cree un objet avec le DataFrame incomplet, et normalement
        # on doit lever une exception
        AnalyseCauses(df_incomplet)


def test_format_periode_invalide(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie qu'une date au mauvais format
    declenche bien une exception AnalyseCausesErreur.
    """
    analyse = AnalyseCauses(df_sncf)

    with pytest.raises(
        AnalyseCausesErreur, match="La période attend le format YYYY-MM"
    ):
        analyse.filtrer_periode("2026-02c", "2026-02")


def test_filtrer_periode(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie que l'on conserve toutes les observations du mois
    selectionnee, y compris lorsque la date de début est identique à la
    date de fin.
    """
    analyse = AnalyseCauses(df_sncf).filtrer_periode("2026-02", "2026-02")
    assert len(analyse.donnees()) == 2


def test_periode_inversee(df_sncf: pd.DataFrame) -> None:
    """Ce test reussi si une période invalide declenche une exception contrôlée."""
    with pytest.raises(AnalyseCausesErreur, match="La date de début"):
        AnalyseCauses(df_sncf).filtrer_periode("2026-03", "2026-01")


def test_fitrer_liaison(df_sncf: pd.DataFrame) -> None:
    """Ce test verfie qu'on selectionne uniquement les trains circulant dans
    le sens demandé.
    """
    analyse = AnalyseCauses(df_sncf).filtrer_liaison("Yaoundé", "Douala")
    assert len(analyse.donnees()) == 4  # On doit avoir 4 observations Yaoundé -> Douala
    assert set(analyse.donnees()["Gare de départ"]) == {
        "Yaoundé"
    }  # On s'assure qu'on n'a bien un set {"Yaoundé"}, et pas {"Yaoundé", "Douala"}


def test_regrouper_sens(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie si le regroupement contient les liaisons dans
    les deux sens.
    """
    analyse = AnalyseCauses(df_sncf).regrouper_sens("Yaoundé", "Douala")
    assert len(analyse.donnees()) == 5


def test_conserver_observations_exploitables(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie si les observations avec zero train en retard
    a l'arrivee, et/ou la somme de pourcentage des causes de retard
    different de 100 avec une tolerance de TOLERANCE_POURCENTAGE
    """
    analyse = AnalyseCauses(df_sncf)

    assert analyse.analyser_volume()["observations"] == 5
    assert analyse.analyser_volume()["observations_exploitables"] == 3
    assert analyse.analyser_volume()["retards_a_l_arrivee"] == 67
    assert analyse.analyser_volume()["retards_couverts"] == 55
    assert analyse.analyser_volume()["retards_exclus"] == 12
    assert analyse.analyser_volume()["circulations_prevues"] == 260


def test_pondere_avec_le_nombre_de_retards(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie le calcul de la moyenne ponderee et de la mediane"""
    analyse = AnalyseCauses(df_sncf).filtrer_liaison("Yaoundé", "Douala")
    repartition = analyse.repartition_causes().set_index("cause")

    # Moyenne ponderee : (20 × 5 + 35 × 10) / (5 + 10) = 30 %
    assert repartition.loc["causes externes", "part_ponderee_pct"] == pytest.approx(30)

    # Mediane : (20 + 35) / 2 = 27,5 %
    assert repartition.loc["causes externes", "mediane_pct"] == pytest.approx(27.5)


def test_aucune_donnee_valide(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie si l'exception est bien levee si on a aucune observation exploitable"""
    analyse = AnalyseCauses(df_sncf).filtrer_periode("2026-03", "2026-03")
    with pytest.raises(AnalyseCausesErreur, match="Aucune observation"):
        analyse.repartition_causes()


def test_comparer_liaisons(df_sncf: pd.DataFrame) -> None:
    """Les profils orientes A->B et B-A restent distincts."""
    analyse = AnalyseCauses(df_sncf)
    tableau = analyse.comparer_liaisons([("Yaoundé", "Douala"), ("Douala", "Yaoundé")])
    assert tableau["liaison"].nunique() == 2
    assert len(tableau) == 12


def test_comparaison_nombres_invalides(df_sncf: pd.DataFrame) -> None:
    """Ce test verifie qu'on leve bien un exception si on n'a pas entre 2 et 5 liaisons à comparer
    ou si on n'a pas deux liaisons distinctes
    """
    analyse = AnalyseCauses(df_sncf)
    with pytest.raises(AnalyseCausesErreur, match="entre 2 et 5"):
        analyse.comparer_liaisons([("Yaoundé", "Douala")])
    with pytest.raises(AnalyseCausesErreur, match="doivent être distinctes"):
        analyse.comparer_liaisons([("Yaoundé", "Douala"), ("Yaoundé", "Douala")])
