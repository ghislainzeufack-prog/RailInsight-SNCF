# Analyse de la persistance des retards TGV

**Projet :** RailInsight-SNCF  
**Contribution :** Analyse statistique, modélisation AR(1) et visualisation interactive  
**Périmètre :** Retards TGV agrégés mensuellement, toutes liaisons confondues  
**Données :** Régularité mensuelle des TGV — SNCF / AQST

---

## 1. Contexte et objectifs

La ponctualité constitue un indicateur essentiel de la qualité du transport ferroviaire. Les retards des trains peuvent évoluer dans le temps sous l'effet de facteurs variés, notamment les conditions météorologiques, les incidents techniques, les travaux sur les infrastructures ou les perturbations de l'exploitation.

L'analyse descriptive permet d'observer ces fluctuations. Cependant, elle ne suffit pas à déterminer si les retards présentent une certaine continuité temporelle.

Cette contribution cherche donc à répondre à la question suivante :

**Le taux global de retard des TGV observé pendant un mois est-il statistiquement lié à celui du mois précédent ?**

Cette question correspond à l'étude de la *persistance temporelle*.

Une persistance positive signifie qu'un niveau de retard relativement élevé pendant un mois tend à être associé à un niveau également élevé le mois suivant. Inversement, un niveau relativement faible peut avoir tendance à être suivi d'un niveau faible.

L'objectif principal est de mesurer cette dépendance temporelle, sans chercher à établir une relation de causalité.

Plus précisément, notre travail consiste à :

1. Préparer et contrôler les données mensuelles de régularité des TGV.
2. Construire un indicateur global de retard supérieur à 15 minutes.
3. Décrire l'évolution de cet indicateur sur la période étudiée.
4. Estimer un modèle autorégressif d'ordre 1, noté AR(1).
5. Interpréter le coefficient de persistance obtenu.
6. Évaluer les prévisions du modèle AR(1) sur une période de test.
7. Comparer ses performances à celles d'un modèle naïf.
8. Mettre les résultats à disposition dans un tableau de bord interactif Streamlit.

Cette contribution s'inscrit dans le projet collectif RailInsight-SNCF et se concentre sur la dimension temporelle globale des retards.

## 2. Présentation des données

### 2.1. Source des données

L'analyse utilise le fichier :

`data/raw/regularite-mensuelle-tgv-aqst.csv`

Il contient des observations mensuelles de régularité des TGV, notamment les volumes de circulations, les annulations et les retards.

Le fichier CSV utilise le point-virgule (`;`) comme séparateur.

Dans la version exploitée pour cette étude, nous disposons de :

| Caractéristique | Valeur |
|---|---|
| Nombre d'observations initiales | 12 907 |
| Nombre de mois dans la série analysée | 105 |
| Premier mois | Janvier 2018 |
| Dernier mois | Septembre 2026 |
| Fréquence d'analyse | Mensuelle |
| Unité de l'indicateur | Pourcentage |

Ces informations correspondent à la version des données utilisée lors du développement. Elles peuvent évoluer si le fichier source est actualisé.

### 2.2. Périmètre de l'étude : une analyse globale

**Notre étude porte sur le taux global mensuel de retard des TGV, toutes liaisons présentes dans le fichier confondues.**

Il est important de distinguer deux niveaux d'analyse.

**Analyse par liaison :** chaque liaison ferroviaire possède sa propre série de taux de retard. On pourrait alors étudier séparément la persistance des retards sur Paris–Lyon, Paris–Bordeaux ou d'autres itinéraires.

**Analyse globale :** toutes les observations valides d'un même mois sont regroupées pour calculer un indicateur unique représentant le taux de retard global des circulations étudiées.

Nous avons retenu la seconde approche.

Ainsi, pour chaque mois, nous additionnons les effectifs de trains réalisés et les effectifs de trains en retard, puis calculons un seul taux mensuel.

Ce choix présente plusieurs avantages :

- Il permet d'obtenir une série chronologique unique et directement interprétable.
- Il répond à notre question sur la persistance globale des retards.
- Il évite de multiplier les modèles statistiques pour chaque liaison.
- Il facilite la comparaison avec les autres analyses globales du projet.

En revanche, les conclusions obtenues ne doivent pas être interprétées comme des résultats propres à une liaison particulière.

Une persistance globale positive n'implique pas nécessairement une persistance positive sur toutes les liaisons.

### 2.3. Variables utilisées

Les principales colonnes du fichier sont :

| Variable | Description |
|---|---|
| `Date` | Mois de l'observation |
| `Nombre de circulations prévues` | Nombre de circulations programmées |
| `Nombre de trains annulés` | Nombre de circulations annulées |
| `Nombre trains en retard > 15min` | Nombre de trains ayant dépassé 15 minutes de retard |

Le fichier contient également :

- `Nombre trains en retard > 30min`
- `Nombre trains en retard > 60min`

Ces deux dernières colonnes ne sont pas utilisées dans la construction de notre indicateur principal.

### 2.4. Justification du seuil de 15 minutes

Nous avons choisi de mesurer la proportion de trains présentant un retard supérieur à 15 minutes.

Les colonnes de retards supérieurs à 15, 30 et 60 minutes sont interprétées comme des indicateurs à seuils cumulatifs.

Cela signifie qu'un train ayant 65 minutes de retard est déjà comptabilisé parmi les trains ayant plus de 15 minutes de retard.

Sous cette interprétation :

$$
N_{>60}\leq N_{>30}\leq N_{>15}
$$

Par exemple, si une observation indique :

| Seuil de retard | Nombre de trains |
|---|---:|
| Plus de 15 minutes | 110 |
| Plus de 30 minutes | 44 |
| Plus de 60 minutes | 8 |

Alors, sous l'hypothèse cumulative, les 110 trains comprennent déjà les 44 trains ayant dépassé 30 minutes et les 8 trains ayant dépassé 60 minutes.

Il serait incorrect de calculer :

$$
110+44+8=162
$$

car cela conduirait à compter plusieurs fois certains trains.

**Nous utilisons donc uniquement la colonne `Nombre trains en retard > 15min`.**

Cette interprétation est cohérente avec les exemples examinés dans le fichier. Une confirmation formelle peut être recherchée dans la documentation officielle du jeu de données.

## 3. Construction de l'indicateur mensuel

### 3.1. Nombre de trains réalisés

Le nombre de trains effectivement réalisés est obtenu en soustrayant les annulations des circulations prévues.

Pour une observation $i$ :

$$
N_{\mathrm{realises},i}
=
N_{\mathrm{prevus},i}
-
N_{\mathrm{annules},i}
$$

Les trains annulés ne sont donc pas inclus dans le dénominateur de notre indicateur.

Cette distinction est importante : notre étude porte sur les retards des trains réalisés et non sur les annulations.

### 3.2. Taux de retard par observation

Pour chaque observation valide, nous définissons :

$$
r_i
=
100\times
\frac{N_{>15,i}}
{N_{\mathrm{realises},i}}
$$

où :

- $N_{>15,i}$ désigne le nombre de trains en retard de plus de 15 minutes ;
- $N_{\mathrm{realises},i}$ désigne le nombre de trains réalisés.

Le résultat est exprimé en pourcentage.

### 3.3. Agrégation mensuelle globale

Pour chaque mois $t$, nous considérons l'ensemble $I_t$ des observations valides appartenant à ce mois.

Le taux mensuel global est défini par :

$$
\boxed{
R_t
=
100\times
\frac{\displaystyle\sum_{i\in I_t}N_{>15,i}}
{\displaystyle\sum_{i\in I_t}N_{\mathrm{realises},i}}
}
$$

Cette formule constitue le fondement de notre analyse.

Elle signifie que nous calculons la proportion globale de trains en retard parmi tous les trains réalisés au cours du mois.

**Il ne s'agit pas d'une moyenne arithmétique des taux calculés séparément pour chaque liaison.**

#### Exemple

Supposons qu'un mois comporte deux liaisons :

| Liaison | Trains réalisés | Trains en retard | Taux |
|---|---:|---:|---:|
| A | 1 000 | 100 | 10 % |
| B | 100 | 30 | 30 % |

Une moyenne simple des taux donnerait :

$$
\frac{10+30}{2}=20\%
$$

Cependant, cette moyenne attribuerait le même poids à deux liaisons ayant des volumes de circulation très différents.

Le taux global correct est :

$$
R_t
=
100\times\frac{100+30}{1000+100}
$$

$$
R_t\approx11{,}82\%
$$

Cette méthode est équivalente à une moyenne pondérée des taux des observations, les poids étant proportionnels aux nombres de trains réalisés.

Elle est donc plus adaptée à notre objectif d'analyse globale.

## 4. Préparation et contrôle des données

Les opérations de préparation sont implémentées dans :

`src/projet_railinsight/data_processing.py`

Ce module contient trois fonctions principales.

### 4.1. Chargement : `charger_donnees_tgv()`

Cette fonction charge le fichier CSV à l'aide de `pandas`.

Elle effectue les opérations suivantes :

1. Lecture du fichier avec le séparateur `;`.
2. Vérification de la présence de la colonne `Date`.
3. Conversion des dates au format `AAAA-MM`.
4. Création de la colonne `Date_parsed`.

Les dates non interprétables sont représentées par des valeurs manquantes.

### 4.2. Validation : `preparer_donnees_retards()`

Cette fonction calcule le nombre de trains réalisés et vérifie la cohérence des observations.

Les conditions de validité sont les suivantes :

$$
N_{\mathrm{prevus},i}\geq0
$$

$$
0\leq N_{\mathrm{annules},i}
\leq N_{\mathrm{prevus},i}
$$

$$
N_{\mathrm{realises},i}>0
$$

$$
0\leq N_{>15,i}
\leq N_{\mathrm{realises},i}
$$

Ces conditions permettent notamment d'éviter :

- les effectifs négatifs ;
- un nombre d'annulations supérieur au nombre de circulations prévues ;
- une division par zéro ;
- un nombre de trains en retard supérieur au nombre de trains réalisés.

La fonction conserve les observations invalides dans le DataFrame préparé, mais leur attribue un taux de retard manquant (`NaN`).

Elle ne modifie pas le DataFrame original.

### 4.3. Agrégation : `calculer_taux_mensuel()`

Cette fonction :

1. Applique les contrôles précédents.
2. Sélectionne les observations valides.
3. Exclut les dates manquantes.
4. Regroupe les données par mois.
5. Calcule les sommes mensuelles des trains réalisés et retardés.
6. Calcule le taux global mensuel.

Le DataFrame retourné contient notamment :

| Colonne | Description |
|---|---|
| `trains_retardes` | Nombre total de trains en retard de plus de 15 minutes pendant le mois |
| `trains_realises` | Nombre total de trains réalisés pendant le mois |
| `taux_retard_15min` | Taux global mensuel de retard, en pourcentage |

La série utilisée pour l'analyse est :

`mensuel["taux_retard_15min"]`

Les observations sont ordonnées chronologiquement.

## 5. Analyse descriptive de la série

La première étape de l'analyse consiste à visualiser l'évolution du taux global mensuel de retard.

Le tableau de bord présente :

- le nombre d'observations initiales ;
- le nombre de mois étudiés ;
- le taux mensuel moyen ;
- le taux du dernier mois ;
- l'évolution chronologique de l'indicateur.

### 5.1. Taux mensuel moyen

La moyenne des taux mensuels est définie par :

$$
\overline R
=
\frac{1}{T}\sum_{t=1}^{T}R_t
$$

où $T$ représente le nombre de mois analysés.

Pour notre série, nous obtenons approximativement :

$$
\overline R=10{,}49\%
$$

Cette valeur signifie que la moyenne arithmétique des taux globaux mensuels est d'environ 10,49 % sur la période étudiée.

Il convient de distinguer cette moyenne du taux obtenu en regroupant l'ensemble des trains sur toute la période.

Dans la moyenne mensuelle, chaque mois possède le même poids, indépendamment du volume de circulation.

### 5.2. Évolution temporelle

La représentation graphique permet d'observer :

- les périodes de hausse du taux de retard ;
- les périodes de baisse ;
- les fluctuations importantes ;
- les éventuelles évolutions durables.

Cette analyse descriptive fournit une première lecture de la dynamique de la série.

Cependant, elle ne permet pas à elle seule de quantifier la dépendance entre deux mois consécutifs.

C'est pourquoi nous introduisons un modèle autorégressif.

## 6. Modélisation de la persistance : modèle AR(1)

### 6.1. Principe

Un modèle autorégressif explique une variable à partir de ses propres valeurs passées.

Dans notre cas, nous cherchons à expliquer le taux de retard d'un mois à partir de celui du mois précédent.

Nous retenons un modèle autorégressif d'ordre 1, noté AR(1).

Ce choix permet de disposer d'un modèle simple, interprétable et adapté à une première étude de la dépendance temporelle.

### 6.2. Formulation mathématique

Le modèle s'écrit :

$$
\boxed{
R_t=c+\phi R_{t-1}+\varepsilon_t
}
$$

où :

- $R_t$ représente le taux global de retard du mois $t$ ;
- $R_{t-1}$ représente le taux global du mois précédent ;
- $c$ est la constante ;
- $\phi$ est le coefficient autorégressif ;
- $\varepsilon_t$ est le terme d'erreur.

Le paramètre central de notre étude est $\phi$.

Il mesure la dépendance linéaire entre deux mois consécutifs dans le cadre du modèle estimé.

### 6.3. Interprétation du coefficient

Dans le cadre d'un AR(1) stationnaire :

- Si $\phi$ est proche de zéro, la dépendance linéaire au mois précédent est faible.
- Si $0<\phi<1$, les fluctuations présentent une persistance positive qui s'atténue progressivement.
- Si $-1<\phi<0$, les écarts tendent à alterner de signe.
- Si $|\phi|\geq1$, la condition usuelle de stationnarité de l'AR(1) n'est pas satisfaite.

Pour un AR(1) stationnaire, la moyenne théorique est :

$$
\mu=\frac{c}{1-\phi}
$$

Cette expression permet de réécrire le modèle sous la forme :

$$
R_t-\mu
=
\phi(R_{t-1}-\mu)+\varepsilon_t
$$

Cette écriture montre que $\phi$ caractérise la transmission des écarts à la moyenne d'un mois au suivant.

### 6.4. Estimation du modèle

L'estimation est réalisée avec la bibliothèque `statsmodels`, à l'aide de la classe `AutoReg`.

La fonction correspondante se trouve dans :

`src/projet_railinsight/persistence.py`

Elle est nommée :

`estimer_ar1(serie)`

Le modèle est estimé sur la partie d'entraînement de la série.

Les résultats obtenus sont approximativement :

$$
\widehat\phi=0{,}437
$$

$$
\widehat c=5{,}657
$$

Le modèle estimé s'écrit donc :

$$
\boxed{
\widehat R_t
=
5{,}657+0{,}437R_{t-1}
}
$$

### 6.5. Interprétation du résultat

Le coefficient estimé est positif et inférieur à 1.

Cela suggère une **persistance temporelle positive modérée** du taux global mensuel de retard.

Dans le cadre du modèle, une augmentation d'un point de pourcentage du taux du mois précédent est associée à une augmentation prévue d'environ 0,437 point du taux du mois courant, toutes choses égales par ailleurs dans la spécification retenue.

Ce résultat ne signifie pas qu'un retard survenu pendant un mois provoque directement un retard le mois suivant.

Il s'agit d'une relation statistique entre les taux mensuels.

Par ailleurs, cette estimation concerne le taux global : elle ne permet pas de conclure à une persistance identique sur chaque liaison.

### 6.6. Limites du modèle

Le modèle AR(1) ne prend en compte qu'une seule valeur passée.

Il ne modélise pas explicitement :

- les effets saisonniers ;
- les évolutions structurelles ;
- les événements exceptionnels ;
- les conditions météorologiques ;
- les caractéristiques propres aux liaisons ;
- les autres facteurs explicatifs des retards.

Il suppose également une relation linéaire entre le taux courant et celui du mois précédent.

Enfin, le taux de retard est borné entre 0 et 100 %, tandis qu'un modèle AR(1) linéaire ne garantit pas automatiquement des prévisions respectant ces bornes.

Ces éléments invitent à interpréter le modèle comme une première approximation de la dynamique temporelle.

## 7. Évaluation des performances prédictives

### 7.1. Objectif de l'évaluation

L'existence d'une dépendance temporelle ne garantit pas qu'un modèle fournisse de bonnes prévisions.

Nous avons donc évalué les performances du modèle AR(1) en les comparant à une méthode de référence.

Deux approches sont considérées :

1. Le modèle AR(1).
2. Le modèle naïf.

### 7.2. Découpage des données

La série est divisée chronologiquement en deux parties :

- **Entraînement :** tous les mois précédant les douze derniers.
- **Test :** les douze derniers mois.

Les coefficients du modèle AR(1) sont estimés sur la période d'entraînement.

La période de test est réservée à l'évaluation.

Ce découpage respecte l'ordre temporel des observations.

### 7.3. Prévisions du modèle AR(1)

Pour un mois $t$ de la période de test, la prévision est calculée par :

$$
\widehat R_t^{AR(1)}
=
\widehat c+\widehat\phi R_{t-1}
$$

Les coefficients $\widehat c$ et $\widehat\phi$ sont estimés à partir de l'échantillon d'entraînement.

Chaque prévision utilise le taux réellement observé au mois précédent.

Nous évaluons donc des **prévisions à un mois d'horizon**, et non une trajectoire récursive de douze mois calculée sans nouvelles observations.

### 7.4. Prévisions du modèle naïf

Le modèle naïf suppose que le taux du mois suivant est identique au taux du mois courant.

Il s'écrit :

$$
\boxed{
\widehat R_t^{naif}=R_{t-1}
}
$$

Ce modèle constitue une référence pertinente pour une série temporelle.

Il permet de déterminer si l'utilisation d'un modèle statistique plus élaboré améliore effectivement les prévisions.

### 7.5. Métriques d'évaluation

Nous utilisons deux métriques.

#### Erreur absolue moyenne : MAE

La MAE est définie par :

$$
MAE
=
\frac{1}{n}
\sum_{t=1}^{n}
|R_t-\widehat R_t|
$$

Elle mesure l'écart absolu moyen entre les valeurs observées et les valeurs prévues.

Plus la MAE est faible, plus les prévisions sont proches des observations en moyenne.

#### Racine de l'erreur quadratique moyenne : RMSE

La RMSE est définie par :

$$
RMSE
=
\sqrt{
\frac{1}{n}
\sum_{t=1}^{n}
(R_t-\widehat R_t)^2
}
$$

Elle pénalise davantage les erreurs importantes.

Les deux métriques sont exprimées en points de pourcentage puisque les taux de retard sont exprimés en pourcentage.

### 7.6. Résultats obtenus

Les résultats sur les douze derniers mois sont les suivants, à l'arrondi près :

| Modèle | MAE | RMSE |
|---|---:|---:|
| AR(1) | 2,983 | 3,647 |
| Naïf | 2,975 | 3,444 |

Le modèle naïf présente une MAE et une RMSE légèrement inférieures à celles du modèle AR(1).

**Sur la période de test considérée, le modèle AR(1) ne surpasse donc pas le modèle naïf.**

Cette observation ne remet pas en cause l'intérêt du modèle AR(1) pour l'analyse de la persistance.

Elle montre simplement que la mise en évidence d'une dépendance temporelle ne garantit pas une amélioration des performances prédictives.

La période de test étant limitée à douze mois, ces résultats doivent être interprétés avec prudence.

## 8. Organisation du code

La contribution est organisée autour de plusieurs fichiers.

| Fichier | Rôle |
|---|---|
| `src/projet_railinsight/data_processing.py` | Chargement, contrôle et agrégation des données |
| `src/projet_railinsight/persistence.py` | Estimation AR(1), prévisions naïves et calcul des métriques |
| `notebooks/analyse_persistance_tgv.ipynb` | Analyse exploratoire et modélisation |
| `apps/persistance_app.py` | Tableau de bord interactif Streamlit |
| `tests/test_data_processing.py` | Tests du traitement des données |
| `tests/test_persistence.py` | Tests des fonctions de modélisation |

Le module `data_processing.py` regroupe les fonctions nécessaires à la préparation de notre série.

Le module `persistence.py` contient les fonctions statistiques.

Le notebook présente les étapes de l'analyse.

Le tableau de bord Streamlit permet de consulter les résultats sans exécuter manuellement les cellules du notebook.

Cette contribution est autonome vis-à-vis du module `common_processing.py`.

## 9. Installation et reproduction des résultats

Cette section explique comment exécuter le projet depuis un terminal.

Les commandes doivent être lancées depuis la racine du dépôt, sauf indication contraire.

### 9.1. Prérequis

Il faut disposer de :

- Git ;
- Python compatible avec la configuration du projet ;
- `uv`, pour la gestion de l'environnement et des dépendances ;
- un terminal ;
- un navigateur pour consulter Streamlit.

VS Code est recommandé pour ouvrir et exécuter le notebook, mais n'est pas indispensable pour lancer le tableau de bord.

### 9.2. Récupérer le dépôt

Cloner le projet :

```bash
git clone https://github.com/ghislainzeufack-prog/RailInsight-SNCF.git
```

Accéder au dossier :

```bash
cd RailInsight-SNCF
```

Pour consulter cette contribution avant son intégration à la branche principale :

```bash
git switch feature/analyse-persistance
```

Après son intégration dans `main`, il suffira d'utiliser la branche principale à jour.

### 9.3. Installer les dépendances

Depuis la racine du projet :

```bash
uv sync
```

Cette commande prépare l'environnement Python et installe les dépendances déclarées dans le projet.

Les principales bibliothèques utilisées sont :

| Bibliothèque | Utilisation |
|---|---|
| `pandas` | Lecture, manipulation et agrégation des données |
| `numpy` | Calcul numérique |
| `statsmodels` | Estimation du modèle AR(1) |
| `scikit-learn` | Calcul des métriques de prévision |
| `plotly` | Visualisations interactives |
| `streamlit` | Interface du tableau de bord |

### 9.4. Vérifier la présence du fichier de données

Le fichier attendu est :

```text
data/raw/regularite-mensuelle-tgv-aqst.csv
```

Il doit être placé dans ce dossier.

Pour vérifier sa présence depuis la racine du projet :

```bash
ls -lh data/raw/regularite-mensuelle-tgv-aqst.csv
```

Si le fichier est absent, il faut récupérer le jeu de données utilisé par le projet et le placer à cet emplacement.

### 9.5. Lancer le tableau de bord Streamlit

Depuis la racine du projet :

```bash
uv run streamlit run apps/persistance_app.py
```

Après le démarrage, Streamlit indique une adresse locale, généralement :

```text
http://localhost:8501
```

Ouvrir cette adresse dans un navigateur si l'application ne s'affiche pas automatiquement.

#### Contenu du tableau de bord

Le tableau de bord est organisé autour de plusieurs parties.

**Vue d'ensemble**

Elle présente les principaux indicateurs descriptifs : nombre d'observations, nombre de mois, taux moyen et dernier taux observé.

**Évolution mensuelle**

Un graphique interactif présente les fluctuations du taux global de retard supérieur à 15 minutes.

Les valeurs affichées correspondent aux taux mensuels calculés après agrégation des effectifs.

**Analyse de la persistance**

Cette partie présente le modèle AR(1), les paramètres estimés et l'interprétation du coefficient autorégressif.

**Comparaison des prévisions**

Elle permet de comparer les taux observés aux prévisions AR(1) et naïves sur la période de test.

Les métriques MAE et RMSE permettent de quantifier les erreurs.

**Conclusion**

Elle résume les principaux résultats et leurs limites.

Les graphiques interactifs permettent notamment de survoler les observations pour consulter leurs valeurs.

Pour arrêter l'application, revenir au terminal et utiliser :

```text
Ctrl+C
```

### 9.6. Ouvrir le notebook

Le notebook d'analyse est :

`notebooks/analyse_persistance_tgv.ipynb`

Pour l'utiliser dans VS Code :

1. Ouvrir le dossier `RailInsight-SNCF`.
2. Ouvrir le notebook dans le dossier `notebooks`.
3. Sélectionner l'environnement Python du projet.
4. Exécuter les cellules dans leur ordre d'apparition.

Le notebook permet de consulter les différentes étapes de l'analyse et de retrouver les calculs statistiques.

Le chemin du fichier de données est construit à partir de la structure du projet.

### 9.7. Exécuter les tests automatisés

Pour exécuter les tests propres à cette contribution :

```bash
uv run pytest tests/test_data_processing.py tests/test_persistence.py -v
```

Ces tests couvrent les fonctions de préparation des données et les fonctions statistiques.

Lors de la dernière validation locale, les douze tests concernés ont réussi.

Pour exécuter tous les tests du dépôt :

```bash
uv run pytest
```

Le résultat global peut évoluer avec les contributions des autres membres du projet.

### 9.8. Vérifier la qualité du code

Pour contrôler les principaux fichiers Python de cette contribution avec Ruff :

```bash
uv run ruff check src/projet_railinsight/data_processing.py src/projet_railinsight/persistence.py apps/persistance_app.py tests/test_data_processing.py tests/test_persistence.py
```

Cette commande permet de détecter les problèmes signalés par les règles de qualité configurées dans le projet.

## 10. Discussion des résultats

Notre analyse met en évidence une dépendance temporelle positive modérée du taux global mensuel de retard.

Le coefficient AR(1) estimé est approximativement égal à 0,437.

Ce résultat suggère qu'une partie des fluctuations du taux mensuel est associée aux fluctuations observées le mois précédent.

Cependant, la comparaison prédictive montre que le modèle naïf obtient de meilleures performances que le modèle AR(1) sur la période de test.

Ces résultats conduisent à distinguer deux aspects.

**Sur le plan descriptif et statistique**, le modèle AR(1) fournit une mesure simple de la persistance temporelle.

**Sur le plan prédictif**, les performances observées ne justifient pas de privilégier le modèle AR(1) par rapport au modèle naïf.

Il convient également de rappeler que l'analyse est globale.

Les résultats ne permettent pas de caractériser individuellement la persistance des retards sur chaque liaison.

Enfin, les relations observées ne constituent pas des preuves de causalité.

## 11. Articulation avec les autres analyses du projet

### 11.1. Complémentarité avec l'étude de la saisonnalité

L'étude de la saisonnalité des retards est prise en charge dans un autre volet du projet RailInsight-SNCF.

Notre contribution se concentre sur la dépendance entre deux mois consécutifs, tandis que l'analyse saisonnière cherche à caractériser les variations récurrentes selon les périodes de l'année.

Ces deux approches sont complémentaires.

En effet, le modèle AR(1) estimé ici ne prend pas explicitement en compte les effets saisonniers.

Les résultats de l'étude de la saisonnalité pourront donc être rapprochés de ceux de notre analyse afin de mieux comprendre la dynamique globale des retards.

Il ne s'agit pas de reproduire le travail consacré à la saisonnalité, mais de situer notre contribution dans l'ensemble du projet.

### 11.2. Complémentarité avec les autres analyses descriptives

Les analyses descriptives du projet peuvent mettre en évidence des différences selon les périodes, les caractéristiques des circulations ou les liaisons.

Notre approche apporte une dimension supplémentaire en étudiant la dépendance temporelle de l'indicateur global.

Elle ne remplace pas ces analyses et ne prétend pas expliquer à elle seule les causes des retards.

## 12. Limites et perspectives

### 12.1. Limites de l'agrégation globale

L'agrégation des données permet de construire un indicateur synthétique, mais elle peut masquer des différences entre liaisons.

Certaines liaisons pourraient présenter une forte persistance, tandis que d'autres pourraient connaître des fluctuations moins structurées.

Ces différences ne peuvent pas être identifiées à partir du seul modèle global.

### 12.2. Analyse par liaison

Une extension possible consisterait à construire une série temporelle distincte pour chaque liaison.

Cela permettrait de comparer les coefficients de persistance et d'identifier d'éventuelles différences.

Cependant, une telle extension nécessiterait :

- de vérifier la disponibilité des observations pour chaque liaison ;
- de contrôler la continuité temporelle des séries ;
- de gérer les mois manquants ;
- de tenir compte des volumes de circulation ;
- d'évaluer séparément les modèles.

Cette extension ne fait pas partie du périmètre actuel et n'est pas indispensable pour répondre à notre question principale.

### 12.3. Comparaison d'autres modèles

D'autres approches pourraient être évaluées, notamment des modèles autorégressifs d'ordre supérieur ou des modèles ARIMA.

Leur intérêt devrait être apprécié à partir de leurs performances sur des données non utilisées pour l'estimation.

### 12.4. Analyse des différents seuils de retard

Il serait également possible de construire trois séries globales correspondant aux retards supérieurs à 15, 30 et 60 minutes.

Cela permettrait de comparer la persistance des retards selon leur gravité.

Ces séries devraient être calculées séparément, sans additionner les indicateurs cumulatifs.

### 12.5. Évaluation prédictive plus approfondie

L'évaluation actuelle repose sur les douze derniers mois.

Une analyse complémentaire pourrait utiliser plusieurs fenêtres chronologiques d'entraînement et de test afin d'étudier la stabilité des performances.

Cette approche permettrait de mieux apprécier la robustesse des résultats.

## 13. Conclusion

Cette contribution propose une analyse reproductible de la persistance temporelle des retards TGV à partir des données mensuelles SNCF / AQST.

Elle repose sur trois choix méthodologiques principaux :

1. Utiliser le nombre de trains en retard de plus de 15 minutes comme indicateur de référence.
2. Construire un taux global mensuel à partir des effectifs agrégés, toutes liaisons étudiées confondues.
3. Étudier la dépendance temporelle à l'aide d'un modèle AR(1), puis comparer ses prévisions à celles d'un modèle naïf.

L'estimation du coefficient autorégressif suggère une persistance positive modérée des taux globaux mensuels.

Toutefois, le modèle AR(1) ne présente pas de meilleures performances prédictives que le modèle naïf sur la période de test considérée.

Cette distinction entre **caractérisation de la persistance** et **qualité de la prévision** constitue un résultat important de l'étude.

Le travail fournit ainsi une base statistique interprétable et reproductible, accompagnée d'un notebook d'analyse, de fonctions Python testées et d'un tableau de bord interactif.

Il complète les autres contributions du projet RailInsight-SNCF, notamment l'étude de la saisonnalité, sans se substituer à elles.