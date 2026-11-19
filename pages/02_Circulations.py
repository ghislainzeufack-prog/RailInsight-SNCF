"""Page Streamlit : Analyse des circulations, annulations et retards TGV."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from projet_railinsight.circulations import (
    AnalyseCirculations,
    ErreurValidationCirculations,
)

FICHIER_CSV = Path("data/raw/regularite-mensuelle-tgv-aqst.csv")


@st.cache_data(show_spinner="Chargement des donnees TGV SNCF...")
def charger_donnees_tgv() -> pd.DataFrame:
    """Charge le jeu de donnees via common_processing ou les chemins standards."""
    try:
        from projet_railinsight.common_processing import charger_donnees  # type: ignore[import-not-found]

        df_commun = charger_donnees()
        if isinstance(df_commun, pd.DataFrame) and not df_commun.empty:
            return df_commun
    except Exception:
        pass

    chemins_candidats = [
        Path("data/processed/regularite-mensuelle-tgv-aqst.csv"),
        Path("data/raw/regularite-mensuelle-tgv-aqst.csv"),
        Path("data/regularite-mensuelle-tgv-aqst.csv"),
        Path("regularite-mensuelle-tgv-aqst.csv"),
    ]
    for chemin in chemins_candidats:
        if chemin.exists():
            sep = (
                ";"
                if ";" in chemin.read_text(encoding="utf-8", errors="ignore")[:500]
                else ","
            )
            return pd.read_csv(chemin, sep=sep)

    url_sncf = (
        "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/"
        "regularite-mensuelle-tgv-aqst/exports/csv?delimiter=%3B"
    )
    return pd.read_csv(url_sncf, sep=";")


def afficher_page_circulations() -> None:
    """Construit et affiche la page interactive Circulations & Annulations."""
    st.title(
        "Les liaisons davantage desservies connaissent-elles des taux d'annulation ou de retard differents ?"
    )
    st.markdown(
        "Cette page examine la relation entre le **volume de circulations prevues** sur une liaison TGV "
        "et sa vulnerabilite aux **annulations** et aux **retards a l'arrivee**, a partir des donnees "
        "mensuelles ouvertes de la SNCF."
    )

    with st.expander(
        "Que mesurent exactement nos indicateurs ? (Methodologie & Limites)",
        expanded=False,
    ):
        st.markdown(
            "- **Unite d'observation :** Une liaison orientee (`Gare de depart -> Gare d'arrivee`) suivie mensuellement.\n"
            "- **Taux d'annulation pondere (%) :** Somme des trains annules / Somme des trains prevus x 100.\n"
            "- **Taux de retard a l'arrivee pondere (%) :** Somme des trains en retard / Somme des trains ayant reellement circule x 100.\n"
            "- **Limites scientifiques :** Le nombre de circulations prevues decrit l'offre de trains (et non le nombre de voyageurs). "
            "L'analyse est **associative et descriptive** : elle ne demontre pas de lien de causalite."
        )

    if not FICHIER_CSV.exists():
        st.error(
            "Fichier CSV introuvable. Verifiez que le fichier est bien dans data/raw/."
        )
        return

    try:
        df_brut = charger_donnees_tgv(str(FICHIER_CSV))
        analyseur = AnalyseCirculations(df_brut)
    except (ErreurValidationCirculations, OSError, ValueError) as exc:
        st.error(f"Impossible de charger ou valider les donnees SNCF : {exc}")
        return

    df_valide = analyseur.filtrer(exclure_invalides=True)
    if df_valide.empty:
        st.warning("Aucune donnee valide disponible dans le jeu de donnees.")
        return

    st.sidebar.header("Filtres d'analyse")
    dates_dispo = sorted(df_valide["date"].unique())
    date_debut, date_fin = st.sidebar.select_slider(
        "Periode d'observation (YYYY-MM)",
        options=dates_dispo,
        value=(dates_dispo[0], dates_dispo[-1]),
    )

    toutes_liaisons = sorted(df_valide["liaison"].unique())
    liaisons_choisies = st.sidebar.multiselect(
        "Filtrer une ou plusieurs liaisons (optionnel)",
        options=toutes_liaisons,
        default=[],
    )

    max_prevu = int(df_valide["nb_train_prevu"].max()) if not df_valide.empty else 500
    volume_min = st.sidebar.slider(
        "Volume mensuel minimal (trains prevus / mois)",
        min_value=0,
        max_value=max(10, min(500, max_prevu)),
        value=0,
        step=10,
    )

    indicateur_cible = st.sidebar.radio(
        "Indicateur principal a explorer",
        options=["taux_annulation", "taux_retard_arrivee"],
        format_func=lambda x: (
            "Taux d'annulation (%)"
            if x == "taux_annulation"
            else "Taux de retard a l'arrivee (%)"
        ),
    )
    libelle_indicateur = (
        "Taux d'annulation (%)"
        if indicateur_cible == "taux_annulation"
        else "Taux de retard a l'arrivee (%)"
    )

    try:
        df_filtre = analyseur.filtrer(
            date_debut=date_debut,
            date_fin=date_fin,
            liaisons=liaisons_choisies if liaisons_choisies else None,
            volume_min=float(volume_min),
        )
    except ErreurValidationCirculations as err:
        st.error(f"Parametre de filtrage invalide : {err}")
        return

    if df_filtre.empty:
        st.info("Aucune observation ne correspond aux filtres selectionnes.")
        return

    resume_kpi = analyseur.resume(df_filtre).iloc[0]
    df_liaisons = analyseur.agreger_par_liaison(df_filtre)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Observations (liaison-mois)",
        f"{int(resume_kpi['nb_observations']):,}".replace(",", " "),
    )
    col2.metric("Liaisons couvertes", f"{int(resume_kpi['nb_liaisons'])}")
    col3.metric(
        "Trains prevus cumules",
        f"{int(resume_kpi['total_trains_prevus']):,}".replace(",", " "),
    )
    col4.metric(
        "Taux d'annulation pondere",
        f"{resume_kpi['taux_annulation_pondere']:.2f} %",
        help="Somme des trains annules / Somme des trains prevus sur la selection.",
    )

    st.divider()

    st.subheader(
        "1. Les axes a fort volume ont-ils un taux d'annulation different ? (Volet A)"
    )
    corr_stats = analyseur.calculer_correlations_volume(
        df_liaisons, cible=indicateur_cible
    )

    fig_scatter = px.scatter(
        df_liaisons,
        x="nb_train_prevu",
        y=indicateur_cible,
        size="nb_mois",
        color="duree_moyenne",
        hover_name="liaison",
        hover_data={
            "nb_train_prevu": True,
            "nb_annulation": True,
            "taux_annulation": ":.2f",
            "taux_retard_arrivee": ":.2f",
            "nb_mois": True,
            "duree_moyenne": ":.0f",
        },
        labels={
            "nb_train_prevu": "Trains prevus cumules sur la periode",
            indicateur_cible: libelle_indicateur,
            "duree_moyenne": "Duree moy. (min)",
            "nb_mois": "Mois observes",
        },
        title=f"Volume prevu vs {libelle_indicateur} ({date_debut} a {date_fin}, n = {corr_stats['n']} liaisons)",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    if corr_stats["n"] >= 3 and pd.notna(corr_stats["spearman"]):
        st.caption(
            f"Constat statistique (n = {corr_stats['n']} liaisons) : Correlation de Spearman = "
            f"**{corr_stats['spearman']:.3f}** | Correlation de Pearson = **{corr_stats['pearson']:.3f}**. "
            "Un volume de desserte eleve est associe a davantage d'annulations en volume absolu, mais pas a une hausse systematique du taux relatif."
        )

    st.divider()

    st.subheader(
        "2. La dispersion des taux change-t-elle selon la categorie de desserte ? (Volet B)"
    )
    df_groupes = analyseur.construire_groupes_volume(df_filtre)
    groupes_dispo = sorted(df_groupes["groupe_volume"].unique())
    groupes_retenus = st.multiselect(
        "Groupes de volume a afficher",
        options=groupes_dispo,
        default=groupes_dispo,
    )
    df_groupes_aff = df_groupes[df_groupes["groupe_volume"].isin(groupes_retenus)]

    if df_groupes_aff.empty:
        st.info("Veuillez selectionner au moins un groupe de volume.")
    else:
        fig_box = px.box(
            df_groupes_aff,
            x="groupe_volume",
            y=indicateur_cible,
            color="groupe_volume",
            points="all",
            hover_name="liaison",
            hover_data=["nb_train_prevu", "nb_annulation", "nb_mois"],
            category_orders={"groupe_volume": sorted(groupes_dispo)},
            labels={
                "groupe_volume": "Categorie de desserte (tertiles de volume)",
                indicateur_cible: libelle_indicateur,
            },
            title=f"Distribution de {libelle_indicateur} par groupe de desserte ({date_debut} a {date_fin})",
        )
        st.plotly_chart(fig_box, use_container_width=True)

    st.divider()

    st.subheader(
        "3. Les liaisons souvent annulees sont-elles aussi les plus en retard ? (Volet C)"
    )
    exclure_iqr = st.checkbox(
        "Exclure les valeurs extremes d'annulation (regle de Tukey 1,5 x IQR)",
        value=False,
    )
    df_duree = analyseur.analyser_duree_et_robustesse(
        df_filtre, exclure_extremes_iqr=exclure_iqr
    )

    if df_duree.empty:
        st.info("Donnees insuffisantes pour afficher le croisement duree / retard.")
    else:
        fig_double = px.scatter(
            df_duree,
            x="taux_annulation",
            y="taux_retard_arrivee",
            color="categorie_duree",
            size="nb_train_prevu",
            hover_name="liaison",
            hover_data=[
                "nb_train_prevu",
                "trains_circules",
                "duree_moyenne",
                "nb_mois",
            ],
            labels={
                "taux_annulation": "Taux d'annulation pondere (%)",
                "taux_retard_arrivee": "Taux de retard a l'arrivee sur trains circules (%)",
                "categorie_duree": "Tranche de duree",
            },
            title=f"Croisement Taux d'annulation vs Taux de retard selon la duree ({len(df_duree)} liaisons)",
        )
        st.plotly_chart(fig_double, use_container_width=True)

    st.divider()

    st.subheader("Comparateur personnalise (2 a 5 liaisons) et Export CSV")
    defaut_comp = df_liaisons["liaison"].head(min(3, len(df_liaisons))).tolist()
    liaisons_comp = st.multiselect(
        "Choisissez entre 2 et 5 liaisons a comparer directement",
        options=df_liaisons["liaison"].tolist(),
        default=defaut_comp,
        max_selections=5,
    )

    if len(liaisons_comp) >= 2:
        df_comp = df_liaisons[df_liaisons["liaison"].isin(liaisons_comp)]
        fig_comp = px.bar(
            df_comp,
            x="liaison",
            y=["taux_annulation", "taux_retard_arrivee"],
            barmode="group",
            hover_data=[
                "nb_train_prevu",
                "nb_annulation",
                "trains_circules",
                "nb_mois",
            ],
            labels={
                "value": "Taux pondere (%)",
                "liaison": "Liaison",
                "variable": "Indicateur",
            },
            title="Comparaison directe des taux ponderes sur les liaisons selectionnees",
        )
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.caption(
            "Selectionnez au moins 2 liaisons ci-dessus pour afficher le graphique comparatif."
        )

    st.dataframe(df_liaisons, use_container_width=True)

    csv_octets = df_liaisons.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Exporter les resultats filtres (CSV avec denominateurs)",
        data=csv_octets,
        file_name=f"railinsight_circulations_{date_debut}_{date_fin}.csv",
        mime="text/csv",
    )

    st.caption(
        "Source : SNCF Open Data — Regularite mensuelle TGV par liaisons. "
        "Documentation methodologique : voir `docs/analyses/circulations.md`."
    )


if __name__ == "__main__":
    afficher_page_circulations()
