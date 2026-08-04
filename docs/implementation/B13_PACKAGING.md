# B13 — Empaquetado reproducible de Sirius 0.1 para Windows 11 x64

## Propósito

Convertir el árbol de Sirius 0.1 en una **carpeta portátil** para Windows 11 x64
mediante un único comando, de forma repetible y auditable, sin instalador y sin
que el ordenador de destino necesite Python ni uv.

Cubre el defecto **A-03 (Empaquetado reproducible)** y la decisión técnica
**ATD-011**.

## Alcance

Dentro de B13:

- proceso canónico de construcción (`scripts/build_windows.ps1`);
- configuración de despliegue versionada (`pysidedeploy.spec`);
- toolchain de empaquetado bloqueado en `uv.lock` (grupo `packaging`);
- artefacto portátil standalone, comprimido en ZIP, con manifiesto y hashes;
- verificación automática del artefacto (`scripts/verify_windows_package.ps1`).

Fuera de B13:

- **B14** (Windows sin clave), **B15** (ventana compacta con proveedor real) y
  **B16** (PA-E2E-01, regresión y cierre) siguen pendientes;
- la aceptación manual **PA-019** no queda cubierta: el smoke test de B13 es una
  comprobación técnica desechable que arranca y termina el proceso, no una
  sesión de uso real;
- no se declara Sirius 0.1 aceptada ni terminada.

## Qué significa «reproducible» aquí

**No** significa identidad binaria byte a byte. Dos construcciones del mismo
commit **no** tienen por qué producir el mismo hash: Nuitka incorpora marcas
temporales y rutas de construcción en el binario, de modo que el SHA-256 del ZIP
cambia entre construcciones. Esa limitación está declarada expresamente en el
campo `reproducibility_note` de cada `BUILD-MANIFEST.json`.

Lo que B13 sí garantiza:

| Garantía | Dónde se sostiene |
|---|---|
| Mismos archivos fuente y mismo commit | worktree temporal detached, comprobación final de Git y `source_commit` en `BUILD-MANIFEST.json` |
| Dependencias bloqueadas | `uv.lock`, con `uv lock --check` y `uv sync --frozen` |
| Configuración de despliegue versionada | `pysidedeploy.spec` en la raíz |
| Un único comando canónico | `.\scripts\build_windows.ps1` |
| Mismo modo de Nuitka | `mode = standalone`, verificado en el dry-run |
| Misma estructura de artefacto | Montaje explícito, verificado por el script de verificación |
| Versiones exactas del toolchain | `BUILD-MANIFEST.json` |
| Inventario íntegro | `FILE-MANIFEST.sha256` |
| Hash del entregable | `<artefacto>.zip.sha256` |
| Sin pasos manuales ocultos | El script carga MSVC por sí mismo |

## Entorno de empaquetado

El build **no** usa la `.venv` del repositorio. Tiene su propio entorno en:

```
%LOCALAPPDATA%\Sirius\packaging-venv
```

seleccionado con `UV_PROJECT_ENVIRONMENT`, que es el mecanismo soportado por uv
para usar un entorno de proyecto distinto del `.venv` por omisión. Verificado
contra uv 0.8.17: crea el entorno en la ruta indicada, instala solo las
dependencias normales más el grupo pedido, y **deja intacta** la `.venv` del
proyecto.

El acceso a ese entorno compartido se serializa con un bloqueo global:

```
%LOCALAPPDATA%\Sirius\.b13-packaging-venv.lock
```

El handle exclusivo se comparte entre todos los clones que construyan bajo la
misma cuenta de Windows y cubre `uv sync`, el inventario del entorno, Nuitka y
la limpieza. El archivo marcador puede persistir después de terminar; solo un
handle exclusivo abierto indica que una construcción sigue activa.

El motivo es un fallo real, dos veces seguidas en Windows antes de llegar a
compilar:

```
Acceso denegado al eliminar .venv\Lib\site-packages\ast_serialize-0.6.0.dist-info\sboms
Acceso denegado al eliminar .venv\Lib\site-packages\coverage-7.15.0.dist-info\licenses
```

La causa no era el permiso, era el diseño. `check.ps1` deja en `.venv` los grupos
normales y `dev`; el build ejecutaba `uv sync --no-default-groups --group
packaging` **sobre esa misma `.venv`**, así que uv hacía exactamente lo que se le
pedía: desinstalar las herramientas de desarrollo. Bajo OneDrive, borrar esos
árboles falla. Reintentar habría sido insistir en destruir el entorno de
desarrollo con más paciencia.

Consecuencias, todas comprobadas por `tests/unit/test_packaging_environment_isolation.py`:

- el build no lee, no sincroniza y no borra nada dentro de `<repo>\.venv`;
- la ruta está fuera del checkout y fuera de OneDrive, y el script aborta si
  alguien la reapunta dentro del repositorio;
- el inventario del entorno sigue exigiendo PySide6, Nuitka, Alembic, SQLAlchemy
  y keyring, y la ausencia de mypy, pytest, Ruff, pytest-qt y pytest-cov;
- esa ruta no aparece en `pysidedeploy.spec` versionado ni en el artefacto; el
  propio build rechaza un spec que contenga `.venv`, una unidad, `$env:`,
  `%TEMP%` o `%USERPROFILE%`.

El **verificador** sí usa la `.venv` de desarrollo, pero solo para leer: necesita
un intérprete con `sirius` importable para consultar SQLite, resolver
`resolve_paths()` y evaluar la precondición de credencial. No la sincroniza.

## Prerrequisitos externos

Deben estar instalados en el equipo que construye. El script **no** los instala:

- **Windows 11 x64**.
- **Visual Studio Build Tools 2022** con el workload *Desktop development with
  C++*, incluyendo:
  - MSVC v143 — VS 2022 C++ x64/x86 build tools (aporta `cl.exe` y `dumpbin.exe`);
  - Windows 11 SDK.
- **uv** en el `PATH`.

No hace falta instalar `python.exe` ni `py.exe` globalmente. El controlador
arranca sus helpers, que usan solo la biblioteca estándar, con Python 3.14
administrado por uv mediante:

```powershell
uv run --no-project --managed-python --python 3.14 python
```

`uv` sigue siendo el único prerrequisito Python del comando canónico. La opción
`--no-project` impide descubrir o cargar el proyecto antes de ejecutar las
guardas; `--managed-python` evita depender de una instalación global. Si ese
runtime no existe todavía, uv puede provisionarlo en su caché mediante su
mecanismo normal de Python administrado, sin convertirlo en una dependencia del
artefacto ni usar la `.venv` del repositorio.

No hace falta abrir una «Developer PowerShell»: `build_windows.ps1` localiza la
instalación con `vswhere.exe` y carga `VsDevCmd.bat -arch=x64` por sí mismo.

Si falta el compilador o el SDK, el script se detiene con un mensaje
`BLOCKED_EXTERNAL_TOOLCHAIN` indicando el componente exacto que falta, sin
descargar ni instalar nada y sin recurrir a un compilador alternativo.

## Comandos

Construir:

```powershell
.\scripts\build_windows.ps1
```

Ese sigue siendo el único comando operativo. El controlador comprueba primero
que el checkout original está completamente limpio, captura su SHA exacto y los
metadatos mínimos del manifiesto, y valida tanto la ruta del entorno bajo
`LOCALAPPDATA` como una raíz temporal privada y única fuera del checkout.

Después de esas guardas y antes de abrir el bloqueo de publicación o crear el
worktree, abre `%LOCALAPPDATA%\Sirius\.b13-packaging-venv.lock` con un handle
exclusivo. Lo conserva durante `uv sync`, el inventario del entorno, Nuitka y la
limpieza, de modo que dos clones de la misma cuenta no pueden sincronizar ni
usar simultáneamente el entorno global de empaquetado.

Después abre `dist/windows/.b13-publish.lock` con un handle exclusivo
(`FileShare.None`) y lo conserva durante **toda** la construcción, la
publicación, cualquier rollback y la limpieza final. El bloqueo se apoya en el
sistema de archivos, por lo que coordina procesos y sesiones de Windows que
comparten ese destino. Una segunda ejecución concurrente se rechaza antes de
compilar. El archivo marcador puede permanecer después: no representa un
bloqueo obsoleto, porque la exclusividad depende del handle abierto y Windows lo
libera automáticamente cuando el proceso termina.

Después crea en la raíz temporal un `git worktree add --detach` del SHA
capturado. La implementación versionada se invoca desde ese worktree: código,
`pyproject.toml`, `uv.lock`, `pysidedeploy.spec`, migraciones, versión, head de
Alembic, módulos importados, entradas de Nuitka y montaje del contenido proceden
exclusivamente del snapshot. El checkout original ya solo es controlador y
destino final. Antes de publicar, el build elimina el scratch legítimo de
Nuitka, vuelve a exigir que el worktree apunte al mismo SHA y que Git no muestre
ningún archivo rastreado modificado ni archivo inesperado sin rastrear. Una
discrepancia aborta sin publicar.

Antes de delegar en `build_windows_impl.ps1`, el wrapper captura una instantánea
completa del entorno del proceso. En un `finally`, elimina todas las variables
creadas por la implementación y restaura todos los valores previos, incluidos
`PATH`, `UV_PROJECT_ENVIRONMENT` y los importados por `VsDevCmd.bat`. Cada
restauración se intenta de forma independiente; sus fallos se agregan y quedan
visibles sin ocultar una excepción original de la construcción.

La publicación trata la carpeta portátil, el ZIP y su `.sha256` como una sola
transacción. Los resultados anteriores se mueven primero a una carpeta privada
`.publish-<guid>/backup`, y los nuevos se registran separadamente conforme se
publican. Si una operación falla, se intentan **todas** las retiradas y
restauraciones, aunque falle alguna intermedia. La transacción solo se elimina
cuando el rollback ha terminado por completo. Si el rollback también falla, la
carpeta `.publish-<guid>` se conserva bajo `dist/windows/` con los backups aún
disponibles, y el error informa tanto del fallo original como de cada fallo de
restauración y de la ruta exacta para recuperación manual.

Ese mismo bloque `finally` elimina siempre el worktree y su raíz temporal y
libera los handles de los bloqueos de publicación y del entorno compartido.
Antes de esa limpieza, si la construcción falla y existen diagnósticos de
compilación, el controlador copia fuera del snapshot únicamente el log
`build-*.log`, el informe `nuitka-crash-report-*.xml`, el dry-run de Nuitka y un
`failure.txt`. Se guardan bajo `build/packaging-diagnostics/` del checkout
original; un fallo al copiarlos se informa sin ocultar la excepción original.

Verificar (desde PowerShell **sin elevar**):

```powershell
.\scripts\verify_windows_package.ps1
```

La verificación **no** toma «el más reciente»: busca exclusivamente el ZIP cuyo
nombre corresponde a la versión actual y al SHA corto del `HEAD` actual, y tras
extraerlo compara `source_commit` y `source_commit_short` del
`BUILD-MANIFEST.json` con el `HEAD` real. Si el artefacto no existe, o procede de
otro commit, la verificación falla y lo dice.

Esto también nace de un caso real: las dos construcciones de `f9b68d5` fallaron y
no dejaron artefacto, pero el verificador encontró el ZIP de `a82972f` de una
ronda anterior, lo validó y terminó como *SUPERADA CON RESERVAS*, acreditando un
commit que no era el del repositorio. Una verificación de B13 no puede acreditar
el artefacto de otro commit. La lógica vive en `scripts/package_provenance.py`,
cubierta por `tests/unit/test_package_provenance.py`.

También acepta uno explícito:

```powershell
.\scripts\verify_windows_package.ps1 -ArtifactPath dist\windows\Sirius-0.1.0.dev0-<sha>-windows-x64
```

## Rutas de salida

```
%LOCALAPPDATA%/Sirius/.b13-packaging-venv.lock                  marcador global del entorno; puede persistir sin estar bloqueado
dist/windows/.b13-publish.lock                                 marcador del bloqueo; puede persistir sin estar bloqueado
dist/windows/Sirius-<versión>-<sha corto>-windows-x64/          carpeta portátil
dist/windows/Sirius-<versión>-<sha corto>-windows-x64.zip        entregable
dist/windows/Sirius-<versión>-<sha corto>-windows-x64.zip.sha256 hash del ZIP
dist/windows/.publish-<guid>/                                    recuperación solo si el rollback de publicación falla
<snapshot temporal>/build/deploy/Sirius.dist/                    salida intermedia
<snapshot temporal>/build/packaging/pyside6-deploy-dry-run.txt   comando Nuitka efectivo
<snapshot temporal>/build/packaging/build-<marca temporal>.log   log completo temporal
build/packaging-diagnostics/<sha>/<ejecución>/                   diagnóstico persistente solo si falla
```

Las rutas bajo `<snapshot temporal>` son salidas de trabajo efímeras y se
eliminan junto con el worktree al terminar. En una construcción correcta, los
únicos resultados publicados son los tres elementos normales bajo
`dist/windows/`. Los marcadores `.b13-publish.lock` y
`%LOCALAPPDATA%\Sirius\.b13-packaging-venv.lock` pueden persistir vacíos y no
deben interpretarse como construcciones activas: en ambos casos solo el handle
exclusivo abierto representa el bloqueo. El primero serializa la publicación
del destino y el segundo protege el entorno compartido durante `uv sync`,
inventario, Nuitka y limpieza entre todos los clones de la misma cuenta. La
carpeta `.publish-<guid>` no queda tras éxito ni tras un rollback completo; solo
se conserva cuando una restauración falla, precisamente para no destruir sus
backups. En una construcción fallida, el controlador conserva antes de limpiar
una copia selectiva de los diagnósticos técnicos bajo
`build/packaging-diagnostics/`; no copia volcados completos del entorno.

`build/` y `dist/` están ignorados por Git: **ni el binario, ni el ZIP, ni los
logs se confirman en el repositorio**.

`pyside6-deploy` impone además su propio directorio intermedio en
`src/sirius/deployment/` (no es configurable: lo deriva del archivo de entrada).
Intenta purgarlo al terminar, pero se traga el `PermissionError` y solo avisa.
Por eso el build lo elimina explícitamente y con reintentos antes de construir y
después de una compilación correcta. Vive únicamente dentro del worktree
temporal: nunca ensucia el checkout original y, incluso si la compilación falla,
la limpieza final elimina el worktree completo después de conservar los
diagnósticos seleccionados.

## Estructura del artefacto

```
Sirius-<versión>-<sha>-windows-x64/
├── Sirius.exe                 punto de entrada único
├── *.dll, *.pyd               runtime de Python, Qt y dependencias (Nuitka)
├── PySide6/                   plugins de Qt
├── alembic.ini                configuración de Alembic, sin URL de datos fija
├── migrations/                entorno y revisiones de Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/*.py
├── BUILD-MANIFEST.json        procedencia y versiones del toolchain
└── FILE-MANIFEST.sha256       SHA-256 de cada archivo del artefacto
```

`alembic.ini` y `migrations/` viajan **junto a `Sirius.exe`** porque el
resolvedor empaquetado
(`sirius.adapters.persistence.migrations._resource_root`) los busca en
`Path(sys.executable).parent` cuando detecta que corre compilado. Solo se copian
archivos **controlados por Git** (`git ls-files migrations`), conservando la
estructura: nunca una copia a ciegas del directorio.

## Datos excluidos

El artefacto no contiene, y la construcción se detiene si aparecen:

- bases de datos (`*.db`, `*.db-wal`, `*.db-shm`);
- `.env`, `.env.*`, `settings.json`, `data_location.json`;
- `application.log` y carpetas `logs`, `backups`, `exports`;
- material de clave privada (cualquier `.pem`, `.crt`, `.cer` o `.key` que
  contenga un bloque `-----BEGIN … PRIVATE KEY-----`) y almacenes de
  credenciales (`.pfx`, `.p12`, `.jks`, `.keystore`);
- rutas de usuario copiadas como archivos;
- cualquier archivo de texto que contenga algo con forma de clave `sk-…`;
- `__pycache__`, `.pyc`, cachés y resultados de pruebas.

La inspección de claves se limita a archivos de texto razonables y **nunca
imprime el supuesto secreto**: informa solo de la ruta y detiene la construcción.

Los certificados se juzgan por contenido, no por extensión. Un almacén **público**
de CA sí viaja en el artefacto y es necesario: `certifi/cacert.pem` es lo que usa
el cliente HTTPS para verificar al proveedor. Lo que nunca puede viajar es una
clave privada. La construcción lista cada certificado público incluido como
aviso, para que quede a la vista.

Los datos de Sirius viven **fuera** del ejecutable, en el directorio local
elegido por el usuario. El artefacto no incrusta base de datos, configuración,
registros, claves ni datos personales.

## Versiones bloqueadas

Las de ejecución y empaquetado están fijadas en `uv.lock`. El grupo `packaging`
de `pyproject.toml` contiene el toolchain y está deliberadamente **fuera** de las
dependencias normales y del grupo `dev`, de modo que ni el entorno de desarrollo
ni el artefacto arrastran Nuitka:

```toml
[dependency-groups]
packaging = [
  "nuitka==4.1.3",
  "ordered-set",
  "zstandard",
]
```

Versiones exactas del intento de referencia (las de cada construcción concreta
quedan registradas en su `BUILD-MANIFEST.json`):

| Componente | Versión |
|---|---|
| Python | 3.14.6 (64 bits) |
| uv | 0.11.28 |
| PySide6 / Qt | 6.11.1 / 6.11.1 |
| Nuitka | 4.1.3 |
| ordered-set | 4.1.0 |
| zstandard | 0.25.0 |
| MSVC | `cl` 19.44.35228 (toolset 14.44.35207) |
| Windows SDK | 10.0.26100.0 |

La reproducibilidad depende de `uv.lock`, **no** de instalaciones globales.

## Cómo comprobar el SHA-256

```powershell
Get-FileHash .\dist\windows\Sirius-<versión>-<sha>-windows-x64.zip -Algorithm SHA256
Get-Content  .\dist\windows\Sirius-<versión>-<sha>-windows-x64.zip.sha256
```

Ambos valores deben coincidir. `verify_windows_package.ps1` hace esta
comprobación automáticamente, y además verifica archivo por archivo contra
`FILE-MANIFEST.sha256`.

## Reproducir desde un checkout limpio

```powershell
git clone <url> sirius
cd sirius
git switch --detach <commit>
.\scripts\build_windows.ps1
.\scripts\verify_windows_package.ps1
```

`pysidedeploy.spec` es portable a propósito: no contiene rutas absolutas, ni
rutas a `.venv`, ni el usuario local. El script de construcción rechaza la
configuración si detecta una ruta local, y genera su propia copia de trabajo con
rutas absolutas bajo `build/packaging/`, de modo que `pyside6-deploy` —que
reescribe el archivo de configuración que recibe— nunca toque el archivo
versionado ni ensucie el árbol de Git.

## Qué comprueba la verificación

**Lo verificado es una copia congelada del ZIP que se distribuye, no la carpeta
de trabajo de `dist/` ni el ZIP original mientras puede seguir cambiando.** El
orden real es deliberado:

1. localiza el ZIP original y su `.sha256`;
2. valida que el archivo de hash sea pequeño y contenga un SHA-256 válido;
3. crea una raíz temporal privada y única;
4. copia el ZIP en bloques a una copia congelada, con un límite de 1 GiB
   comprobado antes de crear el destino y durante la escritura; cualquier copia
   parcial se elimina;
5. calcula el hash de la copia congelada y lo compara con el valor esperado;
6. inspecciona únicamente la copia congelada;
7. extrae únicamente la copia congelada;
8. vuelve a calcular su hash después de inspeccionarla y extraerla;
9. aborta si ese hash cambió;
10. ejecuta las comprobaciones y arranques únicamente sobre lo extraído de esa
    copia.

Si la copia acotada falla o no coincide con el hash esperado, no se extrae nada.
La afirmación final queda limitada a sus bytes verificados; en ningún momento se
inspecciona ni se extrae directamente el ZIP original.

La congelación, inspección y extracción del ZIP **no** viven duplicadas en el
`.ps1`, sino en `scripts/zip_package_inspector.py`, que el verificador invoca y
cuyo JSON consume. El motivo es concreto: en el parser vivió un fallo que
convivió con la comprobación de calidad en verde, porque
`ZipFile.CreateFromDirectory` de .NET Framework escribe los nombres con `\` y el
lector partía solo por `/`. Las pruebas ejercitan exactamente el helper que se
ejecuta y cubren ambos separadores, rutas inseguras, destinos duplicados,
enlaces, límites de tamaño y entradas, copia congelada acotada y eliminación de
salidas parciales. Las rutas se juzgan con `ntpath`, de modo que la semántica es
la de Windows aunque las pruebas corran en Ubuntu.

Antes de combinar cualquier ruta declarada por `FILE-MANIFEST.sha256` con
`$PackageRoot`, `scripts/file_manifest.py` valida el archivo completo con
semántica Windows. Impone límites de 4 MiB, 4096 entradas y 4096 caracteres por
línea; rechaza hashes inválidos, rutas vacías, absolutas, con unidad o UNC,
segmentos vacíos, `.` o `..`, escapes de la raíz y destinos duplicados después
de normalizar separadores y mayúsculas. Solo las entradas ya confinadas llegan
a `Join-Path` y `Get-FileHash`: una entrada rechazada no provoca lectura ni hash
de un destino externo.

- **A. ZIP y estructura**: SHA-256 del ZIP frente a su `.zip.sha256`; el ZIP
  debe tener exactamente una raíz y llamarse como el artefacto; tras extraer,
  `Sirius.exe`, `alembic.ini`, `migrations/`, `BUILD-MANIFEST.json` y
  `FILE-MANIFEST.sha256`; todos los hashes del inventario contra los archivos
  extraídos; ningún archivo del manifiesto ausente, ninguno de más, y el
  recuento de entradas del ZIP cuadrando con el manifiesto; ausencia de datos y
  secretos.
- **B. Independencia del repositorio**: se ejecuta el `Sirius.exe` extraído del
  ZIP, con un directorio de trabajo distinto del repositorio, del ejecutable y
  de los datos, y con datos y directorio de trabajo fuera de la carpeta
  extraída. La localización de Alembic no puede depender del directorio actual.
- **C. Independencia de Python y uv**: el proceso se lanza con un `PATH` reducido
  a componentes básicos de Windows, sin Python, sin uv, sin `.venv` y sin
  variables del repositorio. No se desinstala nada del equipo.
- **D. Datos desechables**: `LOCALAPPDATA`, `APPDATA`, `USERPROFILE`, `TEMP` y
  `TMP` apuntan a una raíz temporal aislada, con un `data_location.json` mínimo
  válido. `HOMEDRIVE` y `HOMEPATH` se derivan únicamente de ese `USERPROFILE`, y
  el verificador exige que ambos lo reconstruyan exactamente; no se pasan los
  valores reales del usuario. Nunca se usa la configuración real ni se
  introduce clave alguna.
- **E. Smoke test**: primer arranque (proceso vivo, ventana superior visible,
  `sirius.db` creado, esquema en el head de Alembic, sin error de migraciones,
  sin `RecursionError`, sin `Traceback` no controlado) y segundo arranque
  reutilizando el mismo entorno (sin duplicar ni corromper el esquema,
  `PRAGMA integrity_check` = `ok`, revisión de Alembic estable). Cada proceso se
  termina desde un `finally`, incluso si falla el sondeo de ventanas o una
  comprobación intermedia.
- **F. Rutas con espacios**: tanto la extracción del paquete como el directorio
  de datos contienen espacios.
- **G. Sin administrador**: si PowerShell está elevado, la verificación se
  detiene y **no** se declara superada.
- **Integridad del `data_location.json` real**: antes del primer arranque se
  anota si existe y, si existe, su SHA-256; después de los arranques se comparan
  existencia y hash como comprobaciones reales. Estas postcondiciones, junto con
  la de Credential Manager, se ejecutan desde un `finally` aunque fallen el
  arranque o las consultas SQLite. Si el ejecutable hubiera creado, borrado o
  modificado el puntero del usuario pese al entorno redirigido, la verificación
  falla. La ruta se resuelve con el mismo criterio que la aplicación
  (`resolve_paths().config_dir`).

## Prueba de onboarding sin clave

Redirigir `LOCALAPPDATA`, `APPDATA` y `USERPROFILE` **no aísla Windows
Credential Manager**. La credencial pertenece a la sesión del usuario de
Windows, no al sistema de archivos: al arrancar, el ejecutable construye el
adaptador real de `keyring` y `main.py::_build_initial_window` llama a
`has_key()`, que consulta la credencial del usuario que ejecuta la prueba.

Por eso `ABSENT` es una **precondición obligatoria** antes de ejecutar
`Sirius.exe`. La sonda consulta el servicio `Sirius` y la clave
`openai_api_key` mediante `ApiKeySettingsUseCase.has_key()`:

- si devuelve `ABSENT`, el verificador puede continuar con los dos arranques;
- si devuelve `PRESENT` o `ERROR`, el verificador aborta antes de ejecutar
  código del paquete y no manipula Credential Manager.

Conviene ser exacto sobre la sonda. **Credential Manager sí se consulta**, y
`has_key()` obtiene internamente el valor mediante `SecretStore.get_secret()`
para reducirlo a un booleano; por tanto, el secreto entra brevemente en memoria
del proceso, igual que durante un arranque normal de Sirius. Lo que se garantiza
es que la sonda solo emite `PRESENT`, `ABSENT` o `ERROR <TipoDeExcepción>`: no
imprime, devuelve, compara ni registra el valor secreto, y no modifica ni
elimina la credencial.

Cuando la precondición se cumple, el verificador exige que la ventana visible
sea la de `OnboardingWindow` (`Sirius 0.1 — Primera configuración`), no
simplemente cualquier ventana de Sirius. Después de los dos arranques vuelve a
consultar Credential Manager y exige que el estado continúe siendo `ABSENT`.
Esto demuestra que el paquete no dejó una credencial persistente en la sesión
real de Windows sin comparar, imprimir ni registrar valores secretos.

### Cómo ejecutar esta prueba de forma reproducible

Hace falta una sesión de Windows sin la credencial de Sirius. En orden de
preferencia:

1. **Cuenta local de Windows dedicada a pruebas.** Crea una cuenta estándar
   (Configuración → Cuentas → Otros usuarios), inicia sesión con ella, clona o
   copia el repositorio y ejecuta ahí `.\scripts\verify_windows_package.ps1`.
   Su bóveda de credenciales es independiente, así que la precondición se
   cumple sin tocar la credencial de tu cuenta habitual.
2. **Máquina virtual o equipo limpio de Windows 11 x64.** Equivalente a lo
   anterior y además valida la portabilidad real del paquete.
3. **Retirada temporal en tu propia cuenta.** Solo si aceptas volver a
   introducir la clave después: elimínala **desde la propia interfaz de
   Sirius** (Configuración → «Eliminar clave»), ejecuta la verificación y
   vuelve a guardarla. No se documenta ningún procedimiento con `cmdkey` ni con
   la interfaz de Credential Manager, porque manipular la bóveda a mano queda
   fuera de lo que Sirius debe pedir a nadie.

La opción 1 es la recomendada: no altera ningún estado y es repetible.

## Limitaciones

- **Sin reproducibilidad binaria bit a bit.** Ver arriba.
- **Sin instalador.** No hay MSI ni EXE de instalación, ni escritura en Program
  Files, ni registro global, ni servicios de Windows.
- **Sin firma de código.** El ejecutable no está firmado; Windows SmartScreen
  puede advertir en la primera ejecución.
- **Sin autoactualización.** Actualizar es sustituir la carpeta.
- **Sin onefile.** B13 usa exclusivamente `standalone`.
- **Solo Windows 11 x64.**
- **Python 3.14 sigue siendo zona de riesgo del toolchain**: Nuitka 4.1.3 avisa
  de que 3.14 tiene soporte experimental. El artefacto se valida por su
  comportamiento real en el smoke test, no por esa advertencia.
- El smoke test **no** sustituye a PA-019 ni a ninguna aceptación manual.
- **El registro de la aplicación deja de escribir después de migrar.**
  `migrations/env.py` llama a `fileConfig(alembic.ini)` con el
  `disable_existing_loggers=True` que trae `logging` por omisión, lo que deja
  los loggers `sirius` y `sirius.main` con `disabled=True`. Se comprobó
  reproduciéndolo también fuera del paquete, así que **no** lo causa el
  empaquetado: es un defecto de observabilidad de la aplicación (S13), y B13 no
  lo corrige por quedar fuera de su vertical. Consecuencia para la verificación:
  las comprobaciones sobre `application.log` (sin `Traceback`, sin
  `RecursionError`, sin error de migraciones) solo cubren con certeza hasta el
  final de las migraciones. Por eso el arranque completo se demuestra además con
  la ventana visible y con el esquema en el head de Alembic, que no dependen del
  registro.

## Diagnosticar un fallo sin exponer datos

1. Si la construcción falla después de generar diagnósticos, el controlador los
   copia antes de limpiar el snapshot a
   `build/packaging-diagnostics/<sha>/<ejecución>/`. Puede contener el log
   `build-*.log`, el dry-run efectivo, un informe de fallo de Nuitka y
   `failure.txt`. La ruta se imprime como `B13 DIAGNOSTICS`.
2. Si aparece `B13 PUBLISH ROLLBACK ERROR`, no borres la carpeta
   `dist/windows/.publish-<guid>/` indicada en el mensaje: contiene los backups
   que no pudieron restaurarse. El mismo mensaje conserva el error original y
   todas las restauraciones fallidas. No ejecutes otro build hasta recuperar o
   descartar conscientemente esos tres resultados.
3. Al compartir un log, revísalo antes: contiene rutas locales del equipo que
   construye. No incluye claves ni datos de Sirius, porque el artefacto no los
   contiene y la construcción se detiene si aparecen. El controlador no copia
   `msvc-env.txt` ni un volcado general del entorno.
4. Para un fallo de arranque, el registro de la aplicación está en
   `<directorio de datos>/logs/application.log`. Ese archivo **sí** pertenece al
   usuario: no lo adjuntes entero; extrae únicamente la traza relevante. El
   registro aplica además un filtro de redacción para valores con forma de clave.
5. La verificación conserva su entorno temporal completo bajo
   `%TEMP%\Sirius Packaging Smoke Test` para inspección. Son datos de prueba
   desechables, nunca los del usuario.
6. Distingue siempre las tres causas al informar: fallo del código de Sirius,
   fallo de configuración del empaquetado, o dependencia externa ausente
   (compilador o SDK).
