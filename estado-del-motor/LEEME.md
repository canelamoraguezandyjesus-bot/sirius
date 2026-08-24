# La memoria del motor

Aquí vive el diario del Work Engine: lo que hizo, cuándo y por qué. Es un
fichero por línea, en JSON, que solo crece.

**Por qué está dentro del repositorio.** Porque el motor corre dentro de GitHub
Actions (ADR-082, decisión I4 del propietario en #270) y el disco del runner
muere con el trabajo. Confirmarlo aquí es la única forma de que la memoria
sobreviva de una invocación a la siguiente.

**Esto no es código y nada lo construye.** Vive aparte a propósito: si el diario
compartiera sitio con el código, cada línea de contabilidad dispararía la
revisión de calidad entera —veinte minutos por una anotación—.

**Cuando el motor lo teclea el propietario**, el diario NO vive aquí: vive en el
directorio de datos de su plataforma, fuera del árbol. Esa decisión sigue
vigente (ADR-055) y ADR-082 solo la deroga para la ejecución dentro de Actions.
Las dos ubicaciones conviven sin tocar código, por `--diario` y
`SIRIUS_MOTOR_DIARIO`.

**No se edita a mano.** Es append-only con checksum por registro; una edición
manual lo invalida.
