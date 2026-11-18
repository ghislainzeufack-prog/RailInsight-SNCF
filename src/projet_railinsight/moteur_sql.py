"""Moteur PostgreSQL commun aux modules d’analyse."""

import os
import re
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def creer_connexion(url: str | None = None) -> Engine:
    """Connexion directe au VPS, avec certificat TLS vérifié."""
    url = url or os.environ.get("DATABASE_URL")
    options = {"connect_timeout": 10}
    if not url:
        url = (
            "postgresql+psycopg://railinsight_lecture@178.104.170.49:5432/"
            "sncf_c_gro_nul?sslmode=verify-ca"
        )
        options["sslrootcert"] = str(
            Path(__file__).parent / "certificats" / "vps-ca.crt"
        )
    return create_engine(url, pool_pre_ping=True, connect_args=options)


def _adapter_parametres(requete: str, parametres: Sequence) -> tuple[str, dict]:
    """Adapter les ? à SQLAlchemy sans modifier les chaînes et commentaires."""
    # Les ? à l’intérieur de textes SQL ne sont pas des paramètres.
    morceaux = re.compile(
        r"--[^\n]*|/\*.*?\*/|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\""
        r"|(?P<dollar>\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$).*?(?P=dollar)|\?",
        re.DOTALL,
    )
    valeurs = {}

    def remplacer(match):
        if match.group() != "?":
            return match.group()
        index = len(valeurs)
        if index >= len(parametres):
            raise ValueError("Il manque une valeur pour un paramètre ?.")
        nom = f"parametre_{index}"
        valeurs[nom] = parametres[index]
        return f":{nom}"

    sql = morceaux.sub(remplacer, requete)
    if len(valeurs) != len(parametres):
        raise ValueError("Il y a plus de valeurs que de paramètres ?.")
    return sql, valeurs


def executer_requete(
    engine: Engine,
    requete: str,
    parametres: Sequence | None = None,
) -> pd.DataFrame:
    """
    Exemple : executer_requete(engine, "SELECT * FROM regularite_tgv
    WHERE service = ?", ["National"]).).
    """
    if isinstance(parametres, (str, bytes, dict)):
        raise TypeError("Fournir une liste ou un tuple de valeurs dans l’ordre des ?.")
    sql, valeurs = _adapter_parametres(
        requete,
        () if parametres is None else parametres,
    )

    with engine.connect() as connexion:
        return pd.read_sql_query(text(sql), connexion, params=valeurs)
