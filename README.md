# VÉRTICE

Shooter táctico en primera persona hecho con Three.js, en un solo archivo (`index.html`).

Se publica con GitHub Pages en https://zenteyacompany.lat.

## Jugar en local
Abre `index.html` en Chrome o Edge. Three.js se carga desde jsDelivr, así que hace falta conexión a internet.

## Cuentas y guardado en la nube
Las cuentas usan Firebase (Google + Firestore, proyecto `vertice-7f000`). Las reglas de seguridad están en `firestore.rules`: pégalas en la consola de Firebase, en Firestore Database › Reglas, y publícalas. En Authentication › Configuración › Dominios autorizados deben estar `zenteyacompany.lat` y `www.zenteyacompany.lat`.

Sin sesión iniciada se juega como invitado y el progreso se guarda en el navegador.

## Amigos y grupo
Con la cuenta de Google cada jugador tiene un ID de jugador `Nombre#1234`. En el panel social del lobby se añaden amigos por su ID, se aceptan solicitudes y se invita al grupo (hasta 5 jugadores). El líder elige mapa y dificultad y pulsa INICIAR PARTIDA: la partida empieza a la vez para todo el grupo. Todo el grupo juega la misma partida en el mismo mapa.

Todo va por Firestore en tiempo real (`users`, `handles` y `parties`). Cada vez que cambie `firestore.rules`, hay que volver a publicarlas en la consola de Firebase.

## Partida en grupo (WebRTC P2P)
Al iniciar la partida, los navegadores del grupo se conectan entre sí con WebRTC, sin servidor de juego. El líder hace de anfitrión: mueve a los bots y reenvía a cada miembro lo que hacen los demás. La conexión se negocia una vez por Firestore (`parties/{grupo}/rtc/{miembro}`), así que las reglas de `firestore.rules` deben estar publicadas.

Cada jugador mueve a su personaje en su propio navegador y ve a sus compañeros en turquesa, con su ID encima. Los impactos a los bots se calculan sobre lo que ve quien dispara y los confirma el anfitrión, que avisa de cada baja a quien la hizo. Si el anfitrión sale, los demás siguen jugando solos contra los bots.

Solo se usan servidores STUN públicos, sin TURN: si dos redes no permiten la conexión directa (algunas redes de empresa o de datos móviles), ese jugador juega por su cuenta.

## Partida no clasificatoria (por rondas)
Modo por defecto del lobby. Tú y 4 aliados bot contra 5 bots, con las reglas de rondas de un shooter táctico:

- Gana quien llegue antes a 13 rondas (como mucho 25). Cambio de bando al acabar la ronda 12.
- Rondas de pistola en la 1 y en la 13: todos vuelven a ¤ 800 y a la pistola de serie. A 12-12, la ronda 25 decide con ¤ 5000 para todos.
- Fases: compra 30 s (barreras en las bases y tienda abierta), ronda 100 s, Spike plantada 45 s (pitido cada vez más rápido) y 7 s de fin de ronda.
- Spike: mantén **4** dentro de un site 4 s para plantar y 7 s junto a ella para desactivar. Pasados 3,5 s, la mitad del progreso queda guardada. **G** la suelta.
- Economía: victoria +3000, derrota 1900 / 2400 / 2900 según la racha, baja +200, plantar +300 a cada atacante, tope ¤ 9000.

Se juega en Santuario, Acrópolis y Códice (cada mapa se dibuja en 3 draw calls). Por ahora es individual; Acrópolis y Códice se pueden usar en grupo en los otros modos cuando estén publicadas las reglas `match-1`.

Códice sigue el mapa táctico de referencia: Inicio Defensor al norte, Inicio Atacante al sur, Sitio B al oeste (Arco B, Torre B, Esquina B, Enlace B, Principal B, Vestíbulo B) y Sitio A al este (Grúa A, Esquina A, Rincón A, Patio A, Principal A, Vestíbulo A), con un Mid en dos alturas (Ventana, Superior, Escaleras e Inferior Mid). El plano está en `MAPS.codice.plan` como rectángulos de suelo en píxeles de la imagen (1 px = 9 cm), y `floorplanWalls` levanta los muros a su alrededor.

### Minimapa
Arriba a la izquierda, en todos los mapas. Muestra el plano del mapa con los sites, tu posición y hacia dónde miras, tus aliados y la Spike (en el suelo si atacas, o plantada). Los enemigos solo aparecen cuando tú o un aliado los tenéis a la vista, y se desvanecen 1,5 s después de perderlos.

## Modelos 3D (Blender)
Los modelos de arma con versión de Blender se generan por script. `blender/titan.py` construye el Titán en sus dos versiones y las exporta a `assets/weapons/`. Cada una lleva un solo material PBR con paleta y un `Muzzle_Point`:
- Estándar: `titan_default.glb`, 1.400 triángulos.
- Dragón: `titan_dragon.glb`, 1.976 triángulos, con cabeza de dragón en la boca, cresta dorada y respiraderos de brasa.

    blender --background --python blender/titan.py -- default
    blender --background --python blender/titan.py -- dragon

(o `pip install bpy` y `python blender/titan.py dragon`). El juego carga los .glb al arrancar. La skin base se usa sin skin comprada, y una skin de la tienda con `modelPath` usa el suyo. Si un .glb no carga (por ejemplo, abriendo `index.html` como archivo local), se usa el modelo procedural. Las poses de cadera y ADS, el retroceso y la ficha del arma están en `BASE_SKINS` de `index.html`.

### Agentes
`blender/generate_agents.py` construye los 5 agentes y los exporta a `assets/characters/<id>.glb`:

| Agente | Rol | Acento | Silueta | Triángulos |
|---|---|---|---|---|
| Valquiria (mujer) | Duelista | `#ff4655` | atlética, pelo corto, hombrera derecha, rodilleras | 4.952 |
| Kage (mujer) | Vanguardia | `#00f3ff` | ligera, traje ceñido, arnés cruzado, coleta alta, visor monofocal | 4.818 |
| Nyx (mujer) | Iniciadora | `#2ec4b6` | capucha, traje técnico, brazo izquierdo cibernético | 5.424 |
| Aegis (hombre) | Centinela | `#ffb703` | hombros anchos, placas balísticas, casco angular cerrado | 5.040 |
| Vortex (hombre) | Controlador | `#7b2cbf` | gabardina hasta los muslos, máscara antigás de doble filtro | 5.326 |

    blender --background --python blender/generate_agents.py -- todos
    python blender/generate_agents.py kage          # con pip install bpy, uno solo

Todos miden 1,80 m con el pivote en los pies, llevan una sola malla con un solo material (1 draw call) y las mismas hitboxes invisibles: `HITBOX_HEAD` (esfera de 0,12 m a 1,65 m), `HITBOX_BODY` (0,38 × 0,65 m a 1,15 m) y `HITBOX_LEGS` (0,30 × 0,75 m a 0,45 m). El juego usa esas medidas (`AGENT_HITBOX`) para los bots, tu jugador y tus compañeros, y avisa en consola si un .glb no las cumple. Tu agente se elige con ‹ › en tu ranura del escuadrón y se guarda con tus ajustes. Los miembros del grupo lo ven cuando están publicadas las reglas `agents-1`.
