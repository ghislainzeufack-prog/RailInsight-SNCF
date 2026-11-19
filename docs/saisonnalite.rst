Module de saisonnalité
===========================

``src/projet_railinsight/saisonnalite.py`` reprend les analyses des notebooks.

Utilisation dans une future page Streamlit
-----------------------------------------------

``creer_connexion()`` se connecte directement à un serveur PostgreSQL ``178.104.170.49:5432`` avec un compte ``railinsight_lecture``. Aucun tunnel ni clé SSH n’est
nécessaire. Le module vérifie le certificat TLS public inclus dans le projet. Ne pas abuser sur les requêtes coûteuses ou multiplier les connexions.

Les identifiants du compte de lecture sont inclus dans le module : cloner le projet et lancer ``uv sync`` suffit. Aucun fichier n’est à configurer.
La base PostgreSQL reste sur le VPS.

.. code-block:: python

   import streamlit as st
   from projet_railinsight.moteur_sql import creer_connexion
   from projet_railinsight.saisonnalite import analyser_saisonnalite

Appeler les fonctions
--------------------------

Après clonage et ``uv sync``, la connexion est prête : le compte de lecture
est inclus dans le projet. Aucun fichier n’est à créer.

Exécuter une requête SQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from projet_railinsight.moteur_sql import creer_connexion, executer_requete

   engine = creer_connexion()

   # Entrée exemple
   requete = "SELECT COUNT(*) AS nombre_lignes FROM regularite_tgv WHERE service = ?"
   data = executer_requete(engine, requete, ["National"])

   # Sortie : un DataFrame Pandas (valeur illustrative)
   #    nombre_lignes
   # 0          12000

Analyser la saisonnalité
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from projet_railinsight.saisonnalite import analyser_saisonnalite

   # Entrée : tous les paramètres (engine créé dans l’exemple précédent)
   resultats = analyser_saisonnalite(
       engine=engine,
       nettoyage=True,      # False pour les données brutes
       service="National",  # None pour tous ; "International" pour l’international
       annee_debut=2024,    # None pour aucune borne de début
       annee_fin=2025,      # None pour aucune borne de fin
   )

   # Sortie : un dictionnaire
   # {
   #     "mensuel": DataFrame des totaux et taux par mois,
   #     "description": {"apercu": DataFrame, "statistiques": DataFrame},
   #     "saisonnalite": DataFrame des moyennes par mois,
   #     "correlations": DataFrame des corrélations,
   #     "regression": dictionnaire des résultats du modèle,
   # }

Calculs et limites
-----------------------

- Le nettoyage exclut les annulations négatives ou supérieures aux circulations
  prévues. Les autres règles du notebook concernent des colonnes absentes de
  cette analyse (durée, retard moyen, retards supérieurs à 30 minutes).
- ``nb_annulations_manquantes`` permet de repérer les mois dont le total est
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
  les degrés de liberté comme ``n - 3`` (constante et deux variables). Une série
  trop courte ou des variables colinéaires renvoient ``disponible=False``.

Tests : ``PYTHONPATH=src uv run pytest tests/test_saisonnalite.py -q``.
