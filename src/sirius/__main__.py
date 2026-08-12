"""Permite abrir Sirius con ``python -m sirius``.

Existe por algo que pasó de verdad: en Windows, una reinstalación a medias deja
el atajo ``sirius`` sin instalar —la carpeta estaba bloqueada y el borrado del
paquete anterior falló a mitad—, y a partir de ahí no había ninguna forma de
abrir la aplicación sin arreglar antes la instalación. El código descargado
estaba entero y correcto, pero era inalcanzable.

Con esto siempre se puede arrancar lo que hay en el disco, sin depender de que
el instalador haya terminado bien. Es la misma aplicación y el mismo punto de
entrada: aquí no vive ninguna lógica.
"""

from sirius.main import main

raise SystemExit(main())
