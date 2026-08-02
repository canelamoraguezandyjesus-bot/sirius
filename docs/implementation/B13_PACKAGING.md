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
| Mismos archivos fuente y mismo commit | `source_commit` en `BUILD-MANIFEST.json` |
| Dependencias bloqueadas | `uv.lock`, con `uv lock --check` y `uv sync --frozen` |
| Configuración de despliegue versionada | `pysidedeploy.spec` en la raíz |
| Un único comando canónico | `.\scripts\build_windows.ps1` |
| Mismo modo de Nuitka | `mode = standalone`, verificado en el dry-run |
| Misma estructura de artefacto | Montaje explícito, verificado por el script de verificación |
| Versiones exactas del toolchain | `BUILD-MANIFEST.json` |
| Inventario íntegro | `FILE-MANIFEST.sha256` |
| Hash del entregable | `<artefacto>.zip.sha256` |
| Sin pasos manuales ocultos | El script carga MSVC por sí mismo |

## Prerrequisitos externos

Deben estar instalados en el equipo que construye. El script **no** los instala:

- **Windows 11 x64**.
- **Visual Studio Build Tools 2022** con el workload *Desktop development with
  C++*, incluyendo:
  - MSVC v143 — VS 2022 C++ x64/x86 build tools (aporta `cl.exe` y `dumpbin.exe`);
  - Windows 11 SDK.
- **uv** en el `PATH`.

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

Verificar (desde PowerShell **sin elevar**):

```powershell
.\scripts\verify_windows_package.ps1
```

La verificación toma por omisión el artefacto más reciente de `dist\windows`.
También acepta uno explícito:

```powershell
.\scripts\verify_windows_package.ps1 -ArtifactPath dist\windows\Sirius-0.1.0.dev0-<sha>-windows-x64
```

## Rutas de salida

```
dist/windows/Sirius-<versión>-<sha corto>-windows-x64/          carpeta portátil
dist/windows/Sirius-<versión>-<sha corto>-windows-x64.zip        entregable
dist/windows/Sirius-<versión>-<sha corto>-windows-x64.zip.sha256 hash del ZIP
build/deploy/Sirius.dist/                                        salida intermedia
build/packaging/pyside6-deploy-dry-run.txt                       comando Nuitka efectivo
build/packaging/build-<marca temporal>.log                       log completo
```

`build/` y `dist/` están ignorados por Git: **ni el binario, ni el ZIP, ni los
logs se confirman en el repositorio**.

`pyside6-deploy` impone además su propio directorio intermedio en
`src/sirius/deployment/` (no es configurable: lo deriva del archivo de entrada).
Intenta purgarlo al terminar, pero se traga el `PermissionError` y solo avisa,
de modo que puede dejar más de 1 GB dentro de `src/` — lo que ensucia el árbol
de Git y, peor, deja archivos `module.*.c` rancios que hacen fallar la siguiente
compilación con `assert not os.path.isfile(...)`. Por eso
`build_windows.ps1` lo elimina explícitamente y con reintentos, tanto antes de
construir como después de una compilación correcta. Si la compilación falla, ese
directorio se conserva a propósito para diagnóstico y lo limpia la siguiente
ejecución.

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
uv sync --frozen --group packaging
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

**Lo verificado es el ZIP que se distribuye, no la carpeta de trabajo de
`dist/`.** El orden es deliberado: primero se comprueba el SHA-256 del ZIP;
después se extrae ese mismo ZIP a una ruta temporal con espacios; y todo lo
demás —inventario de hashes, contaminación y los dos arranques— se hace sobre
la copia extraída. Si el ZIP no coincide con su hash, no se extrae nada y la
verificación se detiene. La afirmación final queda limitada al ZIP cuyo hash se
verificó.

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
  válido. Nunca se usa la configuración real ni se introduce clave alguna.
- **E. Smoke test**: primer arranque (proceso vivo, ventana superior visible,
  `sirius.db` creado, esquema en el head de Alembic, sin error de migraciones,
  sin `RecursionError`, sin `Traceback` no controlado) y segundo arranque
  reutilizando el mismo entorno (sin duplicar ni corromper el esquema,
  `PRAGMA integrity_check` = `ok`, revisión de Alembic estable).
- **F. Rutas con espacios**: tanto la extracción del paquete como el directorio
  de datos contienen espacios.
- **G. Sin administrador**: si PowerShell está elevado, la verificación se
  detiene y **no** se declara superada.
- **Integridad del `data_location.json` real**: antes del primer arranque se
  anota si existe y, si existe, su SHA-256; después del segundo arranque se
  comparan existencia y hash como comprobaciones reales. Si el ejecutable
  hubiera creado, borrado o modificado el puntero del usuario pese al entorno
  redirigido, la verificación falla. La ruta se resuelve con el mismo criterio
  que la aplicación (`resolve_paths().config_dir`).

## Prueba de onboarding sin clave

Redirigir `LOCALAPPDATA`, `APPDATA` y `USERPROFILE` **no aísla Windows
Credential Manager**. La credencial pertenece a la sesión del usuario de
Windows, no al sistema de archivos: al arrancar, el ejecutable construye el
adaptador real de `keyring` y `main.py::_build_initial_window` llama a
`has_key()`, que consulta la credencial del usuario que ejecuta la prueba.

En una máquina que ya tiene guardada la clave real, el ejecutable seguiría el
camino **con** clave, y una verificación que solo comprobase «hay una ventana»
pasaría igualmente sin haber probado el onboarding.

Por eso la verificación evalúa antes una **precondición**:

- consulta solo la **existencia** mediante el puerto de aplicación
  (`ApiKeySettingsUseCase.has_key()`), que por contrato devuelve un booleano y
  nunca el valor;
- no lee, imprime, exporta, modifica ni borra la credencial, y no usa `cmdkey`;
- identificador consultado: servicio `Sirius`, clave `openai_api_key`
  (`src/sirius/config/secrets_config.py`).

Si la credencial **existe**, la comprobación de que la ventana corresponde al
flujo sin clave se marca `[OMITIDA]`, el resto de la verificación continúa y el
resultado final es **SUPERADA CON RESERVAS**, enumerando expresamente lo que no
se ha demostrado. La credencial real no se toca en ningún caso.

Si la credencial **no existe**, se comprueba además que el título de la ventana
es el de `OnboardingWindow` (`Sirius 0.1 — Primera configuración`), no
simplemente que exista alguna ventana de Sirius.

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

1. El log completo de la última construcción está en
   `build/packaging/build-<marca temporal>.log`, y el comando efectivo de Nuitka
   en `build/packaging/pyside6-deploy-dry-run.txt`. Ambos están bajo `build/`,
   ignorado por Git.
2. Al compartir un log, revísalo antes: contiene rutas locales del equipo que
   construye. No incluye claves ni datos de Sirius, porque el artefacto no los
   contiene y la construcción se detiene si aparecen.
3. Para un fallo de arranque, el registro de la aplicación está en
   `<directorio de datos>/logs/application.log`. Ese archivo **sí** pertenece al
   usuario: no lo adjuntes entero; extrae únicamente la traza relevante. El
   registro aplica además un filtro de redacción para valores con forma de clave.
4. La verificación conserva su entorno temporal completo bajo
   `%TEMP%\Sirius Packaging Smoke Test` para inspección. Son datos de prueba
   desechables, nunca los del usuario.
5. Distingue siempre las tres causas al informar: fallo del código de Sirius,
   fallo de configuración del empaquetado, o dependencia externa ausente
   (compilador o SDK).
