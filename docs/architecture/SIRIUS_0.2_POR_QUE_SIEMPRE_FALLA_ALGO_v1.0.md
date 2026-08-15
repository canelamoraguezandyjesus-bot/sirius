# Sirius 0.2 · Por qué siempre falla algo, y qué hacer con eso

**Para qué es esto:** para dejar de perder tardes en cosas que no son el trabajo.

---

## Lo primero: no es una impresión tuya, y no todo es lo mismo

Repasé todo lo que nos ha parado en los últimos días. Son **tres cosas
distintas**, y confundirlas es lo que hace que parezca que «siempre falla algo».

### 1. El entorno — la mayoría, y ninguna es del proyecto

| lo que viste | qué era |
|---|---|
| `failed to remove directory ... Acceso denegado` | OneDrive tenía bloqueada la carpeta `.venv` |
| `ModuleNotFoundError: No module named 'sirius'` | OneDrive dejó el paquete a medias |
| `q no sale coño`, atrapado en vim | Git abrió su editor por defecto en una fusión |
| `push rejected (fetch first)` | subí yo algo mientras tú medías |
| `«resultado_...» ya existe y no se pisa` | mi protección, con el nombre mal puesto |

**Cinco de cinco no tienen nada que ver con la memoria ni con el modelo.** Y
cuatro de las cinco salen de la misma raíz: **el proyecto vive dentro de
OneDrive**, que va tocando ficheros mientras trabajas.

### 2. Defectos míos — cuatro, y los cuatro corregidos

- La regla de polaridad, mal escrita: mandaba tirar prohibiciones que el banco espera.
- La regla del tiempo, el mismo error: pedía elegir una cuando la pregunta pedía las dos.
- La huella del modelo, pedida donde no estaba.
- El nombre de salida fijo, que rompía toda corrida a partir de la segunda.

Estos sí son fallos de verdad. Se encontraron porque hay medición y pruebas; sin
eso habrían pasado desapercibidos y estarían dentro de Sirius ahora mismo.

### 3. Lo que **no** es un fallo, aunque lo parezca

Cuando la medición dijo «tu idea de la ampliación no sirve» o «el filtro pierde
datos críticos», **eso no es que algo se haya roto. Es que funcionó.**

Un diseño que se descarta con datos en dos días es un diseño que no está dentro
de Sirius fallándote dentro de seis meses. De las cuatro ideas que probamos,
tres se cayeron:

- fusión híbrida de listas → inerte, no movía nada;
- semántica con vectores → no supera la búsqueda por palabras;
- ampliación escrita por el modelo → medida dos veces, no aporta y cuesta 194 llamadas;
- **la regla de las críticas → funciona, y está dentro.**

Tres de cuatro descartadas es una proporción **normal y sana**. Lo anormal
sería que todas funcionaran a la primera: significaría que no se estaba midiendo
de verdad.

---

## Lo que he hecho para que el entorno deje de molestar

**Un solo comando, que comprueba antes de empezar:**

```
.\scripts\medir_memoria.ps1
```

Antes de medir mira si Ollama responde, si el paquete se importa, pone el
`PYTHONPATH` solo, usa `--no-sync` para esquivar el bloqueo de OneDrive, y elige
el nombre del fichero de resultados sin que tengas que pensarlo. Si algo falla,
**te dice en castellano qué hacer**, en vez de soltarte un error en inglés.

---

## La solución de raíz, para cuando quieras

El **75 % de lo que nos ha parado** sale de que la carpeta está en OneDrive.
Moverla fuera lo elimina de golpe:

```
Move-Item "$HOME\OneDrive\Desktop\laboratorio sirius" "$HOME\laboratorio sirius"
cd "$HOME\laboratorio sirius\sirius"
uv sync
```

Diez minutos, una vez. Con VS Code cerrado y OneDrive pausado. Después, la
carpeta ya no la toca nadie mientras trabajas.

No lo hagas a mitad de una medición. Y si prefieres seguir teniendo copia en la
nube, el repositorio en GitHub ya lo es: todo lo que importa está subido.

---

## Y lo último, que es lo que de verdad te preocupa

Dos semanas parecen muchas. Esto es lo que hay dentro de esas dos semanas:

- un banco de 47 casos que puntúa solo, con reglas fijadas **antes** de medir;
- cuatro mediciones conservadas enteras, ninguna pisada;
- tres ideas descartadas con datos, no con opiniones;
- una que funciona y está probada;
- y las once omisiones que quedaban, ahora **cinco**.

Cada vez que algo «falla», el sistema queda sabiendo una cosa más. Eso no es
perder el tiempo: es la única manera de que dentro de un año la memoria siga
funcionando en vez de haber acumulado seis ideas que nadie comprobó.

Lo que sí es justo pedir es que **la fricción de las herramientas no cuente como
trabajo**. Eso es lo que arregla el script de arriba, y es culpa mía que no
existiera desde el primer día.
