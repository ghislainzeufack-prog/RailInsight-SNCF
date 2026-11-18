"""Accueil : liste automatiquement les analyses du dossier pages/."""

import re
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="RailInsight SNCF", layout="wide")
st.title("RailInsight - Régularité des TGV")
st.write("Explore les retards et les annulations des TGV.")
st.subheader("Analyses disponibles")

repertoire_pages = Path(__file__).parent / "pages"
pages = [
    page for page in repertoire_pages.glob("*.py")
    if page.name != "__init__.py"
]


def ordre_page(page: Path):
    """Trier les pages numérotées avant les pages sans numéro."""
    numero = re.match(r"^(\d+)", page.stem)
    return (int(numero.group()) if numero else float("inf"), page.stem.casefold())


for page in sorted(pages, key=ordre_page):
    titre = re.sub(r"^\d+[_\s-]*", "", page.stem).replace("_", " ").strip()
    st.page_link(
        f"pages/{page.name}",
        label=titre or page.stem,
        icon="📊",
    )

if not pages:
    st.info("Aucune analyse disponible pour le moment.")
