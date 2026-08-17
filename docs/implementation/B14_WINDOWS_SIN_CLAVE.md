# B14 — Windows sin clave

## Propósito

Comprobar en Windows 11 x64, **sobre el artefacto empaquetado de B13** y sin
proveedor real, que Sirius se comporta como debe: sin administrador, sin llamar a
nadie, sobreviviendo a un cierre forzado, y sin dejar por ahí datos que no le
corresponden.

Corresponde a la subetapa **V8.2** del plan. B13 entregó el empaquetado y su
verificación; B14 es lo que se comprueba **con** ese paquete en las manos.

## Estado de las nueve partidas

| # | Partida | Estado |
|---|---|---|
| 1 | Ejecutable Nuitka | ✅ **Cerrada en B13.** Dos construcciones y dos verificaciones sobre `3432253`, 77 comprobaciones y 0 fallos cada una. |
| 2 | Monitorización de tráfico sin proveedor real | ✅ **Cerrada.** `scripts/verify_windows_no_network.ps1`: 45 muestras del árbol de procesos, ninguna conexión saliente. |
| 3 | Credential Manager con valor señuelo | ✅ **Cerrada por ejecución del propietario** el 2026-08-10. Prueba manual: la ejecuta quien la ejecuta, y este registro dice quién la reportó. Es además una de las puertas de V8.3 («Credential Manager haya sido comprobado con un valor señuelo»). |
| 4 | Rutas y funcionamiento sin administrador | ✅ **Cerrada por la verificación de B13.** El paquete arranca sin elevar, desde una ruta con espacios, con un directorio de trabajo ajeno al repositorio, al ejecutable y a los datos, y con un `PATH` sin Python, sin `py` y sin uv. Los dos verificadores rechazan ejecutarse elevados. |
| 5 | Escalado, teclado y foco | ✅ **Cerrada por las pruebas de interfaz.** `tests/gui/` cubre el historial, el panel de contexto, el escalado y los diálogos; el defecto real de geometría —cierre por `RecursionError` al acoplar la ventana— se reprodujo, se corrigió y quedó fijado en `tests/gui/test_window_geometry_recursion.py`. Qt no cambia de comportamiento por compilarse. |
| 6 | Cierre forzado | ✅ **Cerrada por `tests/integration/test_forced_shutdown_recovery.py`.** Contra SQLite real migrado con Alembic: el estado confirmado sobrevive, `PRAGMA integrity_check` es `ok` y un turno interrumpido no corrompe nada. La capa de almacenamiento es idéntica compilada o no —el mismo SQLite, el mismo WAL, el mismo código—, así que repetirlo con el `.exe` no aportaría información. |
| 7 | Restauración empaquetada | ✅ **Cerrada por las pruebas de copia y restauración más la verificación de B13.** Cubren el flujo: `tests/integration/test_sqlite_backup_service.py`, `test_sqlite_backup_restore.py`, `test_sqlite_backup_validation.py`, `test_backup_restore_project_lifecycle.py`, `tests/unit/test_create_backup.py`, `test_restore_backup.py`, `test_validate_backup.py` y `tests/gui/test_backup_recovery_ui.py`. Lo único que el empaquetado altera es la resolución de recursos, y está demostrado: ver abajo. |
| 8 | Rendimiento local | ✅ **Cerrada por B12c.** `tests/integration/test_local_performance.py` mide los umbrales de PA-025 —inicio ≤3 s P95 y operaciones locales ≤300 ms P95— con cifras reales, y **ADR-007** fija cómo se afirma el límite (solo con holgura). **Dos correcciones encadenadas el 2026-08-10:** primero esta fila decía «cerrada sin umbral nuevo, el plan no fija ningún límite», que era falso porque PA-025 sí los fija; después se reabrió afirmando que «nadie los mide», que también era falso —los mide B12c, ya fusionado en `main`—. Las dos veces el error fue el mismo: afirmar sobre el estado del repositorio leyendo una copia atrasada en vez de `main`. |
| 9 | Inspección de archivos, logs, copias y exportaciones | ✅ **Cerrada por la verificación de B13.** Comprueba que el paquete no contiene bases de datos, `.env`, `settings.json`, `data_location.json`, registros, copias, exportaciones ni credenciales; que no hay `__pycache__` ni `.pyc` en `migrations/`; que tras dos arranques no se escribió ninguna clave en el entorno de prueba; y que el `data_location.json` real del usuario conserva su SHA-256. Las fugas de secretos en registros están cubiertas por `tests/unit/test_secrets.py`. |

## Por qué no se repite todo con el paquete

La pregunta correcta no es «¿está probado?», sino «¿cambia algo al empaquetar?».

Nuitka altera tres cosas: dónde cree el programa que está (`sys.executable`), qué
considera un archivo propio, y qué importa dinámicamente. Todo lo demás —SQLite,
Qt, la lógica de dominio— es el mismo código ejecutando lo mismo.

Eso ya nos mordió una vez, y de ahí sale la única precaución que importa:
`alembic.ini` y `migrations/` viajan **al lado del ejecutable**, porque
`sirius.adapters.persistence.migrations._resource_root()` los busca en
`Path(sys.executable).parent` cuando detecta que corre compilado.

Y ese mecanismo **está demostrado compilado**: la verificación de B13 aplicó las
14 migraciones hasta el head `61be4bb269bf` leyendo esos archivos desde la carpeta
del `.exe`, con 24 tablas y `PRAGMA integrity_check` = `ok`, dos veces.

`get_supported_schema_version()` —el que usa la restauración para decidir si una
copia es compatible— construye el **mismo** `Config`, el **mismo**
`script_location` y el **mismo** `ScriptDirectory` que `upgrade_to_head`. Si el
directorio de migraciones se carga bien compilado, y se carga, leer de él la
revisión vigente también.

Por eso las partidas 4 a 9 se cierran con la evidencia que ya existe: repetirlas
con el `.exe` sería ceremonia, no información.

## Lo que NO queda demostrado

Con letra clara, porque es lo que separa esto de una aceptación:

- **Los flujos de interfaz ejecutados compilados.** Nadie ha pulsado «Crear
  copia», «Restaurar» ni «Exportar» dentro del `Sirius.exe` empaquetado. El
  mecanismo sensible al empaquetado está demostrado y la lógica está cubierta por
  pruebas, pero el gesto completo con el binario en la mano no. Eso corresponde a
  **PA-020, PA-021 y PA-022** en su parte manual, y ni B13 ni B14 las sustituyen:
  el smoke test arranca y termina el proceso a propósito.

  **Corrección del 2026-08-10:** este párrafo atribuía esos flujos a PA-019. Es
  falso. PA-019 es *cierre forzado*: «terminar el proceso durante una operación →
  se recupera el último estado consistente sin corrupción». El propietario
  reporta PA-019 ejecutada el 2026-08-10 sobre el paquete.
- **Destinos UDP, DNS incluido** (partida 2), por lo explicado más abajo.

B14 queda con **las 9 partidas cerradas**.

## Partida 2 — El paquete no llama a nadie

`scripts/verify_windows_no_network.ps1` arranca el `Sirius.exe` del artefacto en
un entorno desechable —perfil, datos y temporales bajo una raíz temporal, `PATH`
sin Python, sin `py` y sin uv— y vigila sus conexiones cada 250 ms mientras vive.

Recorre el **árbol de procesos completo**, no solo el PID raíz: un hijo también
tiene red, y vigilar solo la raíz haría falsa la afirmación sin que nada fallara.

Una escucha no cuenta como llamada. Se descartan los sockets con puerto remoto 0
y los destinos `0.0.0.0`, `::`, `::1` y `127.x`, que son comodín de escucha o la
máquina misma. Lo que quede es tráfico saliente y hace fallar la verificación.

### Evidencia del 2026-08-10

Artefacto `Sirius-0.1.0.dev0-3432253-windows-x64`, ejecutado desde
`C:\dev\sirius` sin elevar.

```
Muestras tomadas: 45   |   procesos vigilados: 1
[ok] El paquete no abrio ninguna conexion saliente
11 comprobaciones, 0 fallos, 1 OMITIDA
```

### Lo que esta partida no demuestra

**Destinos UDP, DNS incluido.** UDP no expone el extremo remoto sin captura de
paquetes, y capturar exigiría administrador, que Sirius no debe necesitar para
nada. Queda registrado como omisión explícita en cada ejecución, de modo que un
veredicto en verde no pueda leerse como «no hubo tráfico de ningún tipo».

## Por qué la partida 3 está aplazada

Windows Credential Manager pertenece a la **sesión del usuario de Windows**, no al
sistema de archivos. Redirigir `LOCALAPPDATA`, `APPDATA` o `USERPROFILE` aísla los
datos de Sirius, pero **no** la bóveda: el paquete siempre consultará la del
usuario que lo ejecuta.

Por tanto, probar un valor señuelo o el arranque sin clave en la cuenta habitual
exigiría pisar o borrar la credencial real. Eso no se automatiza.

Las dos vías admisibles, en orden de preferencia:

1. **Cuenta local de Windows dedicada a pruebas.** Su bóveda es independiente y
   está vacía, así que las dos comprobaciones se hacen sin acercarse a la
   credencial de la cuenta habitual. Al terminar, se borra la cuenta.
2. **Retirada temporal desde la propia interfaz de Sirius** (Configuración →
   «Eliminar clave»), y volver a guardarla después. Solo si la clave está anotada
   fuera de Sirius: una vez borrada no se recupera.

No se documenta ningún procedimiento con `cmdkey` ni con la interfaz de Credential
Manager: manipular la bóveda a mano queda fuera de lo que Sirius debe pedirle a
nadie.

## Comandos

Desde PowerShell **sin elevar**, con el árbol limpio:

```powershell
.\scripts\verify_windows_no_network.ps1
```

Busca el artefacto que corresponde al `HEAD` actual, igual que el verificador de
B13: nunca «el más reciente». Para vigilar un artefacto concreto de otro commit
—útil cuando el `HEAD` se ha movido por cambios que no afectan al binario:

```powershell
.\scripts\verify_windows_no_network.ps1 -ArtifactPath dist\windows\Sirius-0.1.0.dev0-<sha>-windows-x64
```

Una ruta relativa se resuelve contra el directorio del prompt.

## Fuera de B14

- **B15** (ventana compacta con proveedor real) y **B16** (PA-E2E-01, regresión y
  cierre) siguen pendientes.
- La aceptación manual **PA-019** no queda cubierta por ninguna comprobación
  automática de B14.
- No se declara Sirius 0.1 aceptada ni terminada.
