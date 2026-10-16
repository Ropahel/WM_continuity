# Architecture et frontières expérimentales

Ce document décrit les responsabilités visées, sans imposer d'architecture de
réseau. Le projet doit permettre de comparer des encodeurs, prédicteurs,
encodages temporels et positionnels, losses et méthodes d'entraînement.

## Flux du modèle

```text
séquence passée d'images ──> encodeur visuel ──┐
                                               ├──> fusion ──> z(t)
séquence passée de télémétrie ─> encodeur télémétrique ┘          │
                                                                  ├─> policy ─> a(t)
                                                                  └─> prédicteur(z(t), a(t))
                                                                          │
                                                                       z_hat(t+1)
```

Pendant l'entraînement du World Model, un passage de l'encodeur sur la fenêtre
d'observations suivante fournit la cible latente `z(t+1)`. L'encodeur et le
prédicteur sont entraînés conjointement ; la cible du prédicteur reste dans
l'espace latent. Cette conception initiale n'exige pas de décodeur d'image ni
de télémétrie.

En jeu, la policy et le prédicteur peuvent avancer dans l'espace latent sans
encoder chaque image. Lorsque de nouvelles observations sont disponibles,
l'encodeur peut recalibrer l'état latent. La fréquence et le déclenchement de
ce recalibrage restent des choix expérimentaux.

## Composants remplaçables

- **Encodeur** : reçoit uniquement un historique d'observations se terminant à
  l'instant courant. Il pourra combiner un encodeur visuel, un encodeur de
  télémétrie, une agrégation temporelle et des encodages de position ou de
  temps. Ce sont des options à comparer, pas une architecture imposée.
- **Prédicteur** : reçoit l'embedding courant et l'action (ou un historique
  d'actions si une expérience ultérieure le justifie) et prédit un embedding
  futur.
- **Losses** : termes sélectionnables et pondérables indépendamment. Chaque
  expérience enregistre leurs noms, paramètres et poids.
- **Policy** : transforme l'état latent courant en commandes de steering,
  gas et brake.
- **Procédure d'entraînement** : WM et policy sont deux étapes distinctes. La
  policy pourra ensuite être entraînée par imitation ou par une méthode
  génétique/évolutionnaire.

Les variantes devront être sélectionnées par nom et paramètres dans la
configuration, résolues par un registre et sauvegardées avec chaque
expérience. Ajouter une variante ne devrait pas nécessiter de modifier le
collecteur ni le dataset brut.

## Causalité et évaluation

L'encodeur de l'état courant ne doit jamais recevoir d'image ni de télémétrie
postérieure à son instant d'ancrage. Un passage de l'encodeur servant à la
cible peut utiliser la fenêtre suivante pour calculer la loss, mais cette
cible n'est jamais une entrée de l'encodeur courant ni de la policy.

Les ensembles d'entraînement, de validation et de test sont séparés par run
entier. Les métriques de prédiction du WM doivent être rapportées séparément
des performances de conduite : une meilleure loss latente ne garantit pas une
meilleure conduite.

## Ablations de télémétrie

La télémétrie brute est toujours enregistrée lorsqu'elle est disponible. La
configuration du modèle sélectionne les mesures utilisées, y compris une
sélection vide pour tester une entrée image seule. Les ablations ne doivent
pas supprimer de champs des enregistrements bruts.

## Résultats d'expérience

Chaque dossier d'expérience devra contenir la configuration résolue, les
références aux données et aux splits, la révision du code si elle est
disponible, la graine aléatoire, les métriques et les checkpoints. Le format
final des dossiers et des checkpoints sera défini avec le code d'entraînement.
