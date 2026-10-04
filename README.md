# VÉRTICE

Shooter táctico en primera persona hecho con Three.js, en un solo archivo (`index.html`).

Se publica con GitHub Pages en https://zenteyacompany.lat.

## Jugar en local
Abre `index.html` en Chrome o Edge. Three.js se carga desde jsDelivr, así que hace falta conexión a internet.

## Cuentas y guardado en la nube
Las cuentas usan Firebase (Google + Firestore, proyecto `vertice-7f000`). Las reglas de seguridad están en `firestore.rules`: pégalas en la consola de Firebase, en Firestore Database › Reglas, y publícalas. En Authentication › Configuración › Dominios autorizados deben estar `zenteyacompany.lat` y `www.zenteyacompany.lat`.

Sin sesión iniciada se juega como invitado y el progreso se guarda en el navegador.

## Amigos y grupo
Con la cuenta de Google cada jugador tiene un ID de jugador `Nombre#1234`. En el panel social del lobby se añaden amigos por su ID, se aceptan solicitudes y se invita al grupo (hasta 5 jugadores). El líder elige mapa y dificultad y pulsa INICIAR PARTIDA: la partida empieza a la vez para todo el grupo. De momento cada jugador juega su propia partida contra bots, porque todavía no hay servidor de juego en red.

Todo va por Firestore en tiempo real (`users`, `handles` y `parties`). Cada vez que cambie `firestore.rules`, hay que volver a publicarlas en la consola de Firebase.
