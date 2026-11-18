"""Vérifications sur une petite base SQL isolée, sans toucher à PostgreSQL."""

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine

from projet_railinsight.saisonnalite import (
    analyser_saisonnalite,
    calculer_regression,
    charger_donnees_mensuelles,
)


@pytest.fixture
def engine():
    moteur = create_engine("sqlite://")
    pd.DataFrame(
        {
            "date": ["2025-01", "2025-01", "2025-02", "2024-01"],
            "service": ["National", "National", "International", "National"],
            "nb_circulation_prevues": [100, 200, 100, 0],
            "nb_annulation": [10, -2, 5, 0],
            "nb_train_depart_retard": [20, 30, 10, 0],
            "nb_train_retard_arrivee": [25, 40, 12, 0],
        }
    ).to_sql("regularite_tgv", moteur, index=False)
    with moteur.begin() as conn:
        conn.exec_driver_sql("""
            CREATE VIEW regularite_tgv_clean AS
            SELECT date, service, nb_circulation_prevues,
                   CASE WHEN nb_annulation < 0
                          OR nb_annulation > nb_circulation_prevues
                        THEN NULL ELSE nb_annulation END AS nb_annulation,
                   nb_train_depart_retard, nb_train_retard_arrivee
            FROM regularite_tgv
        """)
    yield moteur
    moteur.dispose()


def test_nettoyage_et_taux_sur_memes_lignes(engine):
    data = charger_donnees_mensuelles(engine, annee_debut=2025, annee_fin=2025)
    assert len(data) == 1
    ligne = data.iloc[0]
    assert ligne.total_annulation == 10
    assert ligne.nb_annulations_manquantes == 1
    assert ligne.taux_annulation == 10
    assert ligne.taux_perturbation_depart == 30
    assert ligne.total_retard_depart == 50
    brut = charger_donnees_mensuelles(engine, nettoyage=False, annee_debut=2025)
    assert brut.iloc[0].total_annulation == 8


def test_filtres_vide_et_zero(engine):
    assert len(charger_donnees_mensuelles(engine, service=None)) == 3
    assert pd.isna(charger_donnees_mensuelles(engine).iloc[0].taux_annulation)
    resultat = analyser_saisonnalite(engine, service="National' OR 1=1 --")
    assert resultat["mensuel"].empty
    assert not resultat["regression"]["disponible"]
    with pytest.raises(ValueError):
        charger_donnees_mensuelles(engine, annee_debut=2026, annee_fin=2025)


def test_regression_coefficients_et_degres_liberte():
    mois = np.arange(1, 13)
    annulations = np.array([2, 5, 1, 4, 3, 9, 7, 6, 5, 1, 8, 4])
    data = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=12, freq="MS"),
            "mois": mois,
            "total_annulation": annulations,
            "total_retard_depart": 10 + 2 * mois + 3 * annulations,
        }
    )
    resultat = calculer_regression(data)
    np.testing.assert_allclose(resultat["coefficients"]["coefficient"], [10, 2, 3])
    assert resultat["ddl"] == 9
    assert resultat["r2"] == pytest.approx(1)
    data["total_annulation"] = 1
    assert not calculer_regression(data)["disponible"]


@pytest.mark.parametrize("annee", [0, 10000, "2024", True])
def test_annee_invalide(engine, annee):
    with pytest.raises(ValueError, match="années"):
        charger_donnees_mensuelles(engine, annee_debut=annee)


def test_graphiques_et_mois_absents(engine):
    from io import BytesIO

    from projet_railinsight.saisonnalite import (
        tracer_comparaison_annuelle,
        tracer_correlations,
        tracer_evolution,
    )

    data = charger_donnees_mensuelles(engine)
    comparaison = tracer_comparaison_annuelle(data)
    assert len(comparaison.axes[0].lines) == 2
    assert len(comparaison.axes[0].lines[0].get_xdata()) == 12
    assert np.isnan(comparaison.axes[0].lines[0].get_ydata()[1])
    for figure in [comparaison, tracer_evolution(data), tracer_correlations(data)]:
        fichier = BytesIO()
        figure.savefig(fichier, format="png")
        assert fichier.getvalue().startswith(b"\x89PNG")
    assert len(tracer_comparaison_annuelle(data.iloc[:0]).axes[0].lines) == 0
    with pytest.raises(ValueError):
        tracer_comparaison_annuelle(data, "inconnu")


def test_residus_et_test_manuel(engine, monkeypatch, capsys):
    from projet_railinsight import saisonnalite

    mois = np.arange(1, 13)
    annulations = np.array([2, 5, 1, 4, 3, 9, 7, 6, 5, 1, 8, 4])
    data = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=12, freq="MS"),
            "mois": mois,
            "annee": 2025,
            "total_annulation": annulations,
            "total_retard_depart": 10 + 2 * mois + 3 * annulations,
            "total_retard_arrivee": 5 + mois,
        }
    )
    regression = calculer_regression(data)
    figure = saisonnalite.tracer_residus(regression)
    assert sum(barre.get_height() for barre in figure.axes[0].patches) == 12
    with pytest.raises(ValueError, match="indisponible"):
        saisonnalite.tracer_residus({"disponible": False, "raison": "indisponible"})
    # Le test manuel n’a pas besoin de créer ou fermer le moteur fourni.
    monkeypatch.setattr(
        saisonnalite, "charger_donnees_mensuelles", lambda *a, **k: data
    )
    resultat = saisonnalite.tester_analyse(engine)
    assert resultat["regression"]["disponible"]
    assert "R²" in capsys.readouterr().out
    data["total_annulation"] = 1
    assert not saisonnalite.tester_analyse(engine)["regression"]["disponible"]
    monkeypatch.setattr(
        saisonnalite, "charger_donnees_mensuelles", lambda *a, **k: data.iloc[:0]
    )
    with pytest.raises(ValueError, match="Aucune donnée"):
        saisonnalite.tester_analyse(engine)
