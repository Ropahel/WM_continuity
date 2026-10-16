# Plugin Openplanet

Ce dossier est réservé à la partie Trackmania/Openplanet du collecteur. Aucun
code de plugin n'a encore été ajouté ; le projet établit pour l'instant le
contrat de données côté Python.

Le plugin devrait exposer les mesures convenues lorsqu'elles sont disponibles :
vitesse, steer, gas, brake, gear et RPM. Il devrait aussi exposer des
événements fiables de run (départ, arrivée, reset) si l'API Openplanet le
permet. Le collecteur doit conserver des commandes explicites de début,
fin et reset comme solution de repli.

Le transport et le format des messages ne sont pas encore choisis. Avant
d'implémenter l'adaptateur, vérifier les unités de l'API, sa fréquence
d'échantillonnage et la sémantique des horodatages disponibles. Si aucun temps
de jeu ni numéro de frame n'est fourni, Python horodatera localement la
réception des mesures.
