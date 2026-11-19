"""Vérifier le moteur commun sans accès réseau ni identifiants externes."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine

from projet_railinsight import moteur_sql


@pytest.mark.parametrize(
    ("requete", "valeurs"),
    [("SELECT ?", []), ("SELECT 1", [2])],
)
def test_nombre_parametres(requete, valeurs):
    with pytest.raises(ValueError):
        moteur_sql._adapter_parametres(requete, valeurs)


def test_question_dans_texte_et_commentaire():
    engine = create_engine("sqlite://")
    try:
        data = moteur_sql.executer_requete(
            engine, "SELECT '?' AS texte, ? AS valeur /* ? */ -- ?", ["L'été"]
        )
        assert data.iloc[0].to_dict() == {"texte": "?", "valeur": "L'été"}
        assert moteur_sql.executer_requete(engine, "SELECT 1 AS valeur").iloc[0, 0] == 1
        # Le moteur reste utilisable après chaque lecture.
        with engine.connect() as connexion:
            assert connexion.exec_driver_sql("SELECT 2").scalar() == 2
    finally:
        engine.dispose()


@pytest.mark.parametrize("valeurs", ["National", b"National", {"service": "National"}])
def test_parametres_dans_ordre_uniquement(valeurs):
    with pytest.raises(TypeError):
        moteur_sql.executer_requete(Mock(), "SELECT ?", valeurs)


def test_connexion_vps_verifie_certificat(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fabrique = Mock()
    monkeypatch.setattr(moteur_sql, "create_engine", fabrique)
    assert moteur_sql.creer_connexion() is fabrique.return_value
    options = fabrique.call_args.kwargs["connect_args"]
    assert options["connect_timeout"] == 10
    assert Path(options["sslrootcert"]).is_file()
    assert "sslmode=verify-ca" in fabrique.call_args.args[0]


def test_url_explicite_prioritaire(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env/db")
    fabrique = Mock()
    monkeypatch.setattr(moteur_sql, "create_engine", fabrique)
    moteur_sql.creer_connexion("postgresql+psycopg://explicite/db")
    assert fabrique.call_args.args[0] == "postgresql+psycopg://explicite/db"
    moteur_sql.creer_connexion()
    assert fabrique.call_args.args[0] == "postgresql+psycopg://env/db"
