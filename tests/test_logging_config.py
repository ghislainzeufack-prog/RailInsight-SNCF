"""Test du module logging_config.py"""

import logging

from projet_railinsight.logging_config import configurer_logs


def test_configurer_logs(tmp_path, monkeypatch) -> None:
    """Verifie la creation des fichiers et l'enregistrement des messages."""

    # On utilise un dossier temporaire pour notre test
    monkeypatch.chdir(tmp_path)

    # On isole le logger pour ne pas modifier celui des autres tests
    logger = logging.getLogger("projet_railinsight")
    monkeypatch.setattr(logger, "handlers", [])

    # On configure les logs
    configurer_logs()

    try:
        # On verifie que les deux fichiers ont ete crees
        assert (tmp_path / "logs" / "debug.log").exists()
        assert (tmp_path / "logs" / "errors.log").exists()

        # On enregistre deux messages
        logger.info("Test information")
        logger.error("Test erreur")

        # On verifie que les messages sont ecrits dans les fichiers
        for handler in logger.handlers:
            handler.flush()

        debug = (tmp_path / "logs" / "debug.log").read_text(encoding="utf-8")

        erreurs = (tmp_path / "logs" / "errors.log").read_text(encoding="utf-8")

        # On verifie que chaque message est dans le bon fichier
        assert "Test information" in debug
        assert "Test erreur" in erreurs
        assert "Test information" not in erreurs

    finally:
        # On ferme les fichiers ouverts pendant le test
        for handler in logger.handlers:
            handler.close()
