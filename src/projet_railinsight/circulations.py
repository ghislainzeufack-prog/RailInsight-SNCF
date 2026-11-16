"""Module d'analyse des circulations, annulations et retards TGV.

Ce module fournit la classe ``AnalyseCirculations`` ainsi que l'exception metier
``ErreurValidationCirculations`` pour valider, filtrer et agreger les donnees
de regularite mensuelle TGV de la SNCF sans modifier le DataFrame d'origine.
"""

from __future__ import annotations

from collections.abc import Sequence
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COLONNES_REQUISES: tuple[str, ...] = (
    "date",
    "gare_depart",
    "gare_arrivee",
    "nb_train_prevu",
    "nb_annulation",
    "nb_train_retard_arrivee",
    "duree_moyenne",
)

MAPPING_COLONNES_BRUTES: dict[str, str] = {
    "Date": "date",
    "Gare de départ": "gare_depart",
    "Gare d'arrivée": "gare_arrivee",
    "Nombre de circulations prévues": "nb_train_prevu",
    "Nombre de trains annulés": "nb_annulation",
    "Nombre de trains en retard à l'arrivée": "nb_train_retard_arrivee",
    "Durée moyenne du trajet": "duree_moyenne",
}


class ErreurValidationCirculations(ValueError):
    """Exception levee lorsqu'une entree ou un filtre metier est invalide."""


class CompteurObservations:
    """Compte des observations valides (exercice pedagogique POO du TP).

    Parameters
    ----------
    nombre_initial : int, default 0
        Valeur initiale du compteur (doit etre superieure ou egale a 0).

    Raises
    ------
    ValueError
        Si ``nombre_initial`` est strictement negatif.
    """

    def __init__(self, nombre_initial: int = 0) -> None:
        if nombre_initial < 0:
            raise ValueError("Le nombre initial d'observations ne peut pas etre negatif.")
        self._total: int = int(nombre_initial)

    @property
    def total(self) -> int:
        """Retourne le nombre total d'observations comptabilisees."""
        return self._total

    def augmenter(self, quantite: int) -> None:
        """Ajoute un nombre positif d'observations au compteur.

        Parameters
        ----------
        quantite : int
            Nombre d'observations a ajouter (doit etre >= 0).

        Raises
        ------
        ValueError
            Si ``quantite`` est negative.
        """
        if quantite < 0:
            raise ValueError("La quantite a ajouter ne peut pas etre negative.")
        self._total += int(quantite)


class AnalyseCirculations:
    """Encapsule l'etat valide et les calculs d'annulations et de retards TGV.

    Parameters
    ----------
    donnees : pd.DataFrame
        Jeu de donnees mensuel par liaison (colonnes standardisees ou brutes SNCF).

    Raises
    ------
    ErreurValidationCirculations
        Si ``donnees`` n'est pas un DataFrame ou s'il manque des colonnes requises.
    """

    def __init__(self, donnees: pd.DataFrame) -> None:
        if not isinstance(donnees, pd.DataFrame):
            logger.error("Entree invalide fournie a AnalyseCirculations : type=%s", type(donnees))
            raise ErreurValidationCirculations("L'argument 'donnees' doit etre un pandas DataFrame.")

        copie = donnees.copy(deep=True).rename(columns=MAPPING_COLONNES_BRUTES)

        colonnes_manquantes = [col for col in COLONNES_REQUISES if col not in copie.columns]
        if colonnes_manquantes:
            logger.error("Colonnes obligatoires manquantes : %s", colonnes_manquantes)
            raise ErreurValidationCirculations(
                f"Colonnes obligatoires manquantes : {', '.join(colonnes_manquantes)}"
            )

        for col_num in ("nb_train_prevu", "nb_annulation", "nb_train_retard_arrivee", "duree_moyenne"):
            copie[col_num] = pd.to_numeric(copie[col_num], errors="coerce")

        copie["date"] = copie["date"].astype(str).str.strip()
        copie["gare_depart"] = copie["gare_depart"].astype(str).str.strip()
        copie["gare_arrivee"] = copie["gare_arrivee"].astype(str).str.strip()
        copie["liaison"] = copie["gare_depart"] + " -> " + copie["gare_arrivee"]
        copie["trains_circules"] = copie["nb_train_prevu"] - copie["nb_annulation"]

        masque_valide = (
            copie["nb_train_prevu"].notna()
            & copie["nb_annulation"].notna()
            & (copie["nb_train_prevu"] > 0)
            & (copie["nb_annulation"] >= 0)
            & (copie["trains_circules"] >= 0)
            & (
                copie["nb_train_retard_arrivee"].isna()
                | (
                    (copie["nb_train_retard_arrivee"] >= 0)
                    & (copie["nb_train_retard_arrivee"] <= copie["trains_circules"])
                )
            )
        )

        nb_invalides = int((~masque_valide).sum())
        if nb_invalides > 0:
            logger.warning(
                "Diagnostic circulations : %d lignes incoherentes detectees sur %d.",
                nb_invalides,
                len(copie),
            )

        copie["est_valide"] = masque_valide
        copie["taux_annulation"] = np.where(
            copie["est_valide"],
            (copie["nb_annulation"] / copie["nb_train_prevu"]) * 100.0,
            np.nan,
        )
        copie["taux_retard_arrivee"] = np.where(
            copie["est_valide"] & (copie["trains_circules"] > 0) & copie["nb_train_retard_arrivee"].notna(),
            (copie["nb_train_retard_arrivee"] / copie["trains_circules"]) * 100.0,
            np.nan,
        )

        self._donnees_brutes: pd.DataFrame = copie
        logger.debug("AnalyseCirculations initialisee avec %d lignes.", len(copie))

    @property
    def donnees(self) -> pd.DataFrame:
        """Retourne une copie des donnees enrichies (garantit l'encapsulation)."""
        return self._donnees_brutes.copy(deep=True)

    def diagnostic_qualite(self) -> dict[str, int]:
        """Retourne un bilan chiffre des anomalies detectees dans le jeu de donnees."""
        df = self._donnees_brutes
        return {
            "total_lignes": int(len(df)),
            "lignes_valides": int(df["est_valide"].sum()),
            "lignes_invalides": int((~df["est_valide"]).sum()),
            "prevu_nul_ou_negatif": int((df["nb_train_prevu"] <= 0).sum()),
            "annulations_superieures_au_prevu": int((df["trains_circules"] < 0).sum()),
            "trains_circules_nuls": int((df["trains_circules"] == 0).sum()),
            "retards_superieurs_aux_circules": int(
                ((df["trains_circules"] >= 0) & (df["nb_train_retard_arrivee"] > df["trains_circules"])).sum()
            ),
        }

    def filtrer(
        self,
        date_debut: str | None = None,
        date_fin: str | None = None,
        liaisons: Sequence[str] | None = None,
        volume_min: float = 0.0,
        exclure_invalides: bool = True,
    ) -> pd.DataFrame:
        """Filtre les observations liaison-mois selon les criteres de l'utilisateur."""
        if volume_min < 0:
            logger.error("Filtre invalide : volume_min negatif (%s)", volume_min)
            raise ErreurValidationCirculations("Le volume minimal ne peut pas etre negatif.")

        if date_debut and date_fin and date_debut > date_fin:
            logger.error("Filtre de periode invalide : %s > %s", date_debut, date_fin)
            raise ErreurValidationCirculations(
                "La date de debut ne peut pas etre posterieure a la date de fin."
            )

        df = self._donnees_brutes.copy(deep=True)
        if exclure_invalides:
            df = df[df["est_valide"]]

        if date_debut:
            df = df[df["date"] >= str(date_debut)]
        if date_fin:
            df = df[df["date"] <= str(date_fin)]
        if liaisons is not None and len(liaisons) > 0:
            df = df[df["liaison"].isin(liaisons)]
        if volume_min > 0:
            df = df[df["nb_train_prevu"] >= volume_min]

        logger.debug("Filtrage effectue : %d lignes retenues.", len(df))
        return df.reset_index(drop=True)

    def resume(self, donnees_filtrees: pd.DataFrame | None = None) -> pd.DataFrame:
        """Calcule un tableau synthetique d'indicateurs globaux sur le perimetre retenu."""
        df = self.filtrer() if donnees_filtrees is None else donnees_filtrees
        if df.empty:
            return pd.DataFrame(
                [
                    {
                        "nb_observations": 0,
                        "nb_liaisons": 0,
                        "total_trains_prevus": 0,
                        "total_annulations": 0,
                        "total_trains_circules": 0,
                        "taux_annulation_pondere": np.nan,
                        "taux_retard_pondere": np.nan,
                    }
                ]
            )

        total_prevu = float(df["nb_train_prevu"].sum())
        total_annul = float(df["nb_annulation"].sum())
        total_circules = float(df["trains_circules"].sum())
        total_retard = float(df["nb_train_retard_arrivee"].dropna().sum())

        taux_annul = (total_annul / total_prevu * 100.0) if total_prevu > 0 else np.nan
        taux_retard = (total_retard / total_circules * 100.0) if total_circules > 0 else np.nan

        return pd.DataFrame(
            [
                {
                    "nb_observations": int(len(df)),
                    "nb_liaisons": int(df["liaison"].nunique()),
                    "total_trains_prevus": int(total_prevu),
                    "total_annulations": int(total_annul),
                    "total_trains_circules": int(total_circules),
                    "taux_annulation_pondere": taux_annul,
                    "taux_retard_pondere": taux_retard,
                }
            ]
        )

    def agreger_par_liaison(
        self,
        donnees_filtrees: pd.DataFrame | None = None,
        min_mois: int = 1,
    ) -> pd.DataFrame:
        """Agrege les indicateurs par liaison en sommant numerateurs et denominateurs."""
        if min_mois < 1:
            raise ErreurValidationCirculations("Le parametre 'min_mois' doit etre superieur ou egal a 1.")

        df = self.filtrer() if donnees_filtrees is None else donnees_filtrees
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "liaison",
                    "gare_depart",
                    "gare_arrivee",
                    "nb_mois",
                    "nb_train_prevu",
                    "nb_annulation",
                    "trains_circules",
                    "nb_train_retard_arrivee",
                    "duree_moyenne",
                    "taux_annulation",
                    "taux_retard_arrivee",
                ]
            )

        agg = df.groupby(["liaison", "gare_depart", "gare_arrivee"], as_index=False).agg(
            nb_mois=("date", "count"),
            nb_train_prevu=("nb_train_prevu", "sum"),
            nb_annulation=("nb_annulation", "sum"),
            trains_circules=("trains_circules", "sum"),
            nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
            duree_moyenne=("duree_moyenne", "mean"),
        )
        agg = agg[agg["nb_mois"] >= min_mois].copy()
        if agg.empty:
            return agg.assign(
                taux_annulation=pd.Series(dtype=float),
                taux_retard_arrivee=pd.Series(dtype=float),
            )

        agg["taux_annulation"] = np.where(
            agg["nb_train_prevu"] > 0,
            (agg["nb_annulation"] / agg["nb_train_prevu"]) * 100.0,
            np.nan,
        )
        agg["taux_retard_arrivee"] = np.where(
            agg["trains_circules"] > 0,
            (agg["nb_train_retard_arrivee"] / agg["trains_circules"]) * 100.0,
            np.nan,
        )
        return agg.sort_values("nb_train_prevu", ascending=False).reset_index(drop=True)

    def calculer_correlations_volume(
        self,
        donnees_table: pd.DataFrame | None = None,
        cible: str = "taux_annulation",
    ) -> dict[str, float | int]:
        """Calcule les correlations de Pearson et Spearman entre le volume prevu et un taux cible."""
        df = self.agreger_par_liaison() if donnees_table is None else donnees_table
        if cible not in ("taux_annulation", "taux_retard_arrivee"):
            raise ErreurValidationCirculations(f"Indicateur cible non reconnu : {cible}")

        if df.empty or "nb_train_prevu" not in df.columns or cible not in df.columns:
            return {"n": 0, "pearson": np.nan, "spearman": np.nan}

        sous_df = df[["nb_train_prevu", cible]].dropna()
        n_obs = len(sous_df)
        if n_obs < 3 or sous_df["nb_train_prevu"].nunique() < 2 or sous_df[cible].nunique() < 2:
            return {"n": int(n_obs), "pearson": np.nan, "spearman": np.nan}

        return {
            "n": int(n_obs),
            "pearson": float(sous_df["nb_train_prevu"].corr(sous_df[cible], method="pearson")),
            "spearman": float(sous_df["nb_train_prevu"].corr(sous_df[cible], method="spearman")),
        }

    def construire_groupes_volume(
        self,
        donnees_filtrees: pd.DataFrame | None = None,
        volume_min_liaison: float = 0.0,
    ) -> pd.DataFrame:
        """Classe les liaisons agregees en 3 groupes de desserte (quantiles) pour l'Analyse B."""
        if volume_min_liaison < 0:
            raise ErreurValidationCirculations("Le volume minimal par liaison ne peut pas etre negatif.")

        agg = self.agreger_par_liaison(donnees_filtrees)
        agg = agg[agg["nb_train_prevu"] >= volume_min_liaison].copy()
        if agg.empty:
            agg["groupe_volume"] = pd.Series(dtype="object")
            return agg

        labels = ["1. Faible desserte", "2. Desserte moyenne", "3. Forte desserte"]
        if agg["nb_train_prevu"].nunique() >= 3:
            agg["groupe_volume"] = pd.qcut(
                agg["nb_train_prevu"], q=3, labels=labels, duplicates="drop"
            ).astype(str)
        else:
            agg["groupe_volume"] = "Volume homogene"

        return agg.reset_index(drop=True)

    def analyser_duree_et_robustesse(
        self,
        donnees_filtrees: pd.DataFrame | None = None,
        exclure_extremes_iqr: bool = False,
    ) -> pd.DataFrame:
        """Prepare les donnees par liaison avec categories de duree et filtre IQR optionnel (Analyse C)."""
        agg = self.agreger_par_liaison(donnees_filtrees)
        agg = agg[agg["duree_moyenne"].notna() & (agg["duree_moyenne"] > 0)].copy()
        if agg.empty:
            agg["categorie_duree"] = pd.Series(dtype="object")
            return agg

        if exclure_extremes_iqr and len(agg) >= 4:
            q1 = agg["taux_annulation"].quantile(0.25)
            q3 = agg["taux_annulation"].quantile(0.75)
            iqr = q3 - q1
            seuil_haut = q3 + 1.5 * iqr
            agg = agg[agg["taux_annulation"] <= seuil_haut].copy()

        bornes = [0.0, 90.0, 150.0, 210.0, np.inf]
        etiquettes = ["Court (< 1h30)", "Moyen (1h30 - 2h30)", "Long (2h30 - 3h30)", "Tres long (> 3h30)"]
        agg["categorie_duree"] = pd.cut(
            agg["duree_moyenne"], bins=bornes, labels=etiquettes, right=False
        ).astype(str)
        return agg.reset_index(drop=True)
