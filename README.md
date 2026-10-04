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

## Modelos 3D (Blender)
Las skins base con modelo propio se generan con Blender por script. `blender/titan_default.py` construye el Titán (skin Estándar), con 1.400 triángulos, un solo material PBR y el `Muzzle_Point`, y lo exporta a `assets/weapons/titan_default.glb`:

    blender --background --python blender/titan_default.py

(o `pip install bpy` y `python blender/titan_default.py`). El juego carga el .glb al arrancar; si no puede (por ejemplo, abriendo `index.html` como archivo local), usa el modelo procedural. Las poses de cadera y ADS, el retroceso y la ficha del arma están en `BASE_SKINS` de `index.html`.
