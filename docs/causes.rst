Analyse des causes de retard - Ghislain
=======================================

Présentation
------------

Ce module permet d'analyser la répartition des causes de retard
des trains TGV de la SNCF.

Il permet :

- De filtrer les observations par période et par liaison.
- D'analyser les volumes de trains en retard.
- De calculer la répartition pondérée des causes de retard.
- De comparer les causes de retard entre plusieurs liaisons.


Classe AnalyseCauses
--------------------

.. autoclass:: projet_railinsight.causes.AnalyseCauses
   :members:
   :show-inheritance:


Gestion des exceptions
----------------------

.. autoclass:: projet_railinsight.causes.AnalyseCausesErreur

.. autoclass:: projet_railinsight.causes.ColonnesManquantesErreur


Configuration des logs
----------------------

.. automodule:: projet_railinsight.logging_config
   :members: