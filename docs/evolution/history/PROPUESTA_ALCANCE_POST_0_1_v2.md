# Sirius — Tarjeta de referencia

> **Estado vigente:** HISTÓRICO / NO NORMATIVO. Esta propuesta originó la auditoría post-0.1, pero sus definiciones y su enfoque de «un módulo por fila» fueron sustituidos por el Documento Rector de Evolución v1.0 y las decisiones EV-001 a EV-014.

## Visión de Sirius

Sirius no es el cerebro. Es **los ojos, las manos y la memoria continua**. El pensar difícil lo sigue haciendo el consultor externo (hoy Claude) cuando se le invoca. Sirius es quien está siempre presente, quien ve cuando se le pide, quien mueve cosas por ti, y quien no deja que se pierda nada entre sesiones.

La analogía: **tú eres el jefe. Sirius es tu asistente/secretaria. El consultor externo es el asesor al que se llama para lo difícil.** Tres roles, no uno compitiendo con otro.

**Sobre OpenAI y la voz:** Sirius ya llama hoy a una API de modelo (OpenAI) para pensar en texto — eso es programar un adaptador propio que usa una API, no instalar una app ajena. Si mañana Sirius reconoce o habla, sería la misma categoría: un adaptador propio de Sirius que llama a una API de voz (también puede ser OpenAI, u otra). Eso no es "meter Rewind o Copilot" — es la misma dependencia que ya existe hoy con el texto, solo que para voz.

**Qué es esto:** el punto de partida para lo siguiente. Por cada fila, hay que desarrollar un módulo propio de Sirius (código nuestro, dentro del repositorio) que reproduzca ese comportamiento. Ninguna de estas apps se instala ni se integra: solo se imita cómo resuelven el problema.

| App / patrón real | Qué hace | Módulo que programamos en Sirius (código propio) |
|---|---|---|
| **Copilot Vision** | Ve la pantalla solo cuando tú compartes, nunca antes. | Vista bajo demanda: nada activo hasta que se lo pides. |
| **Rewind / Limitless** | Grababa todo el rato; fundía el portátil; la empresa cerró. | Aviso: nunca grabación continua. |
| **LUCI** (alternativa abierta a Rewind) | Memoria persistente entre sesiones, local, autoalojable. | Memoria propia, en tu máquina, no en la nube de otro. |
| **Zapier Agents / Central** | Un orquestador decide qué herramienta usar, con permiso por alcance y paradas obligatorias. | Sirius reparte tareas a sus propias funciones, con permiso explícito para lo irreversible. |
| **MCP (Model Context Protocol)** | Estándar para conectar una IA a herramientas de forma ordenada. | La forma en que organizamos las herramientas propias de Sirius (no un servicio, un estándar a seguir). |
| **Claude Code Action** (GitHub) | Etiquetas un issue → se crea sola una rama y un borrador de PR. | Rutinas por etiqueta: pones una etiqueta, Sirius dispara el trabajo. |
| **Claude Cowork / Computer Use** | Una IA opera el ordenador con permiso; aún floja cruzando varias apps. | Referencia de qué tan lejos llegar por ahora: con permiso, no autónomo del todo. |
| **Pi (Inflection)** | Compañera conversacional gratuita, cercana, sin postureo. | Referencia de tono para la personalidad de Sirius. |

**Siguiente paso histórico:** desarrollar, módulo por módulo, cómo se programa cada fila dentro de Sirius.
