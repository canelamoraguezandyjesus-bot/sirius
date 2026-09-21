---
name: validacion-manual-en-windows
description: >-
  Cómo se prepara, se guía y se registra la validación manual de Sirius en el
  Windows real del propietario, el único proceso físico de esta casa: qué se le
  manda ejecutar (construir el paquete, verificarlo, comprobar que no habla con
  nadie, las pruebas de aceptación que exigen «windows-real» o «evaluación
  humana»), en qué orden, qué devuelve él y cómo se anota lo demostrado y lo no
  demostrado. Cárgala cuando un cambio toque la interfaz, el empaquetado, el
  arranque o las credenciales de Sirius, cuando una prueba de la trazabilidad
  tenga motivo «windows-real», y antes de declarar superada cualquier prueba
  que ninguna suite pueda dar.
---

# La validación manual en Windows real

**Regla única: lo que solo Windows real puede demostrar no lo demuestra ninguna
suite. Se le pide a él una vez, con el comando exacto, y se anota como suyo,
con fecha, artefacto y sha.**

## Por qué existe, con fechas

- Sirius 0.1 se aceptó el **17-08-2026** con B13 y B14 ejecutados en Windows
  real por el propietario (PR #122). Esa PR llevaba **más de nueve días**
  esperando una ejecución correcta: la validación física era el bloqueo
  material de V8 (ficha PROC-008 de
  `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`).
- `.github/workflows/quality-windows.yml` tiene **cero ejecuciones** en toda su
  historia; los pendientes físicos de agosto (#127, #134) siguen intactos. Hoy
  no bloquea porque 0.1 está aceptado; volverá a bloquear cuando 0.2 toque la
  interfaz.
- El informe que sí funcionó: el **10-08-2026 a las 14:49**, «77
  comprobaciones, 0 fallos, 3 omitidas», y aparte, con esas palabras, «NO se ha
  demostrado: …». Es el molde.

## Los pasos

1. **Decide qué necesita Windows real, y solo eso.**
   `docs/implementation/TRAZABILIDAD_PA_SP.md` dice, prueba por prueba, si la
   cobertura es `automática`, `parcial` o `manual`, y con qué motivo
   (`proveedor-real`, `windows-real`, `evaluación-humana`). Lo `automática` no
   se le pide nunca; lo `parcial` se le pide solo en la parte que su motivo
   nombra.
2. **Prepara los comandos con la skill `comandos-para-su-ordenador`**: dónde se
   pega, qué hace, qué va a salir; la ruta del repositorio entre comillas;
   PowerShell 5.1; un comando por mensaje. Los tres guiones de esta casa:
   - `scripts/build_windows.ps1`: empaqueta desde un checkout limpio, en un
     árbol de trabajo temporal (B13).
   - `scripts/verify_windows_package.ps1 -ArtifactPath <zip>`: verifica el
     paquete en seis fases —localizar y extraer, comprobaciones estáticas,
     precondiciones, puerta de credenciales, utilidades de ejecución y
     evidencia de arranque— (B13).
   - `scripts/verify_windows_no_network.ps1`: el paquete no habla con nadie sin
     proveedor real; sin elevar, en entorno desechable (B14).
   Lo que necesite administrador se dice antes de que lo pegue.
3. **Lo que él devuelve**: la salida entera pegada, nunca un «ok». Para las
   pruebas de evaluación humana, una pregunta cerrada por prueba («PA-…: ¿se
   vio X? sí o no»): él contesta sí, no o un dato (`hablar-con-el-propietario`).
4. **Cómo se registra**, el mismo día: en la tabla de ejecuciones vigente (para
   0.1 fue la de `docs/implementation/V8_EXECUTION.md`: fecha, bloque,
   commit o artefacto, tipo `manual-Windows`, `proveedor-real` o
   `evaluación-humana`, evidencia) y en el ADR del cambio, como «ejecutada y
   reportada por el propietario, fecha, artefacto, sha». Lo no demostrado va
   aparte y con esas palabras, como el 10-08.
5. **Cuándo se le pide**: en lote, cuando esté delante del ordenador
   (`AGENTS.md`, regla 13), y una sola vez: si dice que ya lo probó, está
   probado y se anota así (`verificar-el-estado-real`, paso 3).

## Qué NO hace esta skill

- **No ejecuta nada en su máquina**: la sesión escribe, él ejecuta.
- **No convierte una prueba manual en automática**: la cobertura de la
  trazabilidad sigue diciendo `manual` o `parcial` con su motivo.
- **No sustituye a `quality-windows.yml`** el día que alguien lo haga correr.
- **No cubre el laboratorio físico ni la cabeza robótica**, fuera de alcance
  desde el 19-09-2026.
