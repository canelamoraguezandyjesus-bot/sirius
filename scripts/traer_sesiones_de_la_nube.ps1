<#
.SYNOPSIS
  Trae a este ordenador las sesiones de Claude Code que viven en la nube, una a
  una y sin perder lo ya traido (auditoria de la forma de trabajar, paso 4).

.DESCRIPTION
  DONDE SE PEGA: en PowerShell, en cualquier carpeta. El guion crea el suyo.

  QUE HACE: por cada sesion de la nube del indice del 19-09-2026, ejecuta
  `claude --teleport <id>` en un clon aparte del repositorio. Va una a una,
  apunta en un fichero cual salio bien y cual no, y **se salta las que ya
  estan apuntadas como hechas**: si se corta a mitad, se vuelve a lanzar y
  sigue donde iba.

  QUE VA A SALIR: una linea por sesion -OK o FALLO- y, al final, un recuento
  y la ruta del zip con todo lo traido.

  POR QUE EXISTE: el 20-09-2026 se intentaron traer las 34 sesiones de la nube
  y solo bajaron 6. No se supo por que: el intento fue un bucle sin registro,
  asi que no quedo rastro de cual fallo ni con que error. Este guion apunta.

.NOTES
  No borra nada. No toca el repositorio de trabajo: clona en una carpeta
  temporal propia. Si `claude` no esta en el PATH, se detiene y lo dice.
#>

[CmdletBinding()]
param(
  # Donde clonar y donde dejar el resultado. Por omision, una carpeta nueva
  # en el escritorio, para que sea facil de encontrar y de borrar despues.
  [string]$Carpeta = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'sesiones-nube-sirius'),

  # Segundos de espera entre una sesion y la siguiente. No es cosmetico: el
  # intento del 20-09 pudo morir por ritmo, y no hay forma de saberlo sin
  # probar despacio una vez.
  [int]$EsperaSegundos = 5,

  # Solo enseña que haria, sin traer nada.
  [switch]$SoloEnsenar
)

$ErrorActionPreference = 'Stop'

$SESIONES = @(
  "session_01SpPVZoAxkcD4rg5BNLmp2F"
  "session_012hjxAp3YxHCejwc7G6EKAw"
  "session_011LQB5EL2jbzzLqKEDJ2J7k"
  "session_01KXD1jUyRkjhiKnU3RD9kCA"
  "session_01WdYnLcd8UzwSUVmfuzYzFe"
  "session_0119GCzLHFEoxrwaMg8pNkuQ"
  "session_012L2NZQbWeYNk3L3QfNckfU"
  "session_01LcNbArZ7UZucF5dPjqeMdZ"
  "session_01FT8rDQVx9BxyFUg5ed91UA"
  "session_01BNoR7XiHv37jMkg14NSVxw"
  "session_015ua7Cu6GLNWSDC9CWhXWHm"
  "session_0171zgh9SD2e4aY4vdQv8hQt"
  "session_01CrVrdnitZYuQLynri3Ej3h"
  "session_01E7mRnWYLYgRq1ECsg9Vw5o"
  "session_015mUbXegRNRepDe9REyQ88D"
  "session_017XMvaBMb1xKzuePDJZKGvT"
  "session_01Fa64jbAhXya7TTNqZAwHmV"
  "session_014xzXWCZRonUVNsxJ57irQr"
  "session_017TB4heE4CyGV93JRSCL5fw"
  "session_01Qd5MX1d2iMNoXctMcGxEtX"
  "session_01YbSAUvZfrLj5Ji8rzTEGMq"
  "session_01DvtMap2xCbSFLgWPXSuzHT"
  "session_01WrMPq3coGPDWN9pXaF4Mjf"
  "session_01Qdz71bAnxaZkU2pHXz8NJH"
  "session_01QrGat4SWdF9Fztx4ERn3ty"
  "session_01D6LCDKRxbHwYuuXtntJhEB"
  "session_01AsY18X5QyPtbiJBgFPUovR"
  "session_01MHYCR9xYNAFo5Edq6tU3C2"
  "session_01KPduztBLsFKXkiQaJgwRh4"
  "session_01AsUxZLoJK537giDW6KmSGN"
  "session_01B99qjrdDqpqLKW5JANTL1F"
  "session_013MjEyExVzaAsbGf8CSGjwF"
  "session_01RZBq9rCYG9MuJshovSFhNq"
  "session_01J2Hucr7VPpYwZdNN9AdhBx"
  "session_01T66fRQQnP8ziG1XyQtVba6"
)

function Escribir($texto, $color = 'Gray') {
  Write-Host $texto -ForegroundColor $color
}

# --- 1. Comprobaciones previas, antes de tocar nada --------------------------

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Escribir 'No encuentro el comando `claude` en el PATH. Abre la consola donde sueles usar Claude Code y vuelve a lanzarlo.' 'Red'
  exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Escribir 'No encuentro `git` en el PATH.' 'Red'
  exit 1
}

New-Item -ItemType Directory -Force -Path $Carpeta | Out-Null
$Registro = Join-Path $Carpeta 'traidas.txt'
$Diario   = Join-Path $Carpeta 'diario.txt'
$Clon     = Join-Path $Carpeta 'clon'

if (-not (Test-Path $Registro)) { New-Item -ItemType File -Path $Registro | Out-Null }
$YaHechas = @(Get-Content $Registro | Where-Object { $_ -match '^OK\s' } | ForEach-Object { ($_ -split '\s+')[1] })

$Pendientes = $SESIONES | Where-Object { $YaHechas -notcontains $_ }

Escribir ''
Escribir "Sesiones de la nube en el indice : $($SESIONES.Count)"
Escribir "Ya traidas en intentos anteriores : $($YaHechas.Count)"
Escribir "Quedan por intentar               : $($Pendientes.Count)" 'Cyan'
Escribir "Carpeta de trabajo                : $Carpeta"
Escribir ''

if ($SoloEnsenar) {
  Escribir 'Modo -SoloEnsenar: no se trae nada. Estas son las que faltan:' 'Yellow'
  $Pendientes | ForEach-Object { Escribir "  $_" }
  exit 0
}

if ($Pendientes.Count -eq 0) {
  Escribir 'No queda ninguna pendiente.' 'Green'
  exit 0
}

# --- 2. El clon aparte -------------------------------------------------------

if (-not (Test-Path (Join-Path $Clon '.git'))) {
  Escribir 'Clonando el repositorio en una copia aparte (solo la primera vez)...'
  git clone --depth 1 https://github.com/canelamoraguezandyjesus-bot/sirius.git $Clon
  if ($LASTEXITCODE -ne 0) { Escribir 'El clon ha fallado.' 'Red'; exit 1 }
}

# --- 3. Una a una, apuntando ------------------------------------------------

$Bien = 0
$Mal  = 0
Push-Location $Clon
try {
  foreach ($id in $Pendientes) {
    $marca = (Get-Date).ToString('HH:mm:ss')
    Write-Host -NoNewline "[$marca] $id ... "
    $salida = & claude --teleport $id 2>&1
    $codigo = $LASTEXITCODE
    if ($codigo -eq 0) {
      $Bien++
      Write-Host 'OK' -ForegroundColor Green
      Add-Content $Registro "OK $id $marca"
    } else {
      $Mal++
      Write-Host "FALLO (codigo $codigo)" -ForegroundColor Red
      Add-Content $Registro "FALLO $id $marca codigo=$codigo"
      Add-Content $Diario "=== $id ($marca, codigo $codigo) ==="
      Add-Content $Diario ($salida | Out-String)
    }
    Start-Sleep -Seconds $EsperaSegundos
  }
}
finally {
  Pop-Location
}

# --- 4. El resultado, con su cifra ------------------------------------------

Escribir ''
Escribir "Traidas en esta pasada : $Bien" 'Green'
Escribir "Fallaron               : $Mal" $(if ($Mal -gt 0) { 'Red' } else { 'Gray' })
if ($Mal -gt 0) {
  Escribir "El error de cada una esta en: $Diario" 'Yellow'
  Escribir 'Vuelve a lanzar el guion: se salta las que ya salieron bien.' 'Yellow'
}

$Origen = Join-Path $env:USERPROFILE '.claude\projects'
if (Test-Path $Origen) {
  $Zip = Join-Path $Carpeta ('sesiones_' + (Get-Date).ToString('yyyyMMdd_HHmm') + '.zip')
  Compress-Archive -Path (Join-Path $Origen '*') -DestinationPath $Zip -Force
  Escribir ''
  Escribir "Zip con todas las sesiones locales: $Zip" 'Cyan'
  Escribir 'Ese es el fichero que hay que mandar a la sesion que este haciendo la auditoria.'
}
