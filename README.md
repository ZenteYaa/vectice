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
