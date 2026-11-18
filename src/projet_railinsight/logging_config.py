"""Configuration des logs du projet RailInsight."""

import logging
from pathlib import Path


def configurer_logs() -> None:
    """Enregistre les messages de debug et les erreurs dans deux fichiers."""

    # On cree le dossier logs s'il n'existe pas
    Path("logs").mkdir(exist_ok=True)

    # On recupere le logger de notre projet
    logger = logging.getLogger("projet_railinsight")
    logger.setLevel(logging.DEBUG)

    # On evite de configurer plusieurs fois le meme logger
    if logger.handlers:
        return

    # On cree le fichier pour enregistrer les messages de debug
    debug = logging.FileHandler("logs/debug.log", encoding="utf-8")
    debug.setLevel(logging.DEBUG)

    # On cree le fichier pour enregistrer les erreurs
    erreurs = logging.FileHandler("logs/errors.log", encoding="utf-8")
    erreurs.setLevel(logging.ERROR)

    # On associe les deux fichiers au logger
    logger.addHandler(debug)
    logger.addHandler(erreurs)
