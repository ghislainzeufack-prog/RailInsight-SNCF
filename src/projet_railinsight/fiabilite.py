
import pandas as pd

def calculer_taux_retard(
    trains_prevus: int,
    trains_annules: int,
    trains_retard: int,
) -> float:
    """Calcule le pourcentage de trains en retard parmi les trains circulés."""

    # Validation des effectifs
    if min(trains_prevus, trains_annules, trains_retard) < 0:
        raise ValueError("Les effectifs ne peuvent pas être négatifs.")

    if trains_annules > trains_prevus:
        raise ValueError("Les annulations dépassent les trains prévus.")

    # Calcul des trains circulés
    trains_circules = trains_prevus - trains_annules

    if trains_circules == 0:
        raise ValueError("Aucun train n'a circulé.")

    if trains_retard > trains_circules:
        raise ValueError("Les retards dépassent les trains circulés.")

    # Calcul du taux de retard en pourcentage
    return 100 * trains_retard / trains_circules



def calculer_taux_annulation(
    trains_prevus: int,
    trains_annules: int,
) -> float:
    """Calcule le pourcentage de trains annulés parmi les trains prévus."""

    # Validation des effectifs
    if trains_prevus < 0 or trains_annules < 0:
        raise ValueError("Les effectifs ne peuvent pas être négatifs.")

    if trains_annules > trains_prevus:
        raise ValueError("Les annulations dépassent les trains prévus.")

    if trains_prevus == 0:
        raise ValueError("Aucun train n'était prévu.")

    # Calcul du taux d'annulation en pourcentage
    return 100 * trains_annules / trains_prevus



class AnalyseFiabilite:
    """Analyse la fiabilité des liaisons TGV à partir des données SNCF."""

    def __init__(self, donnees: pd.DataFrame) -> None:
        # Vérification du type des données
        if not isinstance(donnees, pd.DataFrame):
            raise TypeError("Les données doivent être un DataFrame pandas.")

        # Conservation d'une copie indépendante
        self.donnees = donnees.copy()


    def calculer_indicateurs(self) -> pd.DataFrame:
        """Calcule les taux de retard et d'annulation pour chaque observation."""

        # Identification des colonnes nécessaires
        colonnes = [
            "Nombre de circulations prévues",
            "Nombre de trains annulés",
            "Nombre de trains en retard à l'arrivée",
        ]

        # Vérification des colonnes présentes
        manquantes = [col for col in colonnes if col not in self.donnees.columns]

        if manquantes:
            raise ValueError(f"Colonnes manquantes : {manquantes}")

        # Création d'une copie
        resultat = self.donnees.copy()

        # Calcul des trains circulés
        resultat["Trains circulés"] = (
            resultat["Nombre de circulations prévues"]
            - resultat["Nombre de trains annulés"]
        )

        # Validation des effectifs
        prevus = resultat["Nombre de circulations prévues"]
        annules = resultat["Nombre de trains annulés"]
        retards = resultat["Nombre de trains en retard à l'arrivée"]
        circules = resultat["Trains circulés"]

        if (
            prevus.isna().any()
            or annules.isna().any()
            or retards.isna().any()
            or (prevus < 0).any()
            or (annules < 0).any()
            or (retards < 0).any()
            or (annules > prevus).any()
            or (circules <= 0).any()
            or (retards > circules).any()
        ):
            raise ValueError("Effectifs invalides pour le calcul des indicateurs.")

        # Calcul des taux en pourcentage
        resultat["Taux de retard (%)"] = 100 * retards / circules
        resultat["Taux d'annulation (%)"] = 100 * annules / prevus

        return resultat


    def classer_liaisons(
        self,
        annee: int | None = None,
        min_circulations: int = 500,
        min_mois: int = 10,
    ) -> pd.DataFrame:
        """Classe les liaisons selon leur taux de retard à l'arrivée."""

        # Validation des paramètres
        if min_circulations < 0 or min_mois < 1:
            raise ValueError("Seuils de sélection invalides.")

        # Calcul des indicateurs
        donnees = self.calculer_indicateurs()

        # Vérification des colonnes
        colonnes = ["Date", "Service", "Gare de départ", "Gare d'arrivée"]
        manquantes = [col for col in colonnes if col not in donnees.columns]

        if manquantes:
            raise ValueError(f"Colonnes manquantes : {manquantes}")

        # Conversion des dates
        donnees["Date"] = pd.to_datetime(donnees["Date"], errors="coerce")

        if donnees["Date"].isna().any():
            raise ValueError("Dates invalides.")

        # Filtrage de l'année
        if annee is not None:
            donnees = donnees.loc[donnees["Date"].dt.year == annee].copy()

        # Agrégation des effectifs par liaison
        classement = (
            donnees.groupby(
                ["Service", "Gare de départ", "Gare d'arrivée"],
                as_index=False,
            )
            .agg(
                trains_circules=("Trains circulés", "sum"),
                trains_retard=(
                    "Nombre de trains en retard à l'arrivée",
                    "sum",
                ),
                nombre_mois=("Date", "nunique"),
            )
        )

        # Sélection des liaisons suffisamment représentées
        classement = classement.loc[
            (classement["trains_circules"] >= min_circulations)
            & (classement["nombre_mois"] >= min_mois)
        ].copy()

        # Calcul du taux agrégé
        classement["taux_retard"] = (
            100 * classement["trains_retard"] / classement["trains_circules"]
        )

        # Classement décroissant
        classement = classement.sort_values(
            "taux_retard",
            ascending=False,
        ).reset_index(drop=True)

        return classement



    def evolution_temporelle(
        self,
        gare_depart: str,
        gare_arrivee: str,
        service: str,
        annee: int | None = None,
    ) -> pd.DataFrame:
        """Calcule l'évolution mensuelle du taux de retard d'une liaison."""

        # Calcul des indicateurs
        donnees = self.calculer_indicateurs()

        # Vérification des colonnes
        colonnes = ["Date", "Service", "Gare de départ", "Gare d'arrivée"]
        manquantes = [col for col in colonnes if col not in donnees.columns]

        if manquantes:
            raise ValueError(f"Colonnes manquantes : {manquantes}")

        # Conversion des dates
        donnees["Date"] = pd.to_datetime(donnees["Date"], errors="coerce")

        if donnees["Date"].isna().any():
            raise ValueError("Dates invalides.")

        # Sélection de la liaison
        donnees = donnees.loc[
            (donnees["Gare de départ"] == gare_depart)
            & (donnees["Gare d'arrivée"] == gare_arrivee)
            & (donnees["Service"] == service)
        ].copy()

        # Filtrage de l'année
        if annee is not None:
            donnees = donnees.loc[donnees["Date"].dt.year == annee]

        # Agrégation mensuelle
        evolution = (
            donnees.groupby("Date", as_index=False)
            .agg(
                trains_circules=("Trains circulés", "sum"),
                trains_retard=(
                    "Nombre de trains en retard à l'arrivée",
                    "sum",
                ),
            )
            .sort_values("Date")
        )

        # Calcul du taux mensuel
        evolution["taux_retard"] = (
            100 * evolution["trains_retard"] / evolution["trains_circules"]
        )

        return evolution


