# `src/rendering/renderer.py` — fonctionnement détaillé

Ce document décrit **le fichier dans son état actuel**. [`renderer.py`](../src/rendering/renderer.py) convertit un graphe et, éventuellement, un [`PlaybackSnapshot`](playback.md) en lignes de texte colorées destinées à un panneau terminal. Il ne fait pas avancer le temps et ne modifie pas les tours calculés.

## 1. Entrées, sortie et dépendances

`Renderer(graph)` conserve le [`Graph`](../src/domain/graph.py) et fixe `padding = 2` cellules (l. 16–19). `render(size, frame=None, playback=None) -> list[str]` reçoit :

| Paramètre | Rôle |
| --- | --- |
| `size: ContentSize` | Largeur et hauteur en cellules du panneau à remplir. |
| `frame: AnimationFrame \| None` | Temps `elapsed` utilisé pour les couleurs arc-en-ciel et le clignotement ; son absence équivaut ici à `elapsed=0.0`. |
| `playback: PlaybackSnapshot \| None` | Positions visibles des drones et drone sélectionné. Sans instantané, seules les liaisons et zones sont dessinées. |

Le résultat est `Canvas.to_lines()` : une liste de chaînes, une par ligne de la grille. Les chaînes peuvent contenir des séquences ANSI produites par `tuiloom.style`. `Canvas` range une chaîne stylée dans une seule cellule logique et valide sa largeur terminal via `display_width`.

Les autres aides importées sont [`Projector`](../src/rendering/projection.py), qui ramène les coordonnées de la carte vers la taille du panneau, et [`get_line_points`](../src/rendering/line_drawing.py), qui donne les points entiers d'un segment, extrémités incluses. `rainbow_color` et `style` proviennent de Tuiloom.

## 2. Séquence de `render` (l. 21–42)

À chaque appel, `render` crée **un nouveau** `Canvas(size.width, size.height)` rempli d'espaces. Il calcule les minimums et maximums de `x` et `y` sur toutes les zones du graphe, puis construit `Projector` avec une zone utile de `size.width - 2 * padding` par `size.height - 2 * padding`. Le helper `_project` ajoutera ensuite le décalage de 2 cellules aux coordonnées obtenues.

L'ordre de dessin est important :

1. `_draw_connections` trace les liaisons en points `·`.
2. `_draw_zones` écrit `●` sur les cellules des zones, recouvrant les points de liaison aux extrémités.
3. `_draw_drones`, si un instantané existe, écrit les étiquettes des drones au-dessus des deux premières couches.

Quand plusieurs éléments occupent une même cellule, le dernier `canvas.set` l'emporte. Le renderer ne conserve pas d'image précédente : chaque appel repart d'une grille vide, ce qui évite les traces laissées par un drone en mouvement.

## 3. Projection des coordonnées (l. 28–35 et 154–164)

[`Projector.project`](../src/rendering/projection.py) applique une transformation linéaire, avec arrondi, depuis les bornes géographiques du graphe vers les indices de la zone utile. Pour un axe `x` non constant :

```text
screen_x = round((x - min_x) / (max_x - min_x) * (width_utile - 1))
```

Pour `y`, la fraction est inversée afin que les grandes coordonnées de la carte se trouvent plus haut à l'écran :

```text
screen_y = round((1 - (y - min_y) / (max_y - min_y)) * (height_utile - 1))
```

Si toutes les zones ont le même `x` ou le même `y`, `Projector` place cet axe au milieu de la zone utile. `_project` ajoute ensuite `(padding, padding)` aux coordonnées écran. Les mêmes règles sont utilisées pour les zones, les liaisons et les drones, ce qui garde leurs positions alignées lors d'un redimensionnement du panneau.

Les axes `x` et `y` sont ajustés indépendamment : les proportions géométriques de la carte peuvent changer selon la forme du panneau. Des zones distinctes peuvent aussi aboutir à la même cellule après arrondi.

## 4. Liaisons et zones

### `_draw_connections` (l. 44–56)

Pour chaque `Connection`, le renderer récupère les deux `Zone` par leur nom, projette leurs coordonnées et appelle `get_line_points(start, end)`. Cet auxiliaire implémente un tracé entier de type Bresenham et inclut les deux extrémités. Chaque point reçoit le caractère `·` en gras. Les liaisons n'utilisent pas ici leur capacité, leur type ni une couleur spécifique.

### `_draw_zones` et `_zone_color` (l. 58–78)

`_draw_zones` extrait `frame.elapsed` ou `0.0`, calcule une couleur `rainbow_color(elapsed)`, puis parcourt toutes les zones du graphe. Pour chacune, il projette `(zone.x, zone.y)` et dessine `●` en gras, avec la couleur déterminée par `_zone_color`.

`_zone_color(zone_name, animated_color)` lit `zone.metadata.color` :

| Métadonnée | Couleur effectivement utilisée |
| --- | --- |
| `"rainbow"` | La couleur animée calculée pour ce rendu. |
| Chaîne non nulle différente de `"rainbow"` | Cette chaîne est passée à Tuiloom comme couleur. |
| `None` | `"white"`. |

La couleur arc-en-ciel est recalculée à chaque image. Toutes les zones qui demandent `rainbow` reçoivent la même valeur pour une image donnée.

## 5. Positions visuelles des drones

### De `VisualDrone` à une cellule : `_visual_position` (l. 122–128)

Le renderer convertit `visual.start` et `visual.end` en coordonnées écran avec `_location_position`, génère **tous les points entiers** du segment entre les deux, puis prend l'élément d'index `round(progress * (len(points) - 1))`. Une progression de `0` choisit le départ, `1` l'arrivée ; les valeurs intermédiaires avancent par paliers de cellules. Les positions sont donc discrètes, même si `Playback.snapshot()` fournit une progression flottante continue.

### Zone ou milieu de liaison : `_location_position` (l. 130–144)

- Si `location.zone` est renseignée, la fonction projette directement la zone correspondante.
- Sinon, elle exige `location.source` **et** `location.target`, récupère les deux zones, calcule les points du segment projeté et choisit `points[(len(points) - 1) // 2]` : le point médian selon l'ordre du tracé, avec arrondi vers le premier côté en cas d'égalité.
- S'il manque une extrémité pour une position de liaison, elle lève `ValueError("Connection location needs both endpoint zones")`.

Ainsi, l'entrée dans une liaison restreinte se dessine du hub de départ vers le **milieu** de la liaison. Le mouvement d'arrivée du tour ultérieur part de ce milieu et se termine dans la zone cible. Le champ `location.connection` identifie logiquement la liaison, mais cette fonction utilise ses champs `source` et `target` pour calculer les coordonnées.

Exemple conceptuel :

```text
Zone A ●──────────────● Zone B
       └── mouvement 1 → milieu
                       └── mouvement 2 → B
```

## 6. Regroupement, libellé et couleur des drones (l. 80–120)

`_draw_drones` calcule d'abord la cellule de chaque drone de `playback.positions`. Le dictionnaire `groups` associe une coordonnée `(x, y)` à la liste des identifiants qui y aboutissent. Un autre dictionnaire `colors` associe une couleur à cette coordonnée.

Pour chaque `VisualDrone`, `_visible_zone` renvoie la zone de départ si `progress == 0`, celle d'arrivée si `progress == 1`, et `None` pendant l'interpolation (l. 146–152). Quand une zone est visible, sa couleur **remplace** la couleur enregistrée pour le groupe. Hors zone, une couleur est posée seulement si la cellule n'en a pas déjà : celle de `visual.start.source` pour un départ sur liaison, sinon de `visual.start.zone`, sinon du hub de départ. Si plusieurs drones se superposent, la couleur dépend donc de leur ordre de parcours et de la présence éventuelle d'une zone visible ; elle n'est pas calculée individuellement pour les caractères d'un groupe.

Une fois les groupes construits, chaque cellule occupée reçoit :

| Taille du groupe | Libellé |
| ---: | --- |
| 1 | `D<id>`, par exemple `D3` |
| 2 ou plus | `x<effectif>`, par exemple `x4` |

Le libellé est tronqué à `canvas.width`, puis centré autour de `x` autant que les bords le permettent : `left = max(0, min(x - len(label)//2, canvas.width - len(label)))`. Chaque caractère est écrit séparément, en gras et avec la couleur du groupe. Les étiquettes peuvent recouvrir les symboles des zones, les lignes ou une autre étiquette si leurs plages de caractères se chevauchent ; seul le regroupement des drones dont la **cellule d'ancrage est identique** est prévu.

## 7. Sélection et clignotement (l. 110–120)

Un groupe clignote si `playback.selected_drone_id` figure parmi ses drones, si un `frame` est fourni, et si `int(frame.elapsed * 2) % 2 == 0`. Pendant ces demi-secondes, `style(..., reverse=True)` inverse l'affichage de chaque caractère du libellé. Pendant les autres demi-secondes, le libellé revient à son style normal ; il n'est pas supprimé.

Cette règle fonctionne aussi quand le drone sélectionné partage une cellule avec d'autres : c'est le libellé collectif `xN` qui clignote. Sans `AnimationFrame`, il n'y a pas de clignotement, même si un drone est sélectionné. Le renderer lit uniquement l'identifiant dans l'instantané ; le choix du mouvement et du drone appartient à `Playback` et au panneau Simulation.

## 8. Flux complet depuis l'interface

```text
Simulator → Turn / Movement calculés
                    ↓
             Playback.advance(elapsed)
                    ↓
             Playback.snapshot()
                    ↓
             Renderer.render(size, frame, snapshot)
                    ↓
      Canvas : liaisons → zones → drones
                    ↓
             list[str] pour Tuiloom
```

Dans [`main_menu.py`](main_menu.md), le panneau Graphe utilise `ScreenContent.animated(..., fps=20)` et appelle `renderer.render(size, frame, playback.snapshot())` à chaque image. `Playback.snapshot()` fournit une vue cohérente pour ce rendu, tandis que le rappel périodique du menu fait avancer `Playback` avec `frame.elapsed`.

## 9. Préconditions et limites visibles

- Le graphe doit contenir au moins une zone : `min(...)` et `max(...)` sont appelés sans valeur par défaut.
- Le panneau doit fournir une taille suffisante pour la zone utile et pour les cellules écrites. Le panneau animé de `main_menu.py` demande 40 × 20 ; `Renderer.render` ne valide pas lui-même une taille arbitrairement petite.
- Les noms de zones et les extrémités des liaisons présents dans un instantané doivent exister dans le graphe ; les accès sont directs dans `graph.zones`.
- `VisualDrone.progress` provient normalement de `Playback.snapshot()` et reste dans `[0, 1]`. Le renderer ne borne pas cette valeur avant d'indexer les points du segment.
- Les métadonnées de zone déterminent ici la **couleur** seulement. Les règles de capacité, de restriction et de routage sont appliquées en amont par la simulation.
- La sortie est une vue en caractères : arrondis de projection, recouvrement et longueur des libellés peuvent réduire la lisibilité sur des graphes très denses.

## 10. Repères dans le code

| Lignes | Responsabilité |
| --- | --- |
| 16–42 | Initialisation et composition d'une image complète |
| 44–56 | Tracé des liaisons |
| 58–78 | Tracé et couleur des zones |
| 80–120 | Groupes, libellés, couleurs et clignotement des drones |
| 122–144 | Conversion des positions logiques en cellules |
| 146–152 | Détection d'une zone au départ ou à l'arrivée |
| 154–164 | Ajout de la marge à la projection |
