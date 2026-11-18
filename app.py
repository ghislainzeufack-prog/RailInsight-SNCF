"""Page Streamlit : volumes et répartition des causes SNCF."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from projet_railinsight.causes import AnalyseCauses, AnalyseCausesErreur

# Lecture des donnees
FICHIER_CSV = Path("data/raw/regularite-mensuelle-tgv-aqst.csv")

COLONNE_RETARDS = "Nombre de trains en retard à l'arrivée"


# @st.cache_data permet de mettre en cache pour eviter de recharger inutilement les donnees
@st.cache_data(show_spinner="Chargement des données SNCF…")
def charger_donnees(chemin: str) -> pd.DataFrame:
    """Charge le fichier SNCF"""

    return pd.read_csv(chemin, sep=";")


def afficher_repartition(repartition: pd.DataFrame) -> None:
    """Affiche les causes de retard triees selon leur part ponderee."""
    st.subheader("Répartition des causes de retard")

    # On cree un graphique en barres horizontales pour presenter les causes
    # de retard en fonction de leur part ponderee
    fig_causes = px.bar(
        repartition.sort_values("part_ponderee_pct"),
        x="part_ponderee_pct",
        y="cause",
        orientation="h",
        text="part_ponderee_pct",
        labels={"part_ponderee_pct": "Part pondérée (%)", "cause": ""},
    )

    # On personnalise les barres en choisissant la couleur, en arrondissant
    # les valeurs a deux chiffres apres la virgule, et en les affichant a
    # l'exterieur des barres
    fig_causes.update_traces(
        marker_color="#087F8C",
        texttemplate="%{x:.2f} %",
        textposition="outside",
    )

    fig_causes.update_layout(height=430, showlegend=False)
    st.plotly_chart(fig_causes, width="stretch")

    st.dataframe(
        repartition.rename(
            columns={
                "cause": "Cause",
                "mediane_pct": "Médiane (%)",
                "part_ponderee_pct": "Part pondérée (%)",
            }
        ).round(2),
        hide_index=True,
        width="stretch",
    )

    # Permet a l'utilisateur de telecharger les resultats de sa selection
    st.download_button(
        "Télécharger la répartition (CSV)",
        repartition.to_csv(index=False).encode("utf-8-sig"),
        file_name="railinsight_causes.csv",
        mime="text/csv",
    )


def afficher_volumes(analyse: AnalyseCauses) -> None:
    """Affiche les volumes et leur évolution sur la selection courante."""

    # On recupere les effectifs calcules dans notre module causes.py
    volumes = analyse.analyser_volume()

    col1, col2, col3 = st.columns(3)

    # On remplace le separateur de millier par un espace afin de faciliter
    # la lecture des nombres dans Streamlit
    col1.metric(
        "Retards à l'arrivée",
        f"{volumes['retards_a_l_arrivee']:,}".replace(",", " "),
    )
    col2.metric(
        "Retards couverts par l'analyse",
        f"{volumes['retards_couverts']:,}".replace(",", " "),
    )
    col3.metric(
        "Observations exploitables",
        f"{volumes['observations_exploitables']:,}".replace(",", " "),
    )

    if volumes["retards_exclus"] > 0:
        st.info(
            f"{volumes['retards_exclus']} retards appartiennent à des "
            "observations dont la répartition des causes n'est pas exploitable."
        )

    donnees = analyse.donnees()
    if donnees.empty:
        st.warning("Aucune observation pour les filtres sélectionnés.")
        return

    # On regroupe les retards par mois pour suivre leur evolution dans le temps
    volumes_mensuels = (
        donnees.dropna(subset=["Date_parsed"])
        .groupby("Date_parsed", as_index=False)[COLONNE_RETARDS]
        .sum()
    )

    st.subheader("Évolution mensuelle des retards à l'arrivée")
    fig_volumes = px.line(
        volumes_mensuels,
        x="Date_parsed",
        y=COLONNE_RETARDS,
        markers=True,
        labels={"Date_parsed": "Mois", COLONNE_RETARDS: "Retards à l'arrivée"},
    )

    st.plotly_chart(fig_volumes, width="stretch")

    st.caption(
        "Cette courbe compte les retards recensés sur les observations "
        "sélectionnées, y compris si leurs pourcentages de causes "
        "ne sont pas exploitables."
    )


def afficher_sens(analyse: AnalyseCauses, depart: str, arrivee: str) -> None:
    """Compare les causes declarees dans chaque sens de la meme liaison."""

    # On calcule la repartition des causes de retard pour l'aller et le retour
    try:
        comparaison = analyse.comparer_liaisons([(depart, arrivee), (arrivee, depart)])
    except AnalyseCausesErreur:
        st.info(
            "La comparaison aller-retour n'est pas disponible : "
            "au moins un sens ne possède pas de profil de causes exploitable."
        )
        return

    # On affiche les deux sens pour comparer leurs causes de retard
    st.subheader("Aller contre retour : les causes sont-elles identiques ?")
    fig_sens = px.bar(
        comparaison,
        x="cause",
        y="part_ponderee_pct",
        color="liaison",
        barmode="group",
        labels={
            "cause": "Cause",
            "part_ponderee_pct": "Part pondérée (%)",
            "liaison": "Sens",
        },
    )
    fig_sens.update_layout(height=460, xaxis_tickangle=-25)
    st.plotly_chart(fig_sens, width="stretch")


def afficher_comparaison(analyse: AnalyseCauses) -> None:
    """Permet de comparer de deux à cinq liaisons orientees."""

    # Seules les liaisons avec au moins une répartition valide sont proposees.
    donnees = analyse.conserver_observations_exploitables()
    if donnees.empty:
        st.warning("Aucune liaison exploitable sur cette période.")
        return

    liaisons = {
        f"{depart} -> {arrivee}": (depart, arrivee)
        for depart, arrivee in zip(
            donnees["Gare de départ"],
            donnees["Gare d'arrivée"],
            strict=True,
        )
    }

    options = sorted(liaisons)
    if len(options) < 2:
        st.info("Il faut au moins deux liaisons exploitables pour les comparer.")
        return

    selection = st.multiselect(
        "Choisissez entre deux et cinq liaisons orientées",
        options=options,
        default=options[:2],
        max_selections=5,
    )
    if len(selection) < 2:
        st.info("Sélectionnez au moins deux liaisons pour lancer la comparaison.")
        return

    # On recipere les repartitions calculees pour les liaisons choisies
    comparaison = analyse.comparer_liaisons([liaisons[cle] for cle in selection])

    # On compare les pourcentages des causes avec des barres groupees par liaison
    st.subheader("Comparaison des répartitions de causes")
    fig_groupes = px.bar(
        comparaison,
        x="cause",
        y="part_ponderee_pct",
        color="liaison",
        barmode="group",
        labels={
            "cause": "Cause",
            "part_ponderee_pct": "Part pondérée (%)",
            "liaison": "Liaison",
        },
    )
    fig_groupes.update_layout(height=470, xaxis_tickangle=-25)
    st.plotly_chart(fig_groupes, width="stretch")

    # On place les liaisons en lignes et les causes de retard en colonne pour construire
    # la carte de chaleur des pourcentages ponderes
    st.subheader("Carte de chaleur des causes")
    tableau = comparaison.pivot_table(
        index="liaison",
        columns="cause",
        values="part_ponderee_pct",
        aggfunc="first",
    )

    fig_chaleur = px.imshow(
        tableau.round(1),
        text_auto=".1f",
        aspect="auto",
        color_continuous_scale="Blues",
        labels={"color": "Part pondérée (%)"},
    )

    fig_chaleur.update_layout(height=max(330, len(selection) * 85 + 180))
    st.plotly_chart(fig_chaleur, width="stretch")

    # On affiche les volumes de chaque liaison
    st.subheader("Volumes associés aux liaisons comparées")
    volumes = pd.DataFrame(
        [
            {
                "Liaison": cle,
                **analyse.filtrer_liaison(*liaisons[cle]).analyser_volume(),
            }
            for cle in selection
        ]
    )

    st.dataframe(
        volumes[
            [
                "Liaison",
                "retards_a_l_arrivee",
                "retards_couverts",
                "observations_exploitables",
            ]
        ].rename(
            columns={
                "retards_a_l_arrivee": "Retards à l'arrivée",
                "retards_couverts": "Retards couverts",
                "observations_exploitables": "Observations exploitables",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    # On propose l'export csv de la comparaison
    st.download_button(
        "Télécharger la comparaison (CSV)",
        comparaison.to_csv(index=False).encode("utf-8-sig"),
        file_name="railinsight_comparaison_liaisons.csv",
        mime="text/csv",
    )


def afficher_page() -> None:
    """Construit la page interactive à partir du module AnalyseCauses."""

    # On definit la mise en page et le titre de notre page
    st.set_page_config(page_title="RailInsight | Causes TGV", layout="wide")
    st.title("RailInsight — Comprendre les causes des retards TGV")
    st.write(
        "Explorez les six catégories de causes SNCF, les volumes de retards "
        "et les différences entre les liaisons."
    )

    # On verifie la presence du fichier csv
    if not FICHIER_CSV.is_file():
        st.error(
            "Fichier CSV introuvable. Vérifiez que le fichier est bien dans data/raw/."
        )
        st.stop()

    # On charge les donnees
    try:
        df_processed = charger_donnees(str(FICHIER_CSV))
        analyse = AnalyseCauses(df_processed)
    except (OSError, ValueError) as exc:
        st.error(f"Impossible de charger les données SNCF : {exc}")
        st.stop()

    # On recupere les mois disponibles pour construire le filtre de periode
    dates = sorted(
        analyse.donnees()["Date_parsed"].dropna().dt.strftime("%Y-%m").unique().tolist()
    )
    if not dates:
        st.warning("Aucune date mensuelle valide dans le fichier.")
        st.stop()

    st.sidebar.header("Filtres")

    # On affiche par defaut les douze derniers mois disponibles dans le csv
    debut, fin = st.sidebar.select_slider(
        "Période d'analyse",
        options=dates,
        value=(dates[max(0, len(dates) - 12)], dates[-1]),
    )
    analyse = analyse.filtrer_periode(debut, fin)

    # L'utilisateur peut etudier une liaison ou en comparer plusieurs
    mode = st.sidebar.radio(
        "Type d'analyse",
        ["Une liaison", "Comparer des liaisons"],
    )

    if mode == "Comparer des liaisons":
        afficher_comparaison(analyse)
    else:
        # On propse uniquement les gares presentes sur la periode choisie
        donnees = analyse.donnees()
        departs = sorted(donnees["Gare de départ"].dropna().unique().tolist())
        if not departs:
            st.info("Aucune liaison disponible sur la période sélectionnée.")
            st.stop()

        # Les gares d'arrivee dependent de la gare de depart choisie
        depart = st.sidebar.selectbox("Gare de départ", departs)
        arrivees = sorted(
            donnees.loc[donnees["Gare de départ"].eq(depart), "Gare d'arrivée"]
            .dropna()
            .unique()
            .tolist()
        )
        arrivee = st.sidebar.selectbox("Gare d'arrivée", arrivees)
        sens = st.sidebar.radio("Sens de circulation", ["Aller", "Aller-retour"])

        # On filtre soit le sens aller, soit les deux sens de circulation
        if sens == "Aller":
            analyse = analyse.filtrer_liaison(depart, arrivee)
        else:
            analyse = analyse.regrouper_sens(depart, arrivee)

        afficher_volumes(analyse)

        if sens == "Aller-retour":
            afficher_sens(analyse, depart, arrivee)

        # Si la repartition des causes n'est pas exploitable, on affiche
        # un message
        try:
            repartition = analyse.repartition_causes()
        except AnalyseCausesErreur as exc:
            st.warning(str(exc))
        else:
            afficher_repartition(repartition)

    st.divider()
    st.caption(
        "Source : SNCF Open Data, régularité mensuelle TGV par liaisons (AQST). "
        "Les pourcentages pondérés sont descriptifs : ils ne représentent ni des effectifs "
        "exacts attribuables à chaque cause, ni des statistiques officielles globales du "
        "réseau. Un même TGV peut figurer sur plusieurs liaisons."
    )


if __name__ == "__main__":
    afficher_page()
