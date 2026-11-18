"""Ce module analyse les causes de retard sur les observations mensuelles par liaison
à la SNCF
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import pandas as pd

LOGGER = logging.getLogger(__name__)

# Colonnes utilisees pour notre module
# On definit des tuples au lieu des listes car c'est suppose fixe
COLONNES_CAUSES = (
    "Prct retard pour causes externes",
    "Prct retard pour cause infrastructure",
    "Prct retard pour cause gestion trafic",
    "Prct retard pour cause matériel roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel",
    "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)",
)
COLONNE_RETARDS = "Nombre de trains en retard à l'arrivée"
COLONNE_PREVUS = "Nombre de circulations prévues"
COLONNE_ANNULES = "Nombre de trains annulés"

# On transforme le generateur en tuple
LIBELLES_CAUSES = tuple(
    libelle.removeprefix("Prct retard pour ") for libelle in COLONNES_CAUSES
)


# On va créer une classe qui va heriter des fonctionnalites du module ValueError
class AnalyseCausesErreur(ValueError):
    """Erreur reperee lors de l'analyses des causes de retard."""


# On cree egalement une classe qui va heriter de la classe AnalyseCausesErreur
class ColonnesManquantesErreur(AnalyseCausesErreur):
    """Pour reperer le jeu de donnees ne comportant pas toute les colonnes requises"""


class AnalyseCauses:
    """Analyse et filtre la repartition des causes de retard du TGV

    Args:
        df: Donnees chargees, avec une colonne ``Date_parsed`` de type datetime

    Leve une exception si une colonne obligatoire manque lors de la creation de l'objet
    """

    TOLERANCE_POURCENTAGE = 0.1
    COLONNES_REQUISES = (
        "Date",
        "Gare de départ",
        "Gare d'arrivée",
        COLONNE_RETARDS,
        COLONNE_PREVUS,
        COLONNE_ANNULES,
        # '*' dans '*COLONNES_CAUSES' sert a decomposer le tuple pour inserer
        # ses elements individuellement dans un autre tuple
        *COLONNES_CAUSES,
    )

    def __init__(self, df: pd.DataFrame) -> None:
        """Copie les donnees et verifie la presence des colonnes obligatoires."""
        self._df = df.copy()

        # On verifie la presence des colonnes obligatoires
        self.verifier_colonnes()

        self._df["Date_parsed"] = pd.to_datetime(self._df["Date"], errors="coerce")

        for colonne in (
            COLONNE_RETARDS,
            COLONNE_PREVUS,
            COLONNE_ANNULES,
            *COLONNES_CAUSES,
        ):
            # On verifie qu'on a bien des valeurs numeriques sinon on remplace par NaN
            self._df[colonne] = pd.to_numeric(self._df[colonne], errors="coerce")

    def verifier_colonnes(self) -> None:
        """Leve une exception lorsqu'une colonne obligatoire dans les donnees est manquante."""
        manquantes = set(self.COLONNES_REQUISES) - set(self._df.columns)
        if manquantes:
            raise ColonnesManquantesErreur(
                f"Colonnes SNCF manquantes : {', '.join(sorted(manquantes))}"
            )

    def donnees(self) -> pd.DataFrame:
        """Retourne une copie des donnees"""
        return self._df.copy()

    def filtrer_periode(self, debut: str, fin: str) -> AnalyseCauses:
        """Conserve les mois compris entre debut et fin.
        Les deux bornes sont au format ``YYYY-MM``
        """

        # On verifie si 'debut' et 'fin' sont valides
        try:
            debut_mois = pd.Period(debut, freq="M")
            fin_mois = pd.Period(fin, freq="M")
        except (ValueError, TypeError) as exc:
            raise AnalyseCausesErreur("La période attend le format YYYY-MM.") from exc
        if debut_mois > fin_mois:
            raise AnalyseCausesErreur("La date de début dépasse la date de fin.")

        dates = self._df["Date_parsed"].dt.to_period("M")
        LOGGER.info("Filtre période : %s à %s", debut, fin)

        return AnalyseCauses(self._df.loc[dates.between(debut_mois, fin_mois)])

    def filtrer_liaison(self, depart: str, arrivee: str) -> AnalyseCauses:
        """Conserve le sens de circulation ``depart -> arrivee``."""
        LOGGER.info("Filtre liaison : %s -> %s", depart, arrivee)

        return AnalyseCauses(
            self._df.loc[
                self._df["Gare de départ"].eq(depart)
                & self._df["Gare d'arrivée"].eq(arrivee)
            ]
        )

    def regrouper_sens(self, depart: str, arrivee: str) -> AnalyseCauses:
        """Conserve les deux sens d'une paire de gares, sans autre liaison."""
        aller = self._df["Gare de départ"].eq(depart) & self._df["Gare d'arrivée"].eq(
            arrivee
        )
        retour = self._df["Gare de départ"].eq(arrivee) & self._df["Gare d'arrivée"].eq(
            depart
        )
        LOGGER.info("Filtre aller-retour : %s <-> %s", depart, arrivee)

        return AnalyseCauses(self._df.loc[aller | retour])

    def conserver_observations_exploitables(self) -> pd.DataFrame:
        """Conserve les observations où la somme des prct est egal a 100 +/- 0.1.
        les lignes sans retard a l'arrivee, ainsi que les valeurs manquantes sont exclues
        """

        # On selectionne les colonnes relatives aux causes
        pourcentages = self._df[list(COLONNES_CAUSES)]

        # on exclut les lignes contenant au moins une valeur manquante
        masque_complet = pourcentages.notna().all(axis=1)
        masque_bornes = pourcentages.ge(0).all(axis=1) & pourcentages.le(100).all(
            axis=1
        )

        # min_count=len(COLONNES_CAUSES) permet de s'assurer que toutes
        # toutes les cases d'une observation des colonnes selectionnees
        # ne comporte pas de valeurs manquantes, et renvoie NaN si
        # le nombre de valeurs prises pour la somme ne correpond pas
        # au nombre de colonnes dans COLONNES_CAUSES
        masque_somme_prct_valide = (
            pourcentages.sum(axis=1, min_count=len(COLONNES_CAUSES))
            .sub(100)
            .abs()
            .le(self.TOLERANCE_POURCENTAGE)
        )

        # le masque des observations ayant un nombre de trains en retard
        # a l'arrivee superieur a 0
        masque_avec_retard = self._df[COLONNE_RETARDS].gt(0)

        return self._df.loc[
            masque_complet
            & masque_bornes
            & masque_somme_prct_valide
            & masque_avec_retard
        ].copy()

    def analyser_volume(self) -> dict[str, int]:
        """Produit les observations exploitables et les effectifs
        de la selection cumulés par observation liaison-mois
        """
        exploitables = self.conserver_observations_exploitables()
        total_retards = int(self._df[COLONNE_RETARDS].sum())
        couverts = int(exploitables[COLONNE_RETARDS].sum())

        return {
            "observations": len(self._df),
            "circulations_prevues": int(self._df[COLONNE_PREVUS].sum()),
            "trains_annules": int(self._df[COLONNE_ANNULES].sum()),
            "retards_a_l_arrivee": total_retards,
            "observations_exploitables": len(exploitables),
            "retards_couverts": couverts,
            "retards_exclus": total_retards - couverts,
        }

    def repartition_causes(self) -> pd.DataFrame:
        """Compare la mediane et la moyenne ponderee par les retards a l'arrivee.

        Returns:
            Tableau : ``cause``, ``mediane_pct``, ``part_ponderee_pct``

        Leve une exception si aucune observation exploitable n'est dispobible
        """

        exploitables = self.conserver_observations_exploitables()
        if exploitables.empty:
            raise AnalyseCausesErreur(
                "Aucune observation de causes exploitable sur cette selection"
            )

        retards = exploitables[COLONNE_RETARDS]
        pourcentages = exploitables[list(COLONNES_CAUSES)]
        resultat = pd.DataFrame(
            {
                "cause": LIBELLES_CAUSES,
                "mediane_pct": pourcentages.median().to_numpy(),
                "part_ponderee_pct": (
                    pourcentages.mul(retards, axis=0).sum() / retards.sum()
                ).to_numpy(),
            }
        )

        return resultat.sort_values("part_ponderee_pct", ascending=False).reset_index(
            drop=True
        )

    def comparer_liaisons(self, liaisons: Sequence[tuple[str, str]]) -> pd.DataFrame:
        """Compare la repartition des causes de retard entre plusieurs liaisons SNCF.

        Returns:
            Tableau avec ``liaison``, ``cause``, ``part_ponderee_pct``.
        """

        # L'utilisateur doit selectionner entre 2 et 5 liaisons pour effectuer une comparaisons
        if not 2 <= len(liaisons) <= 5:
            raise AnalyseCausesErreur(
                "Sélectionner entre 2 et 5 liaisons pour la comparaison."
            )
        if len(set(liaisons)) != len(liaisons):
            raise AnalyseCausesErreur("Les liaisons doivent être distinctes.")

        comparaisons = []
        for depart, arrivee in liaisons:
            repartition = self.filtrer_liaison(depart, arrivee).repartition_causes()
            repartition.insert(0, "liaison", f"{depart} → {arrivee}")
            comparaisons.append(repartition)
        return pd.concat(comparaisons, ignore_index=True)
