"""Vérifier l’initialisation sans modifier une base PostgreSQL réelle."""

from unittest.mock import MagicMock

import pytest

from projet_railinsight import db_init


@pytest.mark.parametrize("deja_remplie", [False, True])
def test_initialisation_et_import_unique(monkeypatch, tmp_path, deja_remplie):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Database").mkdir()
    (tmp_path / "Database/shema.sql").write_text("CREATE TABLE exemple (id INTEGER);")
    (tmp_path / "Data").mkdir()
    (tmp_path / "Data/regularite-mensuelle-tgv-aqst.csv").write_text("id\n1\n")
    administration = MagicMock()
    administration.cursor.return_value.fetchone.return_value = (
        (1,) if deja_remplie else None
    )
    base = MagicMock()
    curseur = base.cursor.return_value
    curseur.fetchone.side_effect = [(1,)] if deja_remplie else [(0,), (1,)]
    connexion = MagicMock(side_effect=[administration, base])
    monkeypatch.setattr(db_init.psycopg, "connect", connexion)

    db_init.main()

    sql_admin = [
        appel.args[0]
        for appel in administration.cursor.return_value.execute.call_args_list
    ]
    assert any("CREATE DATABASE" in sql for sql in sql_admin) is (not deja_remplie)
    if deja_remplie:
        curseur.copy.assert_not_called()
    else:
        copie = curseur.copy.return_value.__enter__.return_value
        copie.write.assert_called_once_with("id\n1\n")
    assert base.commit.called
    administration.close.assert_called_once()
    base.close.assert_called_once()
