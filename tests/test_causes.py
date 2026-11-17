"""Ce module permet de tester les differentes fonctions implementees dans causes.py"""

import pandas as pd
import pytest
from projet_railinsight.causes import (
    COLONNES_CAUSES,
    AnalyseCauses,
    AnalyseCausesErreur,
    ColonnesManquantesErreur,
)


@pytest.fixture
def df_sncf() -> pd.DataFrame:
    """Cree trois observations valides et deux profils non exploitables."""
    df = pd.DataFrame(
        {
            "Date": ["2026-01", "2026-02", "2026-02", "2026-03", "2026-03"],
            "Gare de départ": ["Yaoundé", "Yaoundé", "Douala", "Yaoundé", "Yaoundé"],
            "Gare d'arrivée": ["Douala", "Douala", "Yaoundé", "Douala", "Douala"],
            "Nombre de trains en retard à l'arrivée": [5, 10, 40, 0, 12],
            "Nombre de circulations prévues": [30, 80, 100, 10, 40],
            "Nombre de trains annulés": [2, 5, 0, 0, 3],
        }
    )
    for cause in COLONNES_CAUSES:
        df[cause] = 0.0
    df.loc[:, COLONNES_CAUSES[0]] = [20, 35, 30, 0, 15]
    df.loc[:, COLONNES_CAUSES[1]] = [10, 45, 40, 0, 20]
    return df


def test_colonne_manquante(df_sncf: pd.DataFrame) -> None:
    """Le test reussi s'il manque une colonne obligatoire et que notre
    programme detecte correctement cette absence
    """

    # On retire volontairement la colonne 'Date'
    df_incomplet = df_sncf.drop(columns="Date")

    # On verifie que notre classe 'ColonnesManquantesErreur' detecte
    # l'exception levee dont le message contient 'Date'
    with pytest.raises(ColonnesManquantesErreur, match="Date"):
        # On cree un objet avec le DataFrame incomplet, et normalement
        # on doit lever une exception
        AnalyseCauses(df_incomplet)
