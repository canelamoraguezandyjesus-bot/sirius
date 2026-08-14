# ADR-012 — Un proceso local que corre como el usuario está dentro de la frontera de confianza

- Estado: PROPUESTO
- Fecha: 2026-08-14
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

La lente de seguridad de AUDITOR-V0-RUN-001 (incidencia #154) señaló que el
diario de captura escribe sus ficheros de marcas en la ruta que decide el
interlocutor del WebSocket, sin acotarla, y que ese interlocutor no tiene que
autenticarse ante Sirius.

El verificador independiente reprodujo el hecho técnico y **no pudo dictaminar**:
lo dejó en NO CONCLUYENTE, con este razonamiento —que es el que hace falta
registrar—: las dos fuentes normativas que el hallazgo invocaba no dicen lo que
afirmaba, el comportamiento que proponía como esperado rompería una función
aprobada, y el impacto exige un atacante que ya está dentro. Lo que quedaba en
pie no era un incumplimiento, sino **una pregunta de política que ningún
documento del repositorio responde**: ¿el modelo de amenaza de Sirius 0.1
incluye un proceso local, corriendo como el usuario, que suplanta a OBS en el
puerto configurado?

Sin esa frontera escrita, el mismo hallazgo volverá en cada auditoría, y cada
verificador volverá a gastar el mismo trabajo para volver a no poder decidirlo.

## Criterio de parada (escrito ANTES de decidir)

Este ADR fija una frontera, no un mecanismo. Si mañana aparece un vector que
**no** exija estar ya dentro de esa frontera —por ejemplo, un interlocutor
remoto, o un proceso con menos privilegios que el usuario—, esta decisión no lo
cubre y hay que decidir de nuevo en vez de estirarla.

## Opciones consideradas

1. **No incluirlo en el modelo de amenaza y dejarlo escrito.**
2. Contener la escritura: el diario solo escribe junto al vídeo si la ruta es
   absoluta y su directorio padre ya existe, y nunca crea directorios.
3. Endurecer la autenticación: si hay contraseña configurada y el servidor no
   la pide, abortar la conexión.

## Decisión

**Opción 1**, decidida por el propietario el 14 de agosto de 2026.

Sirius 0.1 es una aplicación de escritorio Windows, local y monousuario. Un
proceso que ya corre como el usuario puede escribir esos mismos ficheros por sí
solo, sin necesidad de suplantar a nadie: **no gana nada haciéndolo**. Tratarlo
como atacante obligaría a defenderse de quien ya tiene las llaves, que es una
defensa que no defiende.

Queda dentro de la frontera de confianza, y por tanto **no es un defecto** que
el diario acepte la ruta que le da su interlocutor local.

Esto es coherente con el modelo de amenaza ya vigente para la clave de API
(`docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` §14: «sesión de Windows
confiable; malware/administrador fuera de alcance de 0.1»); lo que hacía falta
era decir en voz alta que la misma frontera cubre al interlocutor del WebSocket.

## Comprobación que la sostiene

- El hecho técnico está reproducido por el verificador: el diario escribe donde
  dice el interlocutor. No se discute el hecho, se decide su condición.
- Las fuentes que el hallazgo invocaba se leyeron íntegras (#127) y no exigen lo
  que se les atribuía.
- Lo que esta decisión **no** dice: que la escritura esté acotada (no lo está),
  ni que el interlocutor esté autenticado (no lo está). Dice que, dentro de esta
  frontera, ninguna de las dos cosas es un defecto de Sirius 0.1.

## Consecuencias

- Un hallazgo futuro sobre este mismo mecanismo se cierra citando este ADR, sin
  volver a investigarlo, mientras el vector siga exigiendo estar dentro.
- La contraseña del WebSocket **sigue siendo un secreto** pese a esta decisión:
  su problema no es el modelo de amenaza sino que se guarda en texto plano
  incumpliendo una regla escrita (`AGENTS.md`). Son cosas distintas y esta
  decisión no la absuelve.
- Si Sirius deja de ser monousuario y local —o si el puerto deja de ser
  loopback—, esta frontera caduca y hay que rehacerla.

## Alternativas descartadas y por qué

Las opciones 2 y 3 son baratas y defendibles, y siguen disponibles si la
frontera cambia. Se descartan hoy porque **defienden de quien ya está dentro**:
añaden mecanismo, y con él superficie que mantener y probar, sin cerrar ningún
vector que la frontera no cubra ya. La opción 3 tiene además un coste inmediato
que conviene decir: las pruebas de integración actuales usan un servidor sin
autenticación como caso normal, así que habría que rehacerlas.
