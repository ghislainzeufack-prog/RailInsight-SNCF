"""Tableau de bord Streamlit : persistance des retards TGV."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from projet_railinsight.common_processing import charger_donnees
from projet_railinsight.data_processing import calculer_taux_mensuel
from projet_railinsight.persistence import (
    estimer_ar1,
    evaluer_previsions,
    prevoir_naif,
)

st.set_page_config(
    page_title="RailInsight - Persistance des retards",
    page_icon="🚄",
    layout="wide",
)

st.title("🚄 RailInsight-SNCF")
st.subheader("Analyse de la persistance des retards TGV")

st.write(
    "Étude de l'évolution mensuelle des retards de plus de "
    "15 minutes et comparaison de modèles de prévision."
)


@st.cache_data
def charger_serie_mensuelle():
    """Charge et prépare les taux mensuels de retard."""
    chemin = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "raw"
        / "regularite-mensuelle-tgv-aqst.csv"
    )

    df = charger_donnees(chemin)
    mensuel = calculer_taux_mensuel(df)

    serie = mensuel["taux_retard_15min"].dropna().sort_index()

    return df, serie


try:
    donnees, serie = charger_serie_mensuelle()
except (FileNotFoundError, ValueError, KeyError) as erreur:
    st.error(f"Impossible de préparer les données : {erreur}")
    st.stop()

if len(serie) < 15:
    st.error("La série est trop courte pour réaliser cette analyse.")
    st.stop()


# ---------------------------------------------------------
# 1. Vue d'ensemble
# ---------------------------------------------------------

st.divider()
st.header("1. Vue d'ensemble")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Observations SNCF", f"{len(donnees):,}".replace(",", " "))
col2.metric("Mois étudiés", len(serie))

col3.metric(
    "Moyenne des taux mensuels (+15 min)",
    f"{serie.mean():.2f} %",
)

col4.metric(
    "Taux de retard — dernier mois",
    f"{serie.iloc[-1]:.2f} %",
)

st.caption(f"Période : {serie.index.min():%m/%Y} à {serie.index.max():%m/%Y}")

st.caption(
    "Le taux moyen correspond à la moyenne arithmétique "
    "des taux mensuels de retard de plus de 15 minutes. "
    "Chaque mois possède le même poids dans ce calcul."
)


# ---------------------------------------------------------
# 2. Évolution mensuelle des retards
# ---------------------------------------------------------

st.divider()
st.header("2. Évolution mensuelle des retards")

st.write(
    "Le taux mensuel est calculé en rapportant le nombre "
    "de trains en retard de plus de 15 minutes au nombre "
    "de trains effectivement réalisés."
)

graphique = go.Figure()

graphique.add_trace(
    go.Scatter(
        x=serie.index,
        y=serie.values,
        mode="lines+markers",
        name="Taux de retard",
        line={"color": "#2563EB", "width": 2},
        marker={"size": 4},
        hovertemplate=(
            "Mois : %{x|%m/%Y}<br>Taux de retard : %{y:.2f} %<extra></extra>"
        ),
    )
)

graphique.update_layout(
    title="Évolution du taux mensuel de retard des TGV",
    xaxis_title="Mois",
    yaxis_title="Taux de retard (%)",
    hovermode="x unified",
    height=450,
    margin={"l": 20, "r": 20, "t": 60, "b": 20},
)

graphique.update_xaxes(
    tickformat="%m/%Y",
    dtick="M12",
    showgrid=True,
)

graphique.update_yaxes(
    ticksuffix=" %",
    rangemode="tozero",
)

st.plotly_chart(graphique, width="stretch")

st.info(
    "Une augmentation du taux indique une proportion plus "
    "importante de trains arrivant avec plus de 15 minutes de retard."
)


# ---------------------------------------------------------
# 3. Modèle de persistance AR(1)
# ---------------------------------------------------------

st.divider()
st.header("3. Analyse de la persistance")

horizon_test = 12

serie_train = serie.iloc[:-horizon_test]
serie_test = serie.iloc[-horizon_test:]

try:
    resultat_ar1 = estimer_ar1(pd.Series(serie_train.to_numpy(), dtype=float))
except (ValueError, TypeError) as erreur:
    st.error(f"Erreur lors de l'estimation AR(1) : {erreur}")
    st.stop()

constante = float(resultat_ar1.params.iloc[0])
phi = float(resultat_ar1.params.iloc[1])

col1, col2 = st.columns(2)

col1.metric("Coefficient de persistance φ", f"{phi:.3f}")
col2.metric("Constante estimée", f"{constante:.3f}")

st.latex(r"R_t = c + \phi R_{t-1} + \varepsilon_t")

if 0 < phi < 1:
    st.write(
        "Le coefficient positif indique une persistance des retards : "
        "un mois avec un taux élevé tend à être suivi d'un mois "
        "également relativement élevé. Comme φ est inférieur à 1, "
        "l'effet d'un choc décroît au fil du temps."
    )
elif phi == 0:
    st.write(
        "Le coefficient estimé est nul : le modèle ne met pas "
        "en évidence de dépendance linéaire au mois précédent."
    )
elif -1 < phi < 0:
    st.write(
        "Le coefficient négatif indique une tendance à l'alternance "
        "des écarts entre mois successifs."
    )
else:
    st.warning(
        "Le coefficient estimé se situe en dehors de l'intervalle "
        "de stationnarité usuel de l'AR(1). Son interprétation "
        "nécessite des précautions."
    )


# ---------------------------------------------------------
# 4. Prévisions et comparaison
# ---------------------------------------------------------

st.divider()
st.header("4. Comparaison des prévisions")

st.write(
    "Les modèles sont évalués sur les 12 derniers mois. "
    "Chaque prévision utilise le taux réellement observé "
    "le mois précédent."
)

valeurs_precedentes = serie.shift(1).loc[serie_test.index]

pred_ar1 = pd.Series(
    constante + phi * valeurs_precedentes.to_numpy(),
    index=serie_test.index,
    name="AR(1)",
)

pred_naif = prevoir_naif(serie).loc[serie_test.index]

scores_ar1 = evaluer_previsions(serie_test, pred_ar1)
scores_naif = evaluer_previsions(serie_test, pred_naif)

comparaison = pd.DataFrame(
    {
        "Observé": serie_test,
        "AR(1)": pred_ar1,
        "Naïf": pred_naif,
    }
)

fig_previsions = go.Figure()

fig_previsions.add_trace(
    go.Scatter(
        x=comparaison.index,
        y=comparaison["Observé"],
        mode="lines+markers",
        name="Taux observé",
        line={"color": "#2563EB", "width": 3},
        marker={"size": 7},
        hovertemplate=("Mois : %{x|%m/%Y}<br>Observé : %{y:.2f} %<extra></extra>"),
    )
)

fig_previsions.add_trace(
    go.Scatter(
        x=comparaison.index,
        y=comparaison["AR(1)"],
        mode="lines+markers",
        name="Prévision AR(1)",
        line={"color": "#EA580C", "width": 2, "dash": "dash"},
        marker={"size": 6},
        hovertemplate=("Mois : %{x|%m/%Y}<br>AR(1) : %{y:.2f} %<extra></extra>"),
    )
)

fig_previsions.add_trace(
    go.Scatter(
        x=comparaison.index,
        y=comparaison["Naïf"],
        mode="lines+markers",
        name="Prévision naïve",
        line={"color": "#16A34A", "width": 2, "dash": "dot"},
        marker={"size": 6},
        hovertemplate=("Mois : %{x|%m/%Y}<br>Naïf : %{y:.2f} %<extra></extra>"),
    )
)

fig_previsions.update_layout(
    title="Comparaison des prévisions sur la période de test",
    xaxis_title="Mois",
    yaxis_title="Taux de retard (%)",
    hovermode="x unified",
    legend={
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "left",
        "x": 0,
    },
    height=450,
    margin={"l": 20, "r": 20, "t": 90, "b": 20},
)

fig_previsions.update_xaxes(
    tickformat="%m/%Y",
    dtick="M1",
    tickangle=-45,
)

fig_previsions.update_yaxes(
    ticksuffix=" %",
    rangemode="tozero",
)

st.plotly_chart(fig_previsions, width="stretch")


# ---------------------------------------------------------
# Performances des modèles
# ---------------------------------------------------------

resultats = pd.DataFrame(
    {
        "Modèle": ["AR(1)", "Naïf"],
        "MAE": [scores_ar1["MAE"], scores_naif["MAE"]],
        "RMSE": [scores_ar1["RMSE"], scores_naif["RMSE"]],
    }
)

st.subheader("Performances des modèles")

st.dataframe(
    resultats.style.format({"MAE": "{:.3f}", "RMSE": "{:.3f}"}),
    hide_index=True,
    width="stretch",
)

meilleur_mae = resultats.loc[resultats["MAE"].idxmin(), "Modèle"]

meilleur_rmse = resultats.loc[resultats["RMSE"].idxmin(), "Modèle"]

st.write(f"**Meilleur modèle selon la MAE :** {meilleur_mae}")
st.write(f"**Meilleur modèle selon la RMSE :** {meilleur_rmse}")

st.caption(
    "MAE et RMSE sont exprimées en points de pourcentage. "
    "Une valeur plus faible indique une meilleure précision."
)


# ---------------------------------------------------------
# 5. Conclusion
# ---------------------------------------------------------

st.divider()
st.header("5. Conclusion")

st.write(
    "L'analyse AR(1) permet de quantifier la dépendance "
    "entre les taux de retard de deux mois consécutifs."
)

if meilleur_mae == meilleur_rmse:
    st.write(
        f"Sur la période de test, le modèle {meilleur_mae} "
        "obtient les erreurs de prévision les plus faibles "
        "selon les deux indicateurs."
    )
else:
    st.write(
        "Les critères MAE et RMSE ne désignent pas le même "
        "modèle comme le plus performant."
    )

st.warning(
    "Ces résultats décrivent une dépendance statistique "
    "et ne démontrent pas une relation causale. "
    "Ils dépendent également de la période étudiée."
)

st.caption("Projet RailInsight-SNCF — Analyse de la persistance des retards TGV")
