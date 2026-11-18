
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


