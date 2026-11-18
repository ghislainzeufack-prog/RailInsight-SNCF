Analyse des circulations et annulations
=======================================

Présentation
------------

Ce module permet d'analyser les volumes de circulations prévues, les taux
d'annulation et les taux de retard à l'arrivée des trains TGV à partir du
jeu de données mensuel de la SNCF.

Il permet notamment de :

- valider le schéma des données et diagnostiquer les observations incohérentes,
- filtrer les observations par période, par liaison et par seuil de volume mensuel,
- calculer les indicateurs globaux et par liaison avec pondération par les volumes,
- évaluer les corrélations de Pearson et de Spearman entre volume et régularité (Volet A),
- classer les liaisons par catégories de desserte en tertiles de volume (Volet B),
- analyser conjointement la durée des trajets, les annulations et les retards avec filtrage IQR (Volet C).

Classe AnalyseCirculations
--------------------------

.. autoclass:: projet_railinsight.circulations.AnalyseCirculations
   :members:
   :undoc-members:
   :show-inheritance:

Classe CompteurObservations
---------------------------

.. autoclass:: projet_railinsight.circulations.CompteurObservations
   :members:
   :undoc-members:
   :show-inheritance:

Exceptions
----------

.. autoexception:: projet_railinsight.circulations.ErreurValidationCirculations
   :members:
   :undoc-members:
   :show-inheritance:
