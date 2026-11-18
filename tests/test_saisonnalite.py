"""Vérifications sur une petite base SQL isolée, sans toucher à PostgreSQL."""

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine

from projet_railinsight.saisonnalite import (
    analyser_saisonnalite, calculer_regression, charger_donnees_mensuelles,
)


@pytest.fixture
def engine():
    moteur = create_engine("sqlite://")
    pd.DataFrame({
        "date": ["2025-01", "2025-01", "2025-02", "2024-01"],
        "service": ["National", "National", "International", "National"],
        "nb_circulation_prevues": [100, 200, 100, 0],
        "nb_annulation": [10, -2, 5, 0],
        "nb_train_depart_retard": [20, 30, 10, 0],
        "nb_train_retard_arrivee": [25, 40, 12, 0],
    }).to_sql("regularite_tgv", moteur, index=False)
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
    assert resultat['mensuel'].empty
    assert not resultat['regression']['disponible']
    with pytest.raises(ValueError):
        charger_donnees_mensuelles(engine, annee_debut=2026, annee_fin=2025)


def test_regression_coefficients_et_degres_liberte():
    mois = np.arange(1, 13)
    annulations = np.array([2, 5, 1, 4, 3, 9, 7, 6, 5, 1, 8, 4])
    data = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=12, freq='MS'),
        'mois': mois, 'total_annulation': annulations,
        'total_retard_depart': 10 + 2 * mois + 3 * annulations,
    })
    resultat = calculer_regression(data)
    np.testing.assert_allclose(resultat['coefficients']['coefficient'], [10, 2, 3])
    assert resultat['ddl'] == 9
    assert resultat['r2'] == pytest.approx(1)
    data['total_annulation'] = 1
    assert not calculer_regression(data)['disponible']
