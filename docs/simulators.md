# Choix et intégration des simulateurs

Le premier environnement de travail doit permettre des essais rapides et
déterministes. Push-T, AntMaze et « CUBE » sont des pistes, pas encore des
dépendances installées ni des interfaces vérifiées.

## Comparaison de travail

| Candidat | Type d'expérience | Ordre proposé | Décision préalable |
| --- | --- | ---: | --- |
| CUBE local | Petit environnement vectoriel contrôlé | 1 | Définir explicitement l'état, les actions, le but et les fins d'épisodes ; vérifier si le nom désigne aussi un benchmark précis |
| Push-T | Manipulation avec observations visuelles et temporelles | 2 | Choisir l'implémentation précise, sa licence, son API, son rendu et ses versions |
| AntMaze | Navigation et données de trajectoires, potentiellement hors ligne | 3 | Choisir benchmark, source/version des données, API, moteur et modalités d'observation |

Cette progression est une recommandation pratique, pas une affirmation que ces
benchmarks ont des dépendances interchangeables. Il ne faut pas installer
leurs piles simultanément avant d'avoir retenu un candidat.

## Interface commune

Chaque environnement est encapsulé par un adaptateur interne qui fournit :

- `reset(seed=...)` ;
- `step(action)` avec observation, reward éventuelle, `terminated`,
  `truncated` et informations ;
- espaces d'observation et d'action ;
- identification de l'environnement, de la tâche et des versions ;
- un mode de rendu explicite (`None` pour les expériences headless quand
  possible).

Gymnasium fournit l'interface de base du projet. L'adaptateur peut appeler une
API native ou un paquet de benchmark spécifique, mais le reste du code ne doit
pas dépendre de cette API particulière.

## Politique de dépendances

Le socle inclut seulement PyTorch CPU, Gymnasium, NumPy, PyYAML et TensorBoard,
plus pytest/Ruff pour le développement. Les extras de benchmark ne seront
ajoutés qu'après vérification de l'installation, de la compatibilité Python,
du rendu et des versions de données du candidat retenu.

Les datasets de trajectoires du benchmark ne doivent pas être remplacés par
des données réenregistrées sans le noter : consigner source, version, licence,
prétraitement et split. Pour le premier environnement contrôlé, un petit format
NumPy `.npz` suffit ; choisir ensuite un stockage plus spécialisé seulement
si taille, débit ou API du benchmark le justifient.
