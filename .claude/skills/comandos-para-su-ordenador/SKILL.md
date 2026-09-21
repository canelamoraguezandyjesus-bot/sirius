---
name: comandos-para-su-ordenador
description: >-
  Cómo se le da un comando al propietario para que funcione a la primera en SU
  ordenador (Windows 11, PowerShell 5.1, escritorio y repositorio dentro de
  OneDrive, sin permisos de administrador a mano): el formato dónde / qué / qué
  sale, las trampas medidas de su máquina y lo que no se le pide nunca. Cárgala
  antes de escribirle cualquier comando, ruta o instalación, y cuando un comando
  suyo haya fallado con «no se encuentra la ruta», «acceso denegado» o «la
  ejecución de scripts está deshabilitada».
---

# Comandos para su ordenador

**Regla única: un comando que le falla es un fallo del comando, no suyo. Él no
programa, lo ha dicho, y pega lo que le das.**

## El formato, siempre el mismo

1. **Dónde se pega**: «PowerShell dentro de VS Code» o «PowerShell normal»; si
   hace falta abrirlo como administrador, se dice antes.
2. **Qué hace**, en una línea sin jerga.
3. **Qué va a salir** si va bien, con el texto esperado; y **qué hacer si sale
   otra cosa**: pegar la salida entera. El 09-08-2026 pegó diecinueve salidas
   en setenta minutos y el modo «un comando cada vez» funcionó; el 14-08 a las
   14:15, sin el dónde, se perdió: «no sé ni dónde ponerla».
4. **Un comando por mensaje.** Varios comandos son varias oportunidades de que
   uno falle sin que se sepa cuál.

## Las trampas de su máquina, medidas

- **Su escritorio está en OneDrive.** `C:\Users\ASUS\Desktop` no existe;
  `$HOME\Desktop` falla. Se escribe `[Environment]::GetFolderPath('Desktop')`.
  Tumbó `Sirius.lnk` el 14-08-2026 (15:18) y dos comandos seguidos el
  20-09-2026.
- **El repositorio está en `C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius`**,
  con un espacio en el nombre: la ruta va entre comillas. Él no la sabe de
  memoria («¿yo qué sé dónde está la carpeta?», 11-09-2026 21:17): va escrita.
- **OneDrive rompe enlaces duros y bloquea ficheros.** `uv` falló con el error
  396 y el `.venv` dio «acceso denegado» (08 y 09-08-2026). Con `uv`, añade
  `--link-mode=copy`; nunca borres un `.venv` suyo desde un comando. Él pidió
  sacar el repositorio de OneDrive el 09-08-2026 y sigue ahí: cuenta con ello.
- **PowerShell 5.1**, no 7. `$ErrorActionPreference = 'Stop'` junto con `2>&1`
  convierte cualquier aviso por stderr de un programa nativo en un error que
  mata el guion (20-09-2026: el guion murió en la primera sesión). Alrededor de
  una llamada nativa, `'Continue'`, y se mira `$LASTEXITCODE`.
- **La política de ejecución bloquea los `.ps1` de npm**: «la ejecución de
  scripts está deshabilitada» con `npx.ps1` (11-09-2026 21:54). Se usa
  `npx.cmd`, o `powershell -ExecutionPolicy Bypass -File …` para tus guiones.
- **`winget` pide administrador** y puede fallar con el código 1622 (11-09-2026
  21:51): dile que acepte el aviso de Windows, y que si el paquete ya estaba
  instalado el fallo no importa.
- **Una variable de entorno recién guardada no se ve en la misma consola**
  (11-09-2026 20:59: «me salió vacío»; 21:00: «ahora sí me la imprimió»). Que
  abra una consola nueva antes de comprobarla.
- **Descargas y ficheros de él**: la sesión en la nube no ve su disco. Si el
  comando necesita un fichero suyo, se le pide adjunto una vez, no se le manda
  a buscarlo (26-07-2026: «no vuelvas a buscarlos en el ordenador»).

## Qué NO hace esta skill

- **No ejecuta nada en su máquina**: solo escribe lo que él ejecuta. La
  validación manual en Windows real sigue siendo suya (ficha PROC-008 de la
  auditoría).
- **No cubre el laboratorio físico ni la cabeza robótica**, fuera de alcance
  desde el 19-09-2026.
- **No es una lista cerrada**: cada trampa nueva que tumbe un comando entra
  aquí con su fecha, y las que dejen de existir (si el repositorio sale de
  OneDrive) se quitan.
