# Analyse des circulations et annulations TGV

## 1. Cadrage et question de recherche
**Question principale :** Les liaisons davantage desservies connaissent-elles des taux d'annulation ou de retard différents ?

### Sous-questions étudiées
1. **Volet A (Volume vs Annulations) :** Existe-t-il une association statistique (Pearson / Spearman) entre le volume de circulations prévues et les taux d'annulation ou de retard (à la maille liaison-mois et à la maille liaison agrégée) ?
2. **Volet B (Groupes comparables) :** Cette association subsiste-t-elle lorsque l'on segmente le réseau en 3 groupes de desserte (faible, moyenne, forte par quantiles) et que l'on filtre les petits échantillons ?
3. **Volet C (Durée et robustesse) :** La durée moyenne du trajet influence-t-elle conjointement le taux d'annulation et le taux de retard, avec ou sans valeurs extrêmes ?

### Hypothèses initiales
* **Hypothèse 1 (Effet de priorisation) :** Les liaisons à fort volume (axes structurants) bénéficient d'une meilleure résilience opérationnelle et subissent des taux d'annulation plus faibles que les liaisons secondaires.
* **Hypothèse 2 (Exposition horaire) :** Les trajets plus longs sont associés à des taux de retard plus élevés en raison d'une exposition prolongée aux aléas du réseau.

---

## 2. Diagnostic EDA et contrat des indicateurs

### Colonnes officielles examinées
| Colonne | Type attendu | Unité | Règle de validation / Anomalies observées |
| :--- | :--- | :--- | :--- |
| `date` | Texte / Date (`YYYY-MM`) | Mois | Doit être renseignée et valide |
| `gare_depart` | Texte (`str`) | Gare | Chaîne non vide |
| `gare_arrivee` | Texte (`str`) | Gare | Chaîne non vide |
| `nb_train_prevu` | Numérique (`float/int`) | Trains | Strictement positif pour définir un taux d'annulation |
| `nb_annulation` | Numérique (`float/int`) | Trains | Positif ou nul et inférieur ou égal à `nb_train_prevu` (60 lignes invalides dans le brut où `nb_annulation` dépasse `nb_train_prevu`) |
| `nb_train_retard_arrivee` | Numérique (`float/int`) | Trains | Positif ou nul et inférieur ou égal à `trains_circules` |
| `duree_moyenne` | Numérique (`float`) | Minutes | Strictement positif |

> **Avertissement métier :** `nb_train_prevu` mesure l'offre de circulation ferroviaire et ne doit jamais être interprété comme un nombre de voyageurs. Par ailleurs, conformément à la notice SNCF Open Data, la somme des liaisons ne reconstruit pas la régularité globale du réseau TGV (un même train pouvant être comptabilisé sur plusieurs liaisons).

### Formules et dénominateurs retenus
* **Trains ayant réellement circulé :** `trains_circules = nb_train_prevu - nb_annulation`
* **Taux d'annulation (en %) :** `somme(nb_annulation) / somme(nb_train_prevu) * 100`
* **Taux de retard à l'arrivée (en %) :** `somme(nb_train_retard_arrivee) / somme(trains_circules) * 100`

**Pourquoi pas une moyenne simple des taux mensuels ?**
Prendre la moyenne arithmétique de taux mensuels donne le même poids à un mois creux (ex. 20 trains prévus, 0 annulé = 0 %) qu'à un mois de fort trafic (ex. 100 trains prévus, 10 annulés = 10 %), ce qui donnerait 5 % au lieu du vrai taux pondéré de `10 / 120 = 8,33 %`. Toutes nos agrégations somment numérateurs et dénominateurs avant division.

---

## 3. Choix d'architecture : Pourquoi une classe `AnalyseCirculations` ?
Conformément aux bonnes pratiques de programmation orientée objet (POO), l'utilisation de la classe `AnalyseCirculations` permet :
1. **D'encapsuler et protéger l'état :** Le constructeur valide une seule fois le schéma du `DataFrame`, réalise une copie défensive (`copy()`) pour garantir la non-mutation des données sources et prépare les colonnes dérivées (`liaison`, `trains_circules`, indicateurs de validité).
2. **De séparer le métier de l'interface :** Les règles mathématiques et statistiques vivent dans `src/projet_railinsight/circulations.py` et sont testables unitairement via `pytest` sans dépendre de Streamlit.

---

## 4. Résultats observés et limites scientifiques
* **Volet A (Volume vs Annulations) :** Sur les données SNCF agrégées par liaison comme à la maille liaison-mois, la corrélation de Spearman entre `nb_train_prevu` et `taux_annulation` est très proche de zéro (-0,05 en mensuel, 0,00 en agrégé). Un fort volume de trains prévus entraîne mécaniquement plus d'annulations en valeur absolue, mais n'est pas associé à un taux d'annulation relatif plus élevé.
* **Volet B (Groupes de desserte) :** La comparaison par quantiles de volume (`Faible desserte`, `Desserte moyenne`, `Forte desserte`) montre que les médianes du taux d'annulation restent proches entre groupes, tandis que la dispersion (écart interquartile) est beaucoup plus marquée sur les petites liaisons (sensibilité aux petits dénominateurs).
* **Volet C (Durée et robustesse) :** La stratification par tranche de durée montre une corrélation faible avec le taux d'annulation, mais une tendance légèrement supérieure sur le taux de retard à l'arrivée pour les longs trajets (plus de 3h). Cette relation reste purement **associative et descriptive** : aucune relation causale ne peut en être déduite sans variables de confusion (météo, saturation d'infrastructure, correspondances).
