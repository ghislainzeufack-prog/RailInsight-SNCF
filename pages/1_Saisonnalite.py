"""Page Streamlit de l’analyse de saisonnalité."""

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from projet_railinsight.moteur_sql import creer_connexion, executer_requete
from projet_railinsight.saisonnalite import (
    analyser_saisonnalite,
    tracer_comparaison_annuelle,
    tracer_correlations,
    tracer_evolution,
    tracer_residus,
)

st.set_page_config(page_title="Saisonnalité · RailInsight", page_icon="🚆", layout="wide")
st.title("Saisonnalité des TGV")
st.caption("Explorer les retards et les annulations au fil des mois.")


@st.cache_resource
def moteur_sql():
    return creer_connexion()


@st.cache_data(ttl=300, show_spinner=False)
def options_disponibles():
    return executer_requete(
        moteur_sql(),
        "SELECT DISTINCT date, service FROM regularite_tgv ORDER BY date;",
    )


@st.cache_data(ttl=300, max_entries=32, show_spinner=False)
def charger_analyse(nettoyage, service, annee_debut, annee_fin):
    return analyser_saisonnalite(
        engine=moteur_sql(),
        nettoyage=nettoyage,
        service=service,
        annee_debut=annee_debut,
        annee_fin=annee_fin,
    )


try:
    with st.spinner("Chargement des périodes disponibles…"):
        options = options_disponibles()
except (SQLAlchemyError, OSError, ValueError):
    st.error("La base de données est indisponible. Réessaie dans quelques instants.")
    if st.button("Réessayer"):
        options_disponibles.clear()
        st.rerun()
    st.stop()

if options.empty:
    st.info("La base ne contient aucune donnée à analyser.")
    st.stop()

annees = sorted(pd.to_datetime(options["date"], errors="coerce").dt.year.dropna().astype(int).unique().tolist())
services = sorted(options["service"].dropna().unique().tolist())
if not annees:
    st.info("Aucune période valide n’est disponible.")
    st.stop()

with st.sidebar:
    st.header("Filtres de l’analyse")
    with st.form("filtres_saisonnalite"):
        service = st.selectbox(
            "Service", [None, *services],
            index=services.index("National") + 1 if "National" in services else 0,
            format_func=lambda valeur: "Tous les services" if valeur is None else valeur,
        )
        annee_debut = st.selectbox("Année de début", annees, index=0)
        annee_fin = st.selectbox("Année de fin", annees, index=len(annees) - 1)
        nettoyage = st.checkbox("Utiliser les données nettoyées", value=True)
        st.form_submit_button("Appliquer les filtres", type="primary")
    st.caption("Les résultats sont conservés 5 minutes pour limiter les requêtes.")

if annee_debut > annee_fin:
    st.warning("L’année de début doit précéder ou être égale à l’année de fin.")
    st.stop()

try:
    with st.spinner("Analyse en cours…"):
        resultats = charger_analyse(nettoyage, service, annee_debut, annee_fin)
except (SQLAlchemyError, OSError, ValueError):
    st.error("Impossible de charger l’analyse. Vérifie les filtres ou réessaie plus tard.")
    if st.button("Réessayer l’analyse"):
        charger_analyse.clear()
        st.rerun()
    st.stop()

data = resultats["mensuel"]
if data.empty:
    st.info("Aucune donnée pour cette sélection. Modifie les filtres.")
    st.stop()

st.caption(
    f"{service or 'Tous les services'} · {annee_debut}–{annee_fin} · "
    f"Données {'nettoyées' if nettoyage else 'brutes'}"
)


def total_affiche(colonne):
    total = data[colonne].sum(min_count=1)
    return "Non disponible" if pd.isna(total) else f"{total:,.0f}".replace(",", " ")


colonnes = st.columns(4)
colonnes[0].metric("Mois disponibles", len(data))
colonnes[1].metric("Circulations prévues", total_affiche("total_circulations_prevues"))
colonnes[2].metric("Annulations connues", total_affiche("total_annulation"))
colonnes[3].metric("Retards au départ connus", total_affiche("total_retard_depart"))

manquantes = int(data["nb_annulations_manquantes"].sum())
if manquantes:
    st.info(f"{manquantes} lignes ont un nombre d’annulations inconnu ou exclu du calcul.")

onglet_donnees, onglet_saison, onglet_correlation, onglet_regression = st.tabs(
    ["Données", "Saisonnalité", "Corrélations", "Régression"]
)

with onglet_donnees:
    st.subheader("Données mensuelles")
    st.dataframe(data, hide_index=True, width="stretch")
    st.download_button(
        "Télécharger le CSV",
        data.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"saisonnalite_{annee_debut}_{annee_fin}.csv",
        mime="text/csv",
    )
    with st.expander("Statistiques descriptives"):
        st.dataframe(
            resultats["description"]["statistiques"].drop(columns="date", errors="ignore"),
            width="stretch",
        )
    st.caption("Les taux sont exprimés en pourcentage des circulations prévues connues.")

with onglet_saison:
    libelles = {
        "total_annulation": "Annulations",
        "total_retard_depart": "Retards au départ",
        "total_retard_arrivee": "Retards à l’arrivée",
    }
    indicateur = st.selectbox("Indicateur à comparer", list(libelles), format_func=libelles.get)
    st.subheader("Comparaison par année")
    st.pyplot(tracer_comparaison_annuelle(data, indicateur))
    st.subheader("Moyenne par mois de l’année")
    st.bar_chart(resultats["saisonnalite"][[indicateur]].rename(columns=libelles))
    st.caption("Ces moyennes dépendent du volume de circulation et des années disponibles.")
    with st.expander("Évolution chronologique"):
        st.pyplot(tracer_evolution(data))

with onglet_correlation:
    st.subheader("Relations entre les indicateurs")
    st.pyplot(tracer_correlations(data))
    st.dataframe(resultats["correlations"], width="stretch")
    st.caption("Une corrélation ne démontre pas une relation de cause à effet.")

with onglet_regression:
    st.subheader("Retards au départ selon le mois et les annulations")
    regression = resultats["regression"]
    if not regression["disponible"]:
        st.info(regression["raison"])
    else:
        gauche, droite = st.columns(2)
        gauche.metric("Observations", regression["n_observations"])
        r2 = regression["r2"]
        droite.metric("R²", f"{r2:.3f}" if pd.notna(r2) else "Non défini")
        st.dataframe(regression["coefficients"], width="stretch")
        st.line_chart(regression["observations"].set_index("date")[["observe", "prediction"]])
        st.pyplot(tracer_residus(regression))
        with st.expander("Valeurs observées, prédictions et résidus"):
            st.dataframe(regression["observations"], hide_index=True, width="stretch")
    st.caption(
        "Modèle exploratoire : le mois est numérique, sans représentation cyclique. "
        "Les tests supposent des erreurs indépendantes et de variance constante."
    )
