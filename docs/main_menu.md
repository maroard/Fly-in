# `src/ui/menus/main_menu.py` — fonctionnement

Ce document décrit le menu principal, les panneaux de simulation, la sélection des mouvements et les commandes de lecture. Les liens renvoient au code plutôt qu'à des numéros de lignes qui changent lors des modifications.

## Construction et état partagé

[`Application._build_ui()`](../src/application.py) crée le `KeyboardTerminalApp` (sous-classe de `TerminalApp`), appelle [`build_main_menu(application)`](../src/ui/menus/main_menu.py), puis installe le menu principal. Celui-ci s'appelle `main`, porte le titre `Main Menu`, possède une largeur de menu de 40 et utilise la présentation `overlay`.

L'application conserve le graphe, le renderer, le simulateur, le playback, les panneaux et le handle du rappel périodique. Le menu orchestre l'interface ; [`Simulator`](../src/simulation/simulator.py) calcule les tours et [`Playback`](../src/simulation/playback.py) gère les positions visibles, l'animation et le retour en arrière.

`shown_turn_index` désigne le tour affiché dans Simulation. Pendant la lecture, il suit `playback.turn_index`. Après la fin, la navigation dans l'historique peut les dissocier. Reprendre la lecture ou revenir en arrière les synchronise à nouveau.

## Commandes

| Touche | Portée | Comportement |
| --- | --- | --- |
| `m` / `M` | Globale | Afficher ou masquer le menu principal. |
| `Tab` | Panneaux | Changer le panneau ayant le focus. |
| `Space` | Graphe ou Simulation, en mode `step_by_step` | Démarrer le mouvement en attente. Une nouvelle pression pendant l'animation est ignorée. |
| `Shift+Space` / `Backspace` | Globale, avec un playback en mode `step_by_step` | Annuler l'animation en cours ou, en l'absence d'animation, annuler le dernier mouvement terminé. |
| `↑` / `↓` | Simulation, après la fin | Sélectionner une ligne et reconstruire l'état juste après ce mouvement. Pendant la lecture pas à pas, les flèches ne changent pas la sélection. |
| `Shift+←` / `Shift+→` | Simulation, après la fin | Afficher le tour précédent ou suivant et sélectionner sa première ligne. |

`Shift+Space` et `Backspace` fonctionnent indépendamment du panneau focalisé, y compris depuis Movement ou Stats, et lorsque le menu est affiché. Le retour en arrière ne fait rien avant le premier mouvement, sans playback ou en mode `one_shot`. Après la fin, il rouvre la lecture pas à pas en annulant le dernier mouvement réel, même si l'utilisateur consultait un autre tour dans l'historique.

Le retour en arrière restaure les positions de **tous** les drones, les compteurs, le tour courant et le mouvement en attente. Il traverse les limites de tours et conserve les positions sur les connexions. `Space` permet ensuite de rejouer le mouvement annulé depuis le temps courant, sans relancer le calcul de la simulation.

### Réception de Shift+Space

[`KeyboardTerminalApp`](../src/ui/terminal_app.py) active la désambiguïsation du protocole clavier Kitty (`CSI > 1 u`) au début de la boucle interactive, après l'entrée dans l'écran alternatif. Il restaure l'état précédent (`CSI < u`) à la sortie, y compris si la boucle lève une exception. Tuiloom décode déjà les touches CSI-u ; il lui manquait l'activation du protocole côté terminal.

Le raccourci `Shift+Space` dépend du support de ce protocole par le terminal. Le GNOME Terminal 3.44 / VTE 0.68 installé ici transmet un espace simple pour `Space` et `Shift+Space`. L'application ne peut pas retrouver un modificateur que le terminal ne transmet pas : dans ce cas, utiliser **`Backspace`** pour revenir en arrière. Les deux raccourcis appellent le même callback global. Voir le [protocole clavier Kitty](https://sw.kovidgoyal.net/kitty/keyboard-protocol/) pour les encodages et la pile de restauration du mode clavier.

Les commandes `Run simulation`, `Settings` et `Credit` lancent respectivement une nouvelle lecture, le sous-menu de réglages et le message de crédit.

## Disposition des panneaux

Trois panneaux permanents sont créés au lancement d'une simulation. Movement s'ajoute lorsqu'un mouvement est sélectionné :

```text
┌──────────────────────┬──────────────────┐
│ Graph                │ Simulation       │
│                      ├──────────────────┤
│                      │ Movement         │
│                      ├──────────────────┤
│                      │ Stats            │
└──────────────────────┴──────────────────┘
```

`update_layout()` construit les lignes de cette disposition. La répétition du panneau Graph dans la colonne de gauche lui permet d'occuper toute la hauteur. Sans Movement, la colonne de droite contient seulement Simulation puis Stats.

| Panneau | Contenu et rôle |
| --- | --- |
| Graph | Contenu animé à 20 FPS : `renderer.render(size, frame, playback.snapshot())`. Taille minimale demandée de 40 × 20 ; poids de largeur de 3. |
| Simulation | Une ligne sélectionnable `D-<id>-<destination>` par mouvement du tour affiché, en-tête `Turn <number>:` en gras et sélection en vidéo inverse. Poids de largeur de 2 et poids de hauteur de 2. |
| Movement | Drone sélectionné, position visible, métadonnées de la zone ou connexion et autres drones au même endroit lorsqu'il y en a. Poids de largeur de 2. |
| Stats | Compteurs du tour et résultats finaux via `stats_lines(playback)`. |

Les panneaux permanents sont réutilisés lors d'une nouvelle simulation. Movement est retiré à la désélection ou au redémarrage, puis recréé si une sélection est nécessaire. Un changement de carte retire tous les panneaux dans [`map_menu.py`](../src/ui/menus/map_menu.py).

## Sélection et panneau Movement

`turn_rows(playback)` conserve l'ordre des mouvements du tour. Chaque `SelectableItem` utilise l'identifiant du drone comme `value` et `key`. En mode `one_shot`, les lignes restent désactivées jusqu'à la fin. En mode `step_by_step`, seule la ligne du mouvement courant est activée pendant la lecture : les flèches ne permettent pas de parcourir les autres mouvements. Après la fin, toutes les lignes deviennent sélectionnables.

`on_selection_change(context)` distingue trois cas :

- Une sélection vide efface la relecture et retire Movement.
- Pendant la lecture, une sélection met en évidence le drone dans l'état réel, sans déplacer le curseur de lecture.
- Après la fin, `select_movement(shown_turn_index, context.index)` reconstruit les positions immédiatement après la ligne sélectionnée, puis actualise Movement.

L'index de la ligne identifie le mouvement exact ; le `value` identifie le drone.

### Sélection automatique en mode pas à pas

`sync_step_selection(playback)` sélectionne automatiquement le mouvement actif ou en attente. Il s'exécute dès le lancement, au démarrage d'un mouvement, après chaque mouvement terminé et après un retour en arrière.

Ainsi, le premier mouvement et son panneau Movement sont visibles avant toute pression sur `Space`. Pendant l'animation, la ligne active reste sélectionnée. Une fois le mouvement terminé, la sélection passe au prochain mouvement en attente, dans le même tour ou dans le suivant. Après le dernier mouvement, la dernière ligne reste sélectionnée et Movement reste affiché.

La synchronisation détache temporairement le callback de sélection : la sélection automatique du dernier mouvement doit montrer l'état réel final, sans déclencher une relecture historique. Elle rétablit ensuite le callback, efface une éventuelle relecture, met en évidence le drone courant et actualise Movement.

Pendant la lecture pas à pas, la sélection est pilotée automatiquement. `Space` et les raccourcis de retour (`Shift+Space` ou `Backspace`) déplacent le curseur de lecture ; les flèches ne changent pas le mouvement sélectionné. Revenir en arrière après la fin rétablit ce verrouillage jusqu’à la prochaine fin de lecture.

### Informations affichées

`update_movement_panel(playback)` utilise l'instantané visible du playback. Pour un drone immobile, il lit `visual.end` ; pendant une animation, il lit `visual.start`. La position affichée reste donc celle du départ jusqu'à la fin de l'animation.

Pour une zone, il affiche son nom et tous les champs de `ZoneMetadata` : `zone_type`, `color` et `max_drones`. Pour une connexion, il affiche son nom, sa direction `source → target` et les champs de `ConnectionMetadata`, notamment `max_link_capacity`. Les valeurs sont obtenues par `model_dump()`, valeurs par défaut incluses.

Les autres drones sont ceux dont la position visible correspond à la même zone ou à la même connexion ; le drone sélectionné est exclu. La ligne `Other drones` apparaît uniquement si cette liste n'est pas vide. En relecture, ces informations décrivent l'état historique sélectionné.

## Statistiques et barre d'état

`stats_lines(playback)` affiche le tour de lecture, le nombre de drones livrés, les mouvements terminés dans le tour et le nombre total de tours. Les drones livrés sont comptés à partir des positions visibles au hub final avec une progression de 1. Les mouvements terminés sont issus de `completed_movements`, moins ceux des tours précédents.

Après la fin, deux lignes supplémentaires indiquent la moyenne des numéros de tour d'arrivée et le nombre total de mouvements calculés. Le « Total path cost » correspond à ce nombre de mouvements.

La relecture historique modifie les positions visibles, mais ne modifie pas les compteurs de lecture. Le retour en arrière en mode pas à pas modifie réellement ces compteurs et actualise Stats immédiatement.

`render_status(width)` retourne `NO MAP` sans renderer, `READY` avant la lecture, `RUNNING` pendant celle-ci et `DONE` après la fin. Il ajoute les raccourcis pertinents selon le mode et le focus, dont `Shift+Space` et `Backspace` en mode pas à pas, quel que soit le focus et même après la fin.

La version complète indique la carte sous la forme `parent/fichier`. Si elle dépasse la largeur mesurée par `display_width`, une version sans carte est utilisée, puis une version compacte. Cette dernière ne garantit pas que tous les raccourcis restent visibles sur un terminal étroit. Les changements de lecture déclenchent explicitement `menu.refresh_status_bar()`.

## Lancement et horloge de lecture

`run_simulation(context)` exige un renderer, crée le simulateur avec le mode de routage choisi et calcule tous les tours avant de démarrer la lecture. Une `RuntimeError` affiche une alerte et laisse la lecture précédente en place.

Après calcul réussi, il annule l'ancien rappel périodique, installe le nouveau playback, remet le tour affiché à zéro, cache le menu, configure les panneaux et remplace les commandes de Graph et Simulation. Il établit la disposition et, en mode pas à pas, sélectionne immédiatement le premier mouvement.

`on_tick(frame)` s'exécute à 20 FPS et transmet `frame.elapsed` à `playback.advance()`. Lors d'un changement de tour ou du passage à l'état terminé, il reconstruit Simulation. Lorsqu'un mouvement se termine, il synchronise la sélection en mode pas à pas, actualise Stats et Movement, puis rafraîchit la barre d'état. Graph utilise séparément les instantanés pour dessiner l'animation.

Le rappel reste installé après la fin ; `advance()` retourne alors sans avancer. Cela permet de reprendre la lecture après `Shift+Space`. Une nouvelle simulation ou un changement de carte annule ce rappel.

## Hypothèses et limites

- La construction des lignes, de l'en-tête et des statistiques suppose au moins un tour calculé avec des mouvements accessibles.
- Le retour en arrière restaure l'état en parcourant les mouvements depuis les positions initiales ; il ne recalcule pas les itinéraires.
- Les touches de navigation entre tours sont enregistrées dès le lancement mais restent sans effet avant la fin.
- La durée d'un mouvement vient de `Application.seconds_per_movement` : 2 s pour `low`, 1 s pour `medium`, 0,4 s pour `high`, ou la durée personnalisée.
