"""Accueil et navigation automatique entre les analyses."""

import re
import sys
from pathlib import Path

import streamlit as st

# Toutes les pages trouvent les modules locaux, même sans installation éditable.
REPERTOIRE_PROJET = Path(__file__).resolve().parent
REPERTOIRE_SOURCES = str(REPERTOIRE_PROJET / "src")
if REPERTOIRE_SOURCES not in sys.path:
    sys.path.insert(0, REPERTOIRE_SOURCES)

st.set_page_config(page_title="RailInsight SNCF", layout="wide")


def ordre_page(page: Path):
    """Trier les pages numérotées avant les pages sans numéro."""
    numero = re.match(r"^(\d+)", page.stem)
    return (int(numero.group()) if numero else float("inf"), page.stem.casefold())


fichiers = sorted(
    (
        page for page in (REPERTOIRE_PROJET / "pages").glob("*.py")
        if page.name != "__init__.py"
    ),
    key=ordre_page,
)

pages = []
for fichier in fichiers:
    titre = re.sub(r"^\d+[_\s-]*", "", fichier.stem).replace("_", " ").strip()
    pages.append(
        st.Page(f"pages/{fichier.name}", title=titre or fichier.stem, icon="📊")
    )


def accueil():
    st.title("RailInsight - Régularité des TGV")
    st.write("Explore les retards et les annulations des TGV.")
    st.subheader("Analyses disponibles")
    for page in pages:
        st.page_link(page, label=page.title, icon="📊")
    if not pages:
        st.info("Aucune analyse disponible pour le moment.")


navigation = st.navigation([st.Page(accueil, title="Accueil", default=True), *pages])
navigation.run()
