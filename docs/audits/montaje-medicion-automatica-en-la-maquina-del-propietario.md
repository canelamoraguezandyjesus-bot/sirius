# Medir sin nadie delante: por qué NO un runner auto-alojado, y qué hacer en su lugar

20-09-2026. Escrito a petición del propietario, que pidió dejar montada la
medición automática para solo tener que probarla después.

## El cuello de botella que esto ataca

Tres cosas están bloqueadas por la misma causa, y lleva así desde agosto:

- **D7 punto 6** no pudo registrar su umbral porque «la cifra real de
  coincidencia del etiquetado sigue sin producirse» (ADR-117): CI no tiene
  Ollama.
- **La palanca 1** (ADR-164) no se da por cerrada hasta que el propietario la
  corra a mano. Se corrió por primera vez el 20-09, once días después.
- **Los 218 elementos de más** del banco completo solo se pueden descomponer
  con el filtro real, o sea con Ollama.

Todo lo que necesita modelo necesita a una persona delante. Ése es el cuello.

## Por qué NO un runner auto-alojado

**El repositorio es público** (`visibility: public`, `allow_forking: true`,
comprobado por API el 20-09-2026).

GitHub desaconseja expresamente los runners auto-alojados en repositorios
públicos, y la razón es concreta: cualquiera puede hacer un fork y abrir una
pull request cuyo workflow **ejecute código arbitrario en la máquina del
runner**. Esa máquina sería el PC personal del propietario, con sus ficheros,
sus credenciales y su red local.

Se puede acotar —limitar los disparadores a `workflow_dispatch` y `push`, nunca
`pull_request` ni `pull_request_target`—, pero esa protección depende de que
**ningún** workflow presente ni futuro se equivoque una sola vez. Es una
salvaguarda que hay que acertar siempre, y basta fallarla una vez.

**Recomendación: no se monta.** Si algún día el repositorio pasara a privado,
la conversación cambia.

## Lo que sí se monta, y da casi lo mismo

Una **tarea programada local** que corre las mediciones y **empuja los
resultados a una rama**. No hay nada entrante: ningún código ajeno se ejecuta
en el PC. Solo sale texto.

Con eso, el propietario deja el ordenador encendido y por la mañana las
mediciones están en el repositorio, visibles para cualquier sesión que las
lea — incluida la mía, que sin esto no puede medir nada con modelo (los sitios
que sirven pesos están bloqueados por la política de red del entorno:
`ollama.com`, `registry.ollama.ai` y `huggingface.co` devuelven 403).

### Qué mide cada noche

1. `scripts/medir_banco_con_ollama_real.py --diagnostico` — el banco entero con
   el filtro real. Es la que da los tres suelos de D1.
2. `scripts/medir_interprete_de_peticion.py` — la palanca 1.
3. `tests/acceptance/test_d7_punto_6_coincidencia_etiquetado.py -q -s` — la
   coincidencia del etiquetado.

Las tres con el modelo **precalentado con los mismos parámetros que usa el
adaptador** (`num_ctx=8192`), sin lo cual Ollama recarga el modelo en la
primera llamada real y contamina la medición — el fallo que se aprendió el
20-09.

### La regla dura que el guion aplica solo

Si el contador de **rendiciones no es cero**, el fichero de resultados se marca
`CONTAMINADA` en su primera línea. Una medición contaminada que se guarda sin
marcar es peor que no medir.

### El guion

Se guarda como `medir_de_noche.ps1` en la raíz del repositorio. **No se
commitea a `main`**: vive en la rama de mediciones o fuera del control de
versiones, a elección del propietario.

Se entrega como fichero: **`medir_de_noche.ps1`**, en la raíz de esta rama
de auditoría. Es seguro por construcción:

- **se aborta si el árbol de trabajo tiene cambios sin guardar**, en vez de
  destruirlos (la primera versión de este documento hacía `checkout -B` y
  `--force-with-lease`, que habría borrado el histórico de mediciones cada
  noche y podía pisar trabajo local; corregido);
- **nunca hace force-push** y nunca toca `main` más allá de un fast-forward;
- escribe los resultados **fuera del repositorio** y solo los copia al final;
- **devuelve el clon a la rama en la que estaba**, pase lo que pase;
- marca `CONTAMINADA` en la primera línea cualquier medición con rendiciones
  distintas de cero o con un fallo abierto del adaptador.

### Programarlo

En PowerShell **como administrador**, una vez:

```powershell
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius\medir_de_noche.ps1"'
$cuando = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "Sirius - mediciones nocturnas" `
  -Action $accion -Trigger $cuando -RunLevel Highest -Description `
  "Mide el banco con Ollama real y empuja los resultados a la rama de mediciones."
```

Requisitos: el ordenador encendido y sin suspender a las 3:00, Ollama
arrancado como servicio, y `git` con credenciales ya guardadas.

## Lo que esto da, y lo que no

**Da**: mediciones reales cada noche, sobre el `main` del día, con el arbol
anotado en el nombre del fichero, contaminaciones marcadas solas, y visibles en
el repositorio para cualquiera que las lea.

**No da**: que el ciclo del motor pueda *juzgar* un cambio con modelo. Para eso
haría falta el runner, y el runner no se monta en un repositorio público. Los
encargos que toquen el intérprete o el filtro seguirán entregándose con su
medición pendiente, y esta tarea la producirá a la noche siguiente en vez de
esperar a que alguien se siente.

**Riesgo conocido, ya visto dos veces**: el `.venv` vive dentro de una carpeta
sincronizada por OneDrive, y `uv sync` falla con «Acceso denegado» al borrar el
`dist-info`. Pasó el 05-09 y el 20-09. Las dos veces se recuperó, pero una tarea
desatendida que falle ahí no medirá nada esa noche. Sacar el repositorio de
OneDrive lo resolvería de raíz.
