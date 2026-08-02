[app]

# Nombre del producto. Determina el nombre de la carpeta que pyside6-deploy
# copia a exec_directory (Sirius.dist).
title = Sirius

# Raiz del proyecto, relativa al directorio de este archivo. Este archivo vive
# en la raiz del repositorio, asi que el valor correcto es el punto.
project_dir = .

# Punto de entrada, relativo a la raiz del repositorio.
input_file = src/sirius/__main__.py

# Destino intermedio del artefacto compilado, bajo build/ (ignorado por Git).
# scripts/build_windows.ps1 traslada el contenido a dist/windows/.
exec_directory = build/deploy

# Sirius no usa un archivo de proyecto de Qt.
project_file =

# Vacio a proposito: pyside6-deploy aplica el icono por omision de PySide6.
# Fijar una ruta aqui incrustaria una ruta absoluta del equipo que construye.
icon =

[python]

# Vacio a proposito: el interprete efectivo es el del entorno bloqueado por
# uv.lock. scripts/build_windows.ps1 lo inyecta en la copia de trabajo de esta
# configuracion, para que este archivo no contenga rutas locales.
python_path =

# Version de Nuitka fijada para B13. Nuitka ya viene instalado y bloqueado por
# el grupo `packaging` de uv.lock, de modo que pyside6-deploy lo encuentra
# instalado y no descarga ni instala nada.
packages = Nuitka==4.1.3

android_packages =

[qt]

# Sirius es Qt Widgets puro: sin QML y sin Qt WebEngine.
qml_files =

excluded_qml_plugins =

# Modulos Qt de Sirius. Valor informativo: pyside6-deploy 6.11.1 lo vacia al
# arrancar (Config.__init__ ejecuta el setter `modules = []`, que reescribe la
# clave) y despues siempre vuelve a escanear el arbol, de modo que este valor no
# se puede fijar. El escaneo devuelve estos mismos tres modulos, pero en un
# orden que varia entre ejecuciones. No afecta al binario: lo unico que Nuitka
# recibe es --include-qt-plugins, derivado de `plugins`, que si queda fijado
# aqui abajo.
modules = Core,Gui,Widgets

# Plugins Qt fijados, tal y como los deduce pyside6-deploy a partir de los
# modulos anteriores. Nuitka descarta despues los que ya incluye por defecto.
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,platforminputcontexts,platforms,platforms/darwin,platformthemes,styles,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

[android]

wheel_pyside =

wheel_shiboken =

plugins =

[nuitka]

macos.permissions =

# B13 exige STANDALONE. Este valor tiene prioridad sobre el argumento --mode de
# la linea de ordenes, cuyo valor por omision es onefile.
mode = standalone

# --windows-console-mode=disable   aplicacion de escritorio, sin consola.
# --output-filename=Sirius.exe     el ejecutable se llama Sirius.exe.
# --msvc=latest                    obliga a usar MSVC x64; sin el, Nuitka podria
#                                  recurrir a otro compilador.
# --assume-yes-for-downloads       evita que la construccion se quede esperando
#                                  una respuesta interactiva por las utilidades
#                                  de analisis de Nuitka. El compilador queda
#                                  fijado por --msvc, no se descarga.
#
# Las dos inclusiones siguientes son obligatorias y no son opcionales de estilo.
# Alembic NO importa migrations/env.py ni migrations/versions/*.py: los lee del
# disco y los ejecuta en tiempo de ejecucion. Nuitka analiza imports estaticos,
# de modo que nada de lo que solo usan esos archivos externos entra en el binario
# y la aplicacion muere al migrar con ModuleNotFoundError.
#
# --include-module=logging.config  lo usa migrations/env.py (fileConfig). No lo
#                                  importa ningun modulo compilado de Sirius.
# --include-package=alembic        migrations/versions/*.py hacen "from alembic
#                                  import op" y env.py "from alembic import
#                                  context". alembic.command, que si es
#                                  alcanzable estaticamente, no importa ninguno
#                                  de los dos.
# --nofollow-import-to=mypy        sqlalchemy.ext.mypy y pydantic.mypy importan
#                                  mypy de forma estatica: son extensiones para
#                                  el comprobador de tipos, no codigo de
#                                  ejecucion. Sin esta exclusion, --follow-imports
#                                  mete mypy entero en el artefacto (22 MB) y ata
#                                  el contenido del paquete a una dependencia del
#                                  grupo `dev`. Sirius no importa mypy en tiempo
#                                  de ejecucion.
extra_args = --quiet --noinclude-qt-translations --windows-console-mode=disable --output-filename=Sirius.exe --msvc=latest --assume-yes-for-downloads --include-module=logging.config --include-package=alembic --nofollow-import-to=mypy

[buildozer]

mode = debug

recipe_dir =

jars_dir =

ndk_path =

sdk_path =

local_libs =

arch =
