# Checkpoints et versions des modèles

Ce document distingue les sauvegardes qui permettent de reprendre un
entraînement des modèles nommés que l'on souhaite conserver, comparer ou
utiliser pour jouer. Un fichier de checkpoint n'est pas une expérience : il
doit toujours indiquer de quelle expérience et de quelles variantes il
provient.

## Trois identifiants complémentaires

- **`experiment_id`** identifie un entraînement donné : configuration résolue,
  dataset et splits, graine et révision du code.
- **`architecture_id`** identifie une variante de sous-modèle : rôle
  (`encoder`, `predictor` ou `policy`), nom d'architecture, paramètres et
  révision de l'implémentation.
- **`checkpoint_id`** identifie un instantané précis de poids entraînés. Deux
  checkpoints peuvent avoir le même `architecture_id` et des poids différents.

Les identifiants sont stockés dans des métadonnées, pas déduits uniquement du
nom de fichier. Un manifeste doit aussi indiquer la version du schéma de
checkpoint, la configuration de modèle résolue, la sélection et la
normalisation de télémétrie, les données/splits utilisés, le compteur global
d'étapes et, si disponible, le commit Git.

## Entraînement : sauvegarde périodique pour reprise

Les sauvegardes automatiques servent d'abord à reprendre l'entraînement après
un arrêt. Elles ne sont pas créées à chaque époque. Leur cadence est
configurable et pourra être exprimée en nombre d'étapes d'optimisation (ou en
temps écoulé) une fois la boucle d'entraînement définie.

Structure envisagée pour un entraînement :

```text
runs/
└── <experiment_id>/
    ├── config.resolved.yaml
    ├── experiment.json
    ├── metrics/
    └── checkpoints/
        ├── latest_resume.pt
        └── periodic/
            ├── step_<global_step>.pt
            └── ...
```

`latest_resume.pt` est remplacé à chaque sauvegarde périodique. Les instantanés
numérotés sont optionnels et leur nombre conservé doit être configurable : la
cadence précise et la rétention restent à décider avec le volume réel des
modèles. La suppression automatique ne concerne jamais les modèles enregistrés
manuellement.

Un checkpoint de reprise contient au minimum :

- les états de poids de tous les modules de l'étape en cours ;
- l'état de l'optimiseur et, s'il est utilisé, celui du scheduler ;
- l'époque et le compteur global d'étapes ;
- les états aléatoires nécessaires à une reprise aussi reproductible que
  possible ;
- les identifiants d'expérience et d'architecture, la configuration résolue,
  la référence de dataset/splits et le schéma de checkpoint.

L'écriture se fait dans un fichier temporaire du même dossier, puis est
renommée en fichier final afin d'éviter de laisser `latest_resume.pt` à moitié
écrit en cas d'interruption.

## Entraînement conjoint du WM

L'encodeur et le prédicteur sont explorés comme des sous-modèles distincts,
avec leurs propres `architecture_id`. Toutefois, leurs poids sont entraînés
conjointement et dépendent l'un de l'autre : ils sont donc sauvegardés ensemble
dans un bundle de World Model. On ne doit pas remplacer seulement l'encodeur
ou le prédicteur par une variante provenant d'un autre checkpoint sans
validation explicite de compatibilité et réentraînement/évaluation.

Le manifeste du bundle garde les identifiants et configurations séparés des
deux sous-modèles. Cela permet de répondre à la fois à « quelle architecture
d'encodeur ? » et à « quel prédicteur a été entraîné avec elle ? ».

## Sauvegarde manuelle d'un modèle intéressant

Pendant un entraînement interactif, la commande terminal `save_model` demande
un nom lisible et enregistre un nouvel artefact immuable à partir des poids
actuellement en mémoire. Une sauvegarde ne remplace jamais silencieusement une
version existante. Exemple de bibliothèque :

```text
runs/
└── model_library/
    ├── wm_baseline/
    │   ├── v0001/
    │   │   ├── manifest.json
    │   │   └── world_model.pt
    │   └── v0002/
    │       ├── manifest.json
    │       └── world_model.pt
    └── policy_baseline/
        └── v0001/
            ├── manifest.json
            ├── world_model.pt
            └── policy.pt
```

Lors d'une étape WM, `world_model.pt` regroupe encodeur et prédicteur. Lors
d'une étape policy, l'artefact conserve la policy **et le WM exact** dont elle
dépend (encodeur et prédicteur), pour former un modèle jouable autonome. Le
bundle peut occuper plus d'espace, mais évite qu'une policy perde sa
dépendance si un checkpoint de travail est nettoyé ou déplacé.

Chaque `manifest.json` décrit le nom/version, les `checkpoint_id` et
`architecture_id`, l'expérience d'origine, les données et splits, les
configurations et losses, le compteur d'étapes, les métriques disponibles et
la référence au WM parent pour une policy. Les noms de modèle sont des labels
humains ; les identifiants et manifestes sont la source fiable pour comparer
les versions.

La commande manuelle sauvegarde les poids pour comparaison ou utilisation,
pas l'état d'optimiseur nécessaire à une reprise exacte. Pour continuer
l'entraînement, utiliser le checkpoint de reprise de l'expérience.

## Policy et compatibilité du WM

La policy reçoit `z(t)` ; le sens et la dimension de cet embedding dépendent du
WM qui l'a produit. Son manifeste doit donc référencer l'identifiant exact du
bundle WM. Charger la policy avec un autre WM est refusé par défaut, même si
les dimensions semblent identiques. Une expérience de transfert ou de
remplacement du WM doit être explicite et réévaluée.

Le WM et la policy peuvent avoir leurs propres variantes et versions, mais une
version de modèle destinée au jeu est un bundle cohérent avec toutes ses
dépendances. Les configurations et manifestes rendent les variantes
comparables sans confondre architecture, entraînement et poids sauvegardés.

## Éléments à décider lors de l'implémentation

- la cadence automatique et le nombre d'instantanés périodiques conservés ;
- la métrique de validation utilisée pour afficher des suggestions de modèle
  intéressant (sans sauvegarde automatique à la place de `save_model`) ;
- les interactions exactes de la commande `save_model` et les noms/version
  demandés à l'utilisateur ;
- le format sérialisé final et les migrations de versions de checkpoint.
