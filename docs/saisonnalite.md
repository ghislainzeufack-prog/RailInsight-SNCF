# Module de saisonnalité

`src/projet_railinsight/saisonnalite.py` reprend les analyses des notebooks à
partir de `regularite_tgv` dans PostgreSQL. Il utilise la vue `regularite_tgv_clean` en mode nettoyage, comme `SQL_clean`
dans le notebook, et la table brute sinon (`SQL_ref`). Il ne modifie pas la base.

## Utilisation dans une future page Streamlit

`creer_connexion()` se connecte directement à `178.104.170.49:5432`, base
`sncf_c_gro_nul`, compte `railinsight_lecture`. Aucun tunnel ni clé SSH n’est
nécessaire. Le module vérifie le certificat TLS public inclus dans le projet.

Le mot de passe est lu depuis `~/.pgpass` (voir le README pour la configuration).
Chaque membre demande les identifiants à Romain et installe uniquement les dépendances Python ; la base PostgreSQL reste sur le VPS.

```python
import streamlit as st
from projet_railinsight.moteur_sql import creer_connexion
from projet_railinsight.saisonnalite import analyser_saisonnalite

@st.cache_resource
def connexion():
    return creer_connexion()

@st.cache_data(ttl=300)
def analyses(nettoyage, debut, fin):
    return analyser_saisonnalite(
        connexion(), nettoyage=nettoyage, service="National",
        annee_debut=debut, annee_fin=fin,
    )

resultats = analyses(True, 2020, 2025)
st.dataframe(resultats["mensuel"])
st.line_chart(resultats["mensuel"].set_index("date")[[
    "total_annulation", "total_retard_depart", "total_retard_arrivee"
]])
st.line_chart(resultats["saisonnalite"])
st.dataframe(resultats["correlations"])
regression = resultats["regression"]
if regression["disponible"]:
    st.dataframe(regression["coefficients"])
    st.dataframe(regression["observations"])
else:
    st.info(regression["raison"])
```

Passer `nettoyage=False` pour comparer aux données originales et `service=None`
pour inclure tous les services. Les années sont inclusives ; sans bornes, toutes
les années sont retenues. Les mois absents ne sont pas inventés ou remplis à zéro.

## Calculs et limites

- Le nettoyage exclut les annulations négatives ou supérieures aux circulations
  prévues. Les autres règles du notebook concernent des colonnes absentes de
  cette analyse (durée, retard moyen, retards supérieurs à 30 minutes).
- `nb_annulations_manquantes` permet de repérer les mois dont le total est
  incomplet. SQL ignore les valeurs nulles dans les sommes ; un mois entièrement
  inconnu reste manquant.
- Les taux sont exprimés en pourcentage des circulations prévues. Pour chaque
  taux, le numérateur et le dénominateur portent sur les mêmes lignes connues,
  avec un volume prévu positif. Ils ne représentent pas un pourcentage des
  seuls trains ayant circulé. Aucun écrêtage artificiel à 100 % n'est appliqué.
- Le taux de perturbation au départ combine annulations et retards au départ.
  Il ne cumule pas les retards au départ et à l'arrivée, qui peuvent concerner
  les mêmes trains.
- La saisonnalité est une moyenne des totaux mensuels entre années ; ce n'est
  pas une estimation corrigée du volume de circulation.
- La régression reproduit le modèle exploratoire avec mois numérique et nombre
  d'annulations. Le mois numérique ne représente pas le caractère cyclique de
  l'année. Corrélation et régression n'établissent pas de causalité ; les tests
  de Student supposent notamment des erreurs indépendantes et de variance
  constante, ce qui n'est pas garanti pour ces séries temporelles.
- Le modèle utilise les moindres carrés sans inversion directe de X'X et calcule
  les degrés de liberté comme `n - 3` (constante et deux variables). Une série
  trop courte ou des variables colinéaires renvoient `disponible=False`.

Tests : `PYTHONPATH=src uv run pytest tests/test_saisonnalite.py -q`.

