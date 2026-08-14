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
| 1 | Ejecutable Nuitka | ✅ **Cerrada en B13.** Dos construcciones y dos verificaciones sobre `3432253`, 77 comprobaciones y 0 fallos cada una. Ver `B13_PACKAGING.md`. |
| 2 | Monitorización de tráfico sin proveedor real | ✅ **Cerrada.** `scripts/verify_windows_no_network.ps1`. Evidencia abajo. |
| 3 | Credential Manager con valor señuelo | ⏸ **Aplazada por decisión del usuario.** Requiere una sesión de Windows sin la credencial real; ver «Por qué está aplazada». |
| 4 | Rutas y funcionamiento sin administrador | ◻ Pendiente. Parcialmente cubierta: los dos verificadores rechazan ejecutarse elevados y el paquete arranca sin administrador desde rutas con espacios. |
| 5 | Escalado, teclado y foco | ◻ Pendiente. |
| 6 | Cierre forzado | ◻ Pendiente sobre el paquete. Cubierto **fuera** del paquete por `tests/integration/test_forced_shutdown_recovery.py` (B11). |
| 7 | Restauración empaquetada | ◻ Pendiente. |
| 8 | Rendimiento local | ◻ Pendiente. |
| 9 | Inspección de archivos, logs, copias y exportaciones | ◻ Pendiente. |

B14 **no** se declara cumplido mientras quede una partida abierta.

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
