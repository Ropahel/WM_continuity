# Architecture et frontières expérimentales

Ce document décrit les responsabilités visées, sans imposer d'architecture de
réseau. Le projet doit permettre de comparer des encodeurs, prédicteurs,
encodages temporels et positionnels, losses et méthodes d'entraînement.

## Flux du modèle

```text
séquence passée d'images ──> encodeur visuel         ──┐
                                                       ├──> fusion ──> z(t)
séquence passée de télémétrie ─> encodeur télémétrique ┘                │
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
des dossiers, la reprise périodique et la commande de sauvegarde manuelle sont
définis dans [checkpoints.md](./checkpoints.md).

L'encodeur et le prédicteur étant entraînés conjointement, leurs poids sont
sauvegardés comme un World Model cohérent ; leurs variantes architecturales
restent identifiées séparément dans le manifeste. Une policy sauvegardée
référence exactement le checkpoint du WM avec lequel elle a été entraînée.

## État d'exécution et sûreté de commande

Le processus Python maintient un état explicite du cycle de vie du run :
`UNKNOWN`, `NOT_IN_MAP`, `READY`, `RUNNING`, `RESETTING`, `FINISHED` ou
`ABORTED`.
Initialement, début, fin, reset et abandon sont déclenchés explicitement par
l'utilisateur dans le collecteur. Les événements fiables du plugin pourront
mettre à jour cet état lorsqu'ils auront été vérifiés.

Quand un message frais indique que `ViewingPlayerState()` est nul, le
collecteur sait que la voiture n'est pas dans une map et peut entrer dans
`NOT_IN_MAP`. Une valeur non nulle ne permet pas, à elle seule, de distinguer
l'attente du départ, la conduite, l'arrivée ou le reset. L'absence de message
ou un heartbeat périmé indique `UNKNOWN`, pas `NOT_IN_MAP`. En cas d'état
inconnu ou de télémétrie devenue obsolète, le contrôle par la policy doit être
désactivé et la commande de sortie neutralisée ; une reprise nécessite un état
de run confirmé. Le détail du journal d'événements prévu pour ces transitions
est donné dans [data-format.md](./data-format.md).

La lecture des commandes physiques de la manette via Openplanet est une piste
à vérifier. Elle permettrait de conserver les actions du joueur pour
l'imitation, mais ne doit pas être présumée disponible. À défaut, il faudra
enregistrer les actions émises par le contrôleur Python et garder leur source
identifiée.

## Commandes terminal et journal de latents

Les commandes textuelles et les éventuels raccourcis clavier passent par un
même répartiteur. Le lecteur d'entrée transmet une demande à une file ; la
boucle responsable de l'état du run, du modèle et des writers l'applique à un
point sûr. Ainsi, la saisie n'interrompt pas la réception Openplanet ni le
contrôle et ne modifie pas les poids depuis un thread concurrent.

L'enregistrement des embeddings est désactivé par défaut. Une demande
`record_latents next_run` arme une seule capture complète ; si elle est lancée
pendant un run, `record_latents current_run` capture seulement la suite de ce
run. Le writer s'arrête à la frontière de run ou à la commande
`stop_latent_recording`. Les lignes contiennent l'embedding effectivement
émis, son timestamp et si le vecteur provient d'un recalibrage par l'encodeur
ou d'une propagation du prédicteur. Le format du flux est décrit dans
[data-format.md](./data-format.md).

L'écriture disque ne doit pas se trouver sur le chemin critique de l'inférence :
la boucle du modèle transmet des copies détachées des latents à un writer
asynchrone qui écrit par lots. La file doit être bornée et un débordement doit
produire une erreur visible (et arrêter proprement la capture si nécessaire),
pas perdre silencieusement des vecteurs. La commande terminal reçoit un
accusé indiquant si la capture est armée, démarrée, arrêtée ou en erreur.

Une commande clavier dédiée peut être ajoutée ultérieurement comme simple
déclencheur du même répartiteur. Les commandes terminal constituent le premier
chemin d'interaction à implémenter ; les hotkeys globales demandent une
attention supplémentaire au focus, aux conflits et à la prévention des
déclenchements répétés.
