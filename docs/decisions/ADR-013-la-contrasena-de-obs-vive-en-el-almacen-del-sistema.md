# ADR-013 — La contraseña de OBS vive en el almacén del sistema, y sin él no se guarda

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario
- Numeración: 011 y 012 están tomados por ramas abiertas (correlación de OBS y
  frontera de confianza). Se comprueba antes de asignar porque en la PR #153 se
  crearon dos ADR-008 por no hacerlo.

## Contexto y problema

La lente de seguridad de AUDITOR-V0-RUN-001 (incidencia #154) encontró que la
contraseña del servidor WebSocket de OBS se escribía en claro en
`settings.json`. Un verificador independiente siguió la cadena entera y la
sostuvo, bajando la gravedad de P1 a P2.

Los hechos, comprobados: la contraseña entra por `capture_setup`, se serializa
en claro con `json.dumps(..., indent=4)` y se relee en cada arranque desde
`composition_root`. El fichero que la contiene se declara a sí mismo
«Non-sensitive local configuration storage». Y es una credencial: la
investigación técnica del propio repositorio dice que esa contraseña es lo que
impide que el puerto local quede abierto a cualquier proceso que lo encuentre.

`AGENTS.md` línea 20 lo prohíbe expresamente —«No guardes claves en código,
SQLite, logs o archivos de texto»— y el verificador no encontró ninguna
decisión, ADR, incidencia ni prueba que levantara esa regla. El puerto que lo
evitaría, `SecretStore`, ya estaba construido y en uso para la clave de API.

Conviene decir lo que NO es este problema: no es una brecha explotable a
distancia. El ámbito es una instancia local de OBS, el fichero vive en el perfil
del usuario y no viaja en copias, exportaciones ni registros. Es un
**incumplimiento normativo verificado**, y esa es razón suficiente.

## Criterio de parada (escrito ANTES de decidir)

Si al mover la contraseña resultara que el almacén no puede sostenerla —por
ejemplo, que `keyring` no esté disponible en el entorno real de destino—, no se
inventa un tercer sitio donde guardarla: se para y se decide de nuevo. Un
«temporalmente en texto plano» es como nació este defecto.

## Opciones consideradas

1. **Moverla al almacén seguro ya**, rechazando el guardado si no está
   disponible, y migrando la que ya estuviera escrita.
2. Moverla, pero permitir una excepción avisada en texto plano cuando no haya
   almacén seguro, para que Captura nunca quede inutilizable.
3. Dejarlo como está y registrar la excepción a `AGENTS.md` en un ADR, aceptando
   el texto plano para una credencial de servicio en loopback.

## Decisión

**Opción 1**, elegida por el propietario el 14 de agosto de 2026.

La contraseña pasa al almacén del sistema, junto a la clave de API. **Sin
almacén seguro no se guarda**: es el mismo criterio que ya rige para la clave de
API, y mantenerlo evita la asimetría de tratar como secreto una credencial y no
la otra.

Con migración, que es lo que hace que la decisión sirva de algo: al leerla, una
contraseña que estuviera en `settings.json` se traslada al almacén y se borra
del fichero. Sin ese paso, limitarse a dejar de escribirla dejaría el texto
plano de las instalaciones existentes ahí para siempre — el arreglo protegería
solo a quien instalara Sirius por primera vez.

## Comprobación que la sostiene

- Tres pruebas nuevas, con **mutación verificada en las dos direcciones**:
  devolver la contraseña a `settings.json`, guardar sin almacén seguro, y quitar
  la migración. Las tres ponen su prueba en rojo; con el arreglo, en verde.
- Suite completa: 2091 pruebas en verde, 2 omitidas (MS-A02, ya documentada).
- **Lo que NO demuestra:** que el Credential Manager real de Windows la guarde y
  la devuelva. Las pruebas usan el doble de siempre. Esto entra en la lista de
  validaciones manuales pendientes, junto a la de la clave de API.

## Consecuencias

- Sin almacén seguro, el Módulo Captura **no se puede configurar**. Es
  deliberado y es el precio de la opción elegida: la alternativa era conservar
  una vía de texto plano, que es el defecto que se está cerrando.
- Un fallo del almacén **no impide arrancar Sirius**: sin contraseña, Captura no
  conecta y lo dice. Lo destapó una prueba de GUI existente cuando el error se
  propagaba hasta la construcción de la ventana.
- La primera ejecución tras actualizar retira sola el texto plano heredado, sin
  que el usuario tenga que hacer nada.
- El nombre del secreto (`obs_websocket_password`) queda fijado en
  `secrets_config.py` junto al de la clave de API: renombrarlo después dejaría
  huérfana la contraseña ya guardada.

## Alternativas descartadas y por qué

La **opción 2** conserva exactamente la vía que se quiere cerrar: mientras
exista un camino que escriba la contraseña en texto plano, el defecto sigue ahí
para cualquiera que caiga en ese camino, y el aviso no lo impide —los avisos se
leen una vez y el fichero se queda para siempre—.

La **opción 3** es defendible en su análisis de riesgo: el ámbito es loopback y
el modelo de amenaza aprobado excluye malware y administrador (ver ADR-012). Se
descarta porque el coste de cumplir la regla ya escrita es bajo —el puerto
existe y funciona—, y levantar una prohibición de `AGENTS.md` para ahorrarse ese
coste sienta un precedente peor que el problema que resuelve.
