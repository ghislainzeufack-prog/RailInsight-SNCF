"""Analyse de la saisonnalité, dans l’ordre du notebook Analyse 1."""

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy.engine import Engine

if __package__:
    from .moteur_sql import executer_requete
else:
    from moteur_sql import executer_requete


INDICATEURS = [
    "total_annulation",
    "total_retard_depart",
    "total_retard_arrivee",
]


# %% I. Base de données

def charger_donnees_mensuelles(
    engine: Engine,
    *,
    nettoyage: bool = True,
    service: str | None = "National",
    annee_debut: int | None = None,
    annee_fin: int | None = None,
) -> pd.DataFrame:
    """Lire les totaux mensuels et ajouter année, mois et pourcentages.

    Les dates SQL sont au format YYYY-MM. Les bornes sont inclusives.
    service=None sélectionne tous les services. En mode nettoyage, la lecture
    utilise la vue regularite_tgv_clean créée avec les règles du notebook.

    Les taux utilisent uniquement les lignes dont les deux valeurs sont
    connues, avec un volume prévu strictement positif. Le taux de perturbation
    additionne annulations et retards au départ, jamais départ et arrivée.
    Les valeurs inconnues ne sont pas remplacées par zéro.
    """
    for annee in (annee_debut, annee_fin):
        if annee is not None and (type(annee) is not int or not 1 <= annee <= 9999):
            raise ValueError("Les années doivent être des entiers entre 1 et 9999.")
    if (
        annee_debut is not None
        and annee_fin is not None
        and annee_debut > annee_fin
    ):
        raise ValueError("annee_debut doit être inférieure ou égale à annee_fin.")

    table = "regularite_tgv_clean" if nettoyage else "regularite_tgv"

    requete = f"""
        WITH donnees AS (
            SELECT *,
                nb_circulation_prevues > 0
                    AND nb_annulation IS NOT NULL AS annulation_connue,
                nb_circulation_prevues > 0
                    AND nb_train_depart_retard IS NOT NULL AS depart_connu,
                nb_circulation_prevues > 0
                    AND nb_train_retard_arrivee IS NOT NULL AS arrivee_connue
            FROM {table}
            WHERE (CAST(? AS TEXT) IS NULL OR service = ?)
              AND date BETWEEN ? AND ?
        )
        SELECT
            date,
            SUM(nb_annulation) AS total_annulation,
            SUM(nb_train_depart_retard) AS total_retard_depart,
            SUM(nb_train_retard_arrivee) AS total_retard_arrivee,
            SUM(nb_circulation_prevues) AS total_circulations_prevues,
            COUNT(*) AS nb_lignes,
            COUNT(*) - COUNT(nb_annulation) AS nb_annulations_manquantes,

            -- Pour chaque taux, garder les mêmes lignes au numérateur
            -- et au dénominateur. NULLIF évite la division par zéro.
            100.0 * SUM(nb_annulation) FILTER (WHERE annulation_connue)
                / NULLIF(SUM(nb_circulation_prevues)
                    FILTER (WHERE annulation_connue), 0) AS taux_annulation,

            100.0 * SUM(nb_train_depart_retard) FILTER (WHERE depart_connu)
                / NULLIF(SUM(nb_circulation_prevues)
                    FILTER (WHERE depart_connu), 0) AS taux_retard_depart,

            100.0 * SUM(nb_train_retard_arrivee) FILTER (WHERE arrivee_connue)
                / NULLIF(SUM(nb_circulation_prevues)
                    FILTER (WHERE arrivee_connue), 0) AS taux_retard_arrivee,

            100.0 * SUM(nb_annulation + nb_train_depart_retard)
                    FILTER (WHERE annulation_connue AND depart_connu)
                / NULLIF(SUM(nb_circulation_prevues)
                    FILTER (WHERE annulation_connue AND depart_connu), 0)
                AS taux_perturbation_depart
        FROM donnees
        GROUP BY date
        ORDER BY date;
    """

    parametres = [
        service,
        service,
        f"{annee_debut:04d}-01" if annee_debut else "0001-01",
        f"{annee_fin:04d}-12" if annee_fin else "9999-12",
    ]

    data = executer_requete(engine, requete, parametres)
    return preparer_donnees(data)


def preparer_donnees(data: pd.DataFrame) -> pd.DataFrame:
    """Convertir la date et extraire l’année et le mois."""
    data = data.copy()
    data["date"] = pd.to_datetime(data["date"], format="%Y-%m")
    data["annee"] = data["date"].dt.year
    data["mois"] = data["date"].dt.month
    return data


# %% I.1. Description


def decrire_donnees(data: pd.DataFrame) -> dict:
    """Aperçu et statistiques descriptives des données mensuelles."""
    return {"apercu": data.head(), "statistiques": data.describe()}


# %% I.2. Visualisation de corrélation et comparaison par année


def tracer_evolution(data: pd.DataFrame):
    """Courbes des annulations et retards au fil du temps."""
    from matplotlib.figure import Figure

    figure = Figure(figsize=(12, 9))
    for axe, indicateur in zip(figure.subplots(3, 1), INDICATEURS):
        axe.plot(data["date"], data[indicateur])
        axe.set(title=indicateur, xlabel="Date", ylabel="Nombre de trains")
        axe.grid(alpha=0.3)
    figure.tight_layout()
    return figure


def tracer_comparaison_annuelle(
    data: pd.DataFrame, indicateur: str = "total_annulation"
):
    """Comparer les mois de chaque année, comme dans le notebook."""
    from matplotlib.figure import Figure

    if indicateur not in INDICATEURS:
        raise ValueError(f"Choisir un indicateur parmi {INDICATEURS}.")
    figure = Figure(figsize=(12, 6))
    axe = figure.subplots()
    for annee, groupe in data.groupby("annee"):
        # Les mois absents restent des trous dans les courbes.
        valeurs = groupe.set_index("mois")[indicateur].reindex(range(1, 13))
        axe.plot(valeurs.index, valeurs, label=str(annee))
    axe.set(title=indicateur, xlabel="Mois", ylabel="Nombre de trains")
    axe.set_xticks(range(1, 13))
    if not data.empty:
        axe.legend(title="Année")
    axe.grid(alpha=0.3)
    return figure


# %% I.3. Tableau de corrélation


def calculer_correlations(data: pd.DataFrame) -> pd.DataFrame:
    """Matrice de corrélation, sans la colonne date."""
    return data[["annee", "mois", *INDICATEURS]].corr()


def tracer_correlations(data: pd.DataFrame):
    """Heatmap de la matrice de corrélation."""
    from matplotlib.figure import Figure
    import seaborn as sns

    figure = Figure(figsize=(8, 6))
    sns.heatmap(
        calculer_correlations(data),
        annot=True,
        vmin=-1,
        vmax=1,
        cmap="coolwarm",
        ax=figure.subplots(),
    )
    figure.tight_layout()
    return figure


# %% II. Régression linéaire multiple


def calculer_regression(data: pd.DataFrame) -> dict:
    """Estimer retards au départ ~ constante + mois + annulations.

    Reproduit le modèle exploratoire du notebook (mois numérique, non cyclique).
    Les lignes incomplètes sont exclues. Les résultats décrivent des associations,
    sans établir de causalité. Les erreurs standards supposent des résidus iid.
    """
    valeurs = data[["mois", "total_annulation", "total_retard_depart"]]
    valeurs = valeurs.replace([np.inf, -np.inf], np.nan).dropna()
    x = np.column_stack(
        [np.ones(len(valeurs)), valeurs.iloc[:, :2].to_numpy(dtype=float)]
    )
    y = valeurs["total_retard_depart"].to_numpy(dtype=float)
    if len(y) <= 3 or np.linalg.matrix_rank(x) < 3:
        return {
            "disponible": False,
            "raison": (
                "Il faut plus de 3 observations complètes "
                "et des variables non colinéaires."
            ),
        }

    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    predictions = x @ beta
    residus = y - predictions

    ddl = len(y) - x.shape[1]  # La constante est déjà incluse dans X.
    covariance = (residus @ residus / ddl) * (np.linalg.pinv(x) @ np.linalg.pinv(x).T)
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    t = np.divide(beta, se, out=np.full(3, np.nan), where=se > 0)

    coefficients = pd.DataFrame(
        {
            "coefficient": beta,
            "erreur_standard": se,
            "t": t,
            "p_value": 2 * stats.t.sf(np.abs(t), ddl),
        },
        index=["constante", "mois", "annulations"],
    )

    observations = data.loc[valeurs.index, ["date"]].copy()
    observations["observe"] = y
    observations["prediction"] = predictions
    observations["residu"] = residus

    sst = np.sum((y - y.mean()) ** 2)
    return {
        "disponible": True,
        "coefficients": coefficients,
        "observations": observations,
        "n_observations": len(y),
        "ddl": ddl,
        "r2": float(1 - residus @ residus / sst) if sst > 0 else float("nan"),
    }


# %% II.1. Histogramme des résidus


def tracer_residus(regression: dict):
    """Histogramme des résidus observés moins prédits."""
    from matplotlib.figure import Figure

    if not regression["disponible"]:
        raise ValueError(regression["raison"])
    figure = Figure(figsize=(8, 5))
    axe = figure.subplots()
    axe.hist(regression["observations"]["residu"], bins=20)
    axe.set(title="Distribution des résidus", xlabel="Résidu", ylabel="Effectif")
    return figure


# %% Utilisation dans Streamlit


def analyser_saisonnalite(engine: Engine, **filtres) -> dict:
    """Fonction principale : données SQL, saisonnalité, corrélations, régression.

    Accepte les mêmes filtres que charger_donnees_mensuelles. Les DataFrames
    renvoyés peuvent être affichés avec st.dataframe, st.line_chart ou Plotly.
    La saisonnalité est la moyenne des totaux de chaque mois sur les années
    sélectionnées ; elle dépend donc du volume de circulation de ces années.
    """
    data = charger_donnees_mensuelles(engine, **filtres)
    return {
        "mensuel": data,
        "description": decrire_donnees(data),
        "saisonnalite": data.groupby("mois")[INDICATEURS].mean(),
        "correlations": calculer_correlations(data),
        "regression": calculer_regression(data),
    }


# %% Test manuel


def tester_analyse(engine: Engine, **filtres) -> dict:
    """Tester la connexion SQL et afficher les résultats de l’analyse."""
    resultats = analyser_saisonnalite(engine, **filtres)
    data = resultats["mensuel"]
    if data.empty:
        raise ValueError("Aucune donnée trouvée pour les filtres sélectionnés.")

    print(f"Connexion SQL OK — {len(data)} mois chargés.")
    print("\n1. Aperçu des données")
    print(resultats["description"]["apercu"].to_string(index=False))
    print("\n2. Saisonnalité")
    print(resultats["saisonnalite"])
    print("\n3. Corrélations")
    print(resultats["correlations"])
    print("\n4. Régression")
    regression = resultats["regression"]
    if regression["disponible"]:
        print(regression["coefficients"])
        print(f"R² = {regression['r2']:.4f}")
    else:
        print(regression["raison"])
    return resultats


if __name__ == "__main__":
    if __package__:
        from .moteur_sql import creer_connexion
    else:
        from moteur_sql import creer_connexion

    engine = creer_connexion()
    try:
        tester_analyse(engine)
    finally:
        engine.dispose()
