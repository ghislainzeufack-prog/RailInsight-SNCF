from pathlib import Path

import plotly.express as px
import streamlit as st

from projet_railinsight.fiabilite import AnalyseFiabilite
from projet_railinsight.preprocessing_fiabilite import (
    charger_et_preparer_donnees,
)

# Configuration de la page
st.set_page_config(
    page_title="Fiabilité des liaisons TGV",
    page_icon="🚄",
    layout="wide",
)

st.title("🚄 Fiabilité des liaisons TGV")
st.write("Analyse des retards à l'arrivée des liaisons TGV.")

# Précisions méthodologiques
st.caption(
    "Taux de retard = trains en retard à l'arrivée / trains circulés × 100. "
    "Les indicateurs portent sur les liaisons respectant les filtres."
)


# Chemin du fichier brut SNCF
CHEMIN = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "regularite-mensuelle-tgv-aqst.csv"
)


@st.cache_data
def charger_donnees():
    # Préparation automatique des données
    return charger_et_preparer_donnees(CHEMIN)


if not CHEMIN.exists():
    st.error("Fichier CSV brut SNCF introuvable dans data/raw/.")
    st.stop()

df = charger_donnees()
analyse = AnalyseFiabilite(df)

# Paramètres d'analyse
st.sidebar.header("Filtres")

annee = st.sidebar.selectbox(
    "Année",
    [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2026],
)

if annee == 2020:
    st.info("2020 : année marquée par des perturbations exceptionnelles.")

if annee == 2026:
    st.warning(
        "2026 : données disponibles jusqu'en septembre seulement. "
        "Un minimum de 12 mois exclura toutes les liaisons."
    )

min_circulations = st.sidebar.number_input(
    "Nombre minimal de circulations",
    min_value=1,
    value=500,
    step=100,
)

min_mois = st.sidebar.slider(
    "Nombre minimal de mois observés",
    min_value=1,
    max_value=12,
    value=10,
)

# Classement des liaisons
classement = analyse.classer_liaisons(
    annee=annee,
    min_circulations=min_circulations,
    min_mois=min_mois,
)

if classement.empty:
    st.warning("Aucune liaison ne respecte les filtres sélectionnés.")
    st.stop()

# Indicateurs de synthèse
col1, col2, col3 = st.columns(3)

col1.metric("Liaisons retenues", len(classement))
col2.metric(
    "Taux de retard le plus élevé",
    f"{classement['taux_retard'].max():.2f} %",
)
col3.metric(
    "Trains circulés",
    f"{classement['trains_circules'].sum():,.0f}",
)

# Graphique du Top 10
st.subheader("Top 10 des liaisons les plus en retard")

top10 = classement.head(10).copy()

top10["Liaison"] = top10["Gare de départ"] + " → " + top10["Gare d'arrivée"]

fig_top10 = px.bar(
    top10.sort_values("taux_retard"),
    x="taux_retard",
    y="Liaison",
    color="Service",
    orientation="h",
    labels={
        "taux_retard": "Taux de retard (%)",
    },
    hover_data=["trains_circules", "nombre_mois"],
)

# Affichage des taux sur les barres
fig_top10.update_traces(
    texttemplate="%{x:.1f} %",
    textposition="outside",
    cliponaxis=False,
)

fig_top10.update_layout(
    xaxis_title="Taux de retard à l'arrivée (%)",
    yaxis_title="",
    xaxis_range=[0, min(100, top10["taux_retard"].max() * 1.15)],
)

fig_top10.update_layout(
    height=550,
    yaxis_title="",
)

st.plotly_chart(fig_top10, use_container_width=True)

# Sélection d'une liaison
st.subheader("Évolution mensuelle d'une liaison")

options = list(
    classement[["Service", "Gare de départ", "Gare d'arrivée"]].itertuples(
        index=False, name=None
    )
)

service, depart, arrivee = st.selectbox(
    "Choisir une liaison",
    options,
    format_func=lambda x: f"{x[1]} → {x[2]} ({x[0]})",
)

# Évolution temporelle
evolution = analyse.evolution_temporelle(
    gare_depart=depart,
    gare_arrivee=arrivee,
    service=service,
    annee=annee,
)

fig_evolution = px.line(
    evolution,
    x="Date",
    y="taux_retard",
    markers=True,
    labels={
        "Date": "Mois",
        "taux_retard": "Taux de retard (%)",
    },
)

fig_evolution.update_layout(height=400)

st.plotly_chart(fig_evolution, use_container_width=True)

# Tableau détaillé
with st.expander("Voir le classement détaillé"):
    st.dataframe(classement, use_container_width=True)
