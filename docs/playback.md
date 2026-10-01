# `src/simulation/playback.py` — fonctionnement détaillé

Ce document décrit **le fichier dans son état actuel**. [`playback.py`](../src/simulation/playback.py) transforme des tours déjà calculés en positions visibles au fil du temps. Il ne décide pas des trajets ni des contraintes de circulation : ces décisions viennent du [`Simulator`](../src/simulation/simulator.py). Il fournit des instantanés à [`renderer.py`](renderer.md) et des commandes à [`main_menu.py`](main_menu.md).

## 1. Contrat d'entrée et de sortie

Le constructeur `Playback(graph, turns, mode, seconds_per_movement)` reçoit un [`Graph`](../src/domain/graph.py), une liste de [`Turn`](../src/simulation/turn.py), un mode littéral `one_shot` ou `step_by_step`, et la durée visuelle d'un mouvement en secondes. Chaque `Turn` possède `number` et une liste ordonnée de `Movement(drone_id, destination)`.

`destination` désigne soit une zone présente dans `graph.zones`, soit une liaison sous la forme `<zone_name1>-<zone_name2>` utilisée pour entrer dans une zone restreinte. Dans ce dernier cas, le drone reste visuellement au milieu de la liaison jusqu'à un mouvement ultérieur vers la zone cible. Les noms de zones interdisent le tiret ; le simulateur émet le nom de liaison dans l'ordre de `Connection.zone_name1` et `zone_name2`.

Les principales sorties publiques sont `snapshot()` pour le dessin, `advance(elapsed)` pour l'horloge, `start_next_movement()` pour le mode pas à pas et `select_movement(...)` pour la relecture après la fin.

## 2. Types de données (l. 11–32)

| Type | Champs | Sens |
| --- | --- | --- |
| `Location` | `zone`, `connection`, `source`, `target` | Position logique. Pour une zone, `zone` suffit. Pour une liaison, `connection` est son nom et `source`/`target` identifient ses extrémités. Les quatre champs ont `None` comme valeur initiale. |
| `VisualDrone` | `start`, `end`, `progress` | Position visuelle entre deux `Location`. `progress` vaut normalement de 0 à 1 ; le renderer choisit une cellule entre les deux. |
| `PlaybackSnapshot` | `positions`, `selected_drone_id`, `turn_index`, `completed_movements`, `finished` | Copie cohérente de l'état utile à l'interface et au renderer. `positions` associe chaque identifiant de drone à un `VisualDrone`. |

Ces trois classes sont des `@dataclass(frozen=True)` : leurs attributs ne peuvent pas être réaffectés. Le dictionnaire `positions` contenu dans l'instantané reste, lui, un objet Python mutable ; `snapshot()` en crée un nouveau à chaque appel.

## 3. État interne de `Playback` (l. 35–60)

| Attribut | Valeur initiale | Rôle |
| --- | --- | --- |
| `graph`, `turns`, `mode`, `seconds_per_movement` | Arguments | Données de référence et cadence. |
| `turn_index` | `0` | Index du tour actuellement atteint, commençant à zéro. Sur la dernière image, il reste l'index du dernier tour. |
| `completed_movements` | `0` | Nombre de `Movement` entièrement animés depuis le début. Un groupe automatique de plusieurs mouvements l'incrémente de la taille du groupe. |
| `finished` | `not turns` | Vrai immédiatement si aucun tour n'est fourni, ou après le dernier groupe. |
| `last_elapsed` | `0.0` | Dernier temps fourni à `advance`, utilisé pour l'interpolation et pour dater un `Space`. |
| `selected_drone_id` | `None` | Drone mis en évidence par le renderer, notamment lors d'une relecture. |
| `_locations` | Tous les drones au hub de départ | Position logique définitive après les mouvements achevés. |
| `_replay_locations` | `None` | État reconstruit pour regarder un ancien mouvement, distinct de `_locations`. |
| `_active` | Liste vide | Tuples `(drone_id, start, end)` des mouvements en cours d'animation. |
| `_active_since` | `0.0` | Temps de départ du groupe `_active`. |
| `_next_movement` | `0` | Index du prochain mouvement à démarrer dans le tour courant. |
| `_started` | `False` | Indique que le mode automatique a déjà démarré son premier tour. |
| `_lock` | `threading.Lock()` | Protège les lectures et modifications de ces états. |

`_initial_locations()` (l. 166–170) crée un `dict` avec les identifiants `1` à `graph.nb_drones`, chacun placé dans `graph.start_hub.name`.

## 4. Transformation d'un `Movement` : `_motion` (l. 172–200)

`_motion(movement, locations=None)` lit la position de départ du drone dans le dictionnaire fourni, ou dans `_locations` par défaut, puis calcule sa `Location` d'arrivée. Il retourne `(drone_id, start, end)` **sans modifier** le dictionnaire.

- Si `movement.destination` est une clé de `graph.zones`, l'arrivée est `Location(zone=destination)`.
- Sinon, la destination est interprétée comme un nom de liaison. Le départ doit être une zone (`start.zone` non nul), faute de quoi un `ValueError` est levé. La fonction cherche dans `graph.connections` la première liaison dont `zone_name1-zone_name2` correspond exactement à la destination. La cible est l'autre extrémité de la liaison ; l'arrivée est `Location(connection=destination, source=start.zone, target=target)`.

La recherche emploie `next(...)` sans valeur de secours : une destination de liaison absente provoque `StopIteration`. Le code suppose que les `Turn` passés à `Playback` respectent la sortie du simulateur et que l'identifiant du drone figure dans `locations`.

La progression de `_locations` se fait uniquement **à la fin** de l'animation : le mouvement en cours est porté par `_active` et projeté par `snapshot()`. Cette séparation explique qu'un drone puisse être visuellement entre deux endroits tout en conservant son dernier emplacement logique achevé.

## 5. Mode `one_shot` : un tour en parallèle

Au premier `advance(elapsed)`, si le mode est `one_shot`, `_started` passe à vrai et `_start_turn(elapsed)` crée un tuple actif pour **chaque** mouvement du tour courant (l. 108–110 et 159–164). Tous ces mouvements partagent `_active_since` : ils avancent donc ensemble, même si le tour contient plusieurs drones.

L'exécution de `advance` (l. 102–134) est la suivante :

1. Sous verrou, mémoriser `elapsed` dans `last_elapsed`.
2. Si `finished`, retourner `False` immédiatement.
3. En mode automatique, lancer le premier tour si nécessaire.
4. Tant qu'un groupe actif a atteint `active_since + seconds_per_movement`, inscrire toutes ses arrivées dans `_locations`, augmenter `completed_movements` et `_next_movement` du nombre de mouvements actifs, puis vider `_active`.
5. Si `_next_movement` atteint le nombre de mouvements du tour : terminer la lecture si c'était le dernier tour ; sinon avancer `turn_index`, réinitialiser `_next_movement`, signaler `page_changed=True` et démarrer le tour suivant en automatique.
6. Retourner `page_changed`.

Le tour suivant démarre à `next_start = _active_since + seconds_per_movement`, **pas** forcément à l'heure du tick courant. La boucle `while` peut donc absorber plusieurs tours si l'interface reçoit un grand saut de temps. Le retour booléen reste simplement `True` dès qu'au moins une page a changé. Terminer le dernier tour sans changer de page renvoie `False` ; `main_menu.py` détecte cette fin en comparant `finished` avant et après l'appel.

Exemple avec deux mouvements au tour 1, un au tour 2, et une durée de 1 s :

| Temps `elapsed` | Tour | Mouvements achevés | Effet visible |
| --- | ---: | ---: | --- |
| `0.0` | 0 | 0 | Les deux premiers drones commencent ensemble. |
| `0.5` | 0 | 0 | Leurs `VisualDrone.progress` valent `0.5`. |
| `1.0` | 1 | 2 | Le tour 1 s'achève ; le mouvement du tour 2 démarre. |
| `2.0` | 1 | 3 | La lecture est terminée. |

## 6. Mode `step_by_step` : un mouvement par commande

`advance` ne démarre pas automatiquement de mouvement dans ce mode. `start_next_movement()` (l. 90–100) vérifie sous verrou que le mode est bien `step_by_step`, que la lecture n'est pas finie et qu'aucun mouvement n'est déjà actif. S'il peut agir, il prend `turns[turn_index].movements[_next_movement]`, crée une liste `_active` à un seul élément, date son départ à `last_elapsed` et renvoie `True`. Sinon, il renvoie `False` sans modifier l'état.

Le temps initial d'un `Space` est donc celui du **dernier tick reçu**, pas l'instant système exact de l'appui. Les appuis répétés pendant l'animation sont ignorés. Quand `advance` constate la fin de ce mouvement, il augmente `_next_movement`. Si le tour comporte encore des mouvements, il laisse `_active` vide jusqu'au prochain `Space`. Si c'était le dernier du tour, il change de tour ; dans ce mode, il attend également un nouveau `Space` avant de commencer le premier mouvement du suivant.

Le mode pas à pas agit sur la **présentation des mouvements déjà calculés**. Il n'appelle jamais `Simulator.step()` et ne recalcule aucun trajet.

## 7. Instantanés et interpolation : `snapshot()` (l. 136–157)

`snapshot()` prend le verrou, puis choisit `_replay_locations` si une relecture est active, `_locations` sinon. Il crée d'abord, pour chaque drone, `VisualDrone(location, location, 1.0)` : un drone immobile est représenté par un trajet de longueur nulle, entièrement accompli.

S'il existe des mouvements actifs **et** qu'aucune relecture n'est active, il calcule leur progression par `(last_elapsed - _active_since) / seconds_per_movement`, bornée à `[0.0, 1.0]`, et remplace les entrées correspondantes par `VisualDrone(start, end, progress)`. Il renvoie ensuite les positions et les compteurs dans `PlaybackSnapshot`.

Le verrou permet à un rendu animé exécuté sur un autre thread d'obtenir positions et compteurs cohérents, même si le callback du menu fait évoluer la lecture. Le verrou n'est pas exposé au renderer : celui-ci travaille sur l'instantané reçu. Le calcul suppose une durée strictement positive ; les réglages de l'application imposent actuellement des durées positives.

## 8. Relecture après la fin (l. 62–89)

`select_drone(drone_id)` modifie uniquement l'identifiant à mettre en évidence. Il ne reconstruit aucune position et n'est pas le mécanisme principal du panneau Simulation actuel.

`select_movement(turn_index, movement_index)` exige `finished=True`, sinon lève `ValueError("Replay needs a finished movement")`. Il choisit le mouvement ciblé, recrée les positions initiales, puis **rejoue logiquement** tous les mouvements des tours précédents et ceux du tour demandé **jusqu'à l'index choisi inclus**. Pour chaque mouvement, il appelle `_motion(prior, locations)` puis remplace la position du drone par l'arrivée. Enfin, il range ce dictionnaire dans `_replay_locations` et affecte `selected_drone_id` au drone du mouvement choisi.

Cette reconstruction donne un état « après la ligne sélectionnée ». Elle suit l'ordre des lignes de `Turn.movements`, même si le mode automatique avait animé tous les mouvements d'un tour simultanément. Les drones dont le mouvement se trouve plus bas dans le même tour restent à leur position précédente dans cette vue. La relecture n'altère ni `_locations`, ni `turn_index`, ni `completed_movements`, ni `finished` : l'horloge et les métriques demeurent celles de la simulation achevée.

`clear_replay()` remet `_replay_locations` et `selected_drone_id` à `None` ; le prochain instantané montre donc les positions finales. Lorsqu'une sélection du panneau Simulation est effacée ou que ses lignes sont reconstruites, `main_menu.py` l'appelle.

Une liaison vers une zone restreinte reste une `Location(connection=..., source=..., target=...)` dans la relecture jusqu'au mouvement ultérieur qui arrive explicitement dans la zone. Le renderer la place au milieu de la liaison.

## 9. Invariants, préconditions et détails à retenir

- `turn_index` et `_next_movement` sont des **index à partir de zéro** ; `Turn.number` est destiné à l'affichage et vaut normalement `index + 1` selon le simulateur.
- `completed_movements` compte les **entrées de `Turn.movements` terminées visuellement**, y compris l'entrée sur une liaison restreinte et l'arrivée ultérieure dans la zone.
- `advance` attend un temps `elapsed` compatible avec les précédents appels ; le fichier n'effectue pas lui-même de validation de monotonie.
- `start_next_movement()` indexe directement la liste du tour. Les tours vides ne sont pas gérés explicitement ici ; le simulateur normal produit des tours utiles ou signale un blocage.
- Les méthodes publiques modifiant l'état et `snapshot()` utilisent le même verrou. `_start_turn`, `_initial_locations` et `_motion` sont des auxiliaires appelés dans ce protocole.
- La position sur une liaison est une donnée logique ; le **milieu exact en cellules** est calculé plus tard par `Renderer._location_position`.

## 10. Repères dans le code

| Lignes | Responsabilité |
| --- | --- |
| 11–32 | Types de positions et instantané |
| 35–60 | Initialisation de l'état de lecture |
| 62–89 | Sélection et reconstruction pour la relecture |
| 90–100 | Démarrage manuel d'un mouvement |
| 102–134 | Avance temporelle, fin de mouvement et changement de tour |
| 136–157 | Instantané et interpolation |
| 159–170 | Démarrage d'un tour et positions initiales |
| 172–200 | Conversion d'un mouvement en trajet logique |
