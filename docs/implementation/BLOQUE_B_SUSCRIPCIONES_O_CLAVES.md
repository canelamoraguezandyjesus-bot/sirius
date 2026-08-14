# Bloque B — ¿Sirven las suscripciones para un runner multimodelo, o hacen falta claves de API?

- **Fecha:** 15 de agosto de 2026
- **Pregunta que responde:** la del §4 de
  [`AGENTES_SUPERFICIE_DE_INVOCACION.md`](AGENTES_SUPERFICIE_DE_INVOCACION.md),
  la única incógnita que bloquea toda la línea multimodelo.
- **Encargo:** el Bloque B del §7 de ese documento. No construye el adaptador
  ni convierte el runbook: solo responde la pregunta, con la comprobación
  delante.

## Nota de arranque (escrita y comprometida ANTES del experimento)

1. **¿Dónde vive la respuesta y dónde puede observarse?** En el propio
   paquete Inspect AI: qué credenciales exigen sus proveedores es un hecho de
   su código y de sus errores de arranque, observable instalándolo en un
   entorno desechable y pidiéndole un modelo sin credencial puesta. No hace
   falta gastar dinero en oír responder a ningún modelo: la pregunta es qué
   PIDE, no qué contesta.

2. **¿Qué NO va a garantizar este informe?** No prueba la cuenta de ChatGPT
   Business del propietario (aquí no hay forma de iniciar su sesión, y no se
   va a intentar); no mide el coste real por ejecución de ningún proveedor
   (eso exige llamadas reales de pago); y no prueba tokens que este entorno
   no posee — no se extrae ni se reutiliza ninguna credencial de la sesión.

3. **Criterio de parada:** si la instalación de Inspect no es posible en este
   entorno (red, proxy), el experimento se declara NO CONCLUYENTE y se deja
   escrito qué máquina lo puede responder — no se sustituye la medición por
   lo que diga la documentación de nadie, que es justo lo que la
   investigación externa dejó sin verificar.

4. **¿Qué haría el fallo imposible en vez de improbable?** Cada afirmación de
   la tabla de resultados lleva al lado el comando ejecutado y su salida
   literal recortada. Una afirmación sin su comando no entra en la tabla.

## Resultado

**La respuesta es distinta para cada suscripción, y eso cambia el plan.**

| Suscripción | ¿Sirve para un runner? | Cómo |
|---|---|---|
| **Claude** (la actual) | **Sí — ya demostrado** para motores Claude Code; **mecanismo verificado y pendiente de una prueba de 5 min** para Inspect | Abajo, caminos 1 y 2 |
| **ChatGPT Business** | **No por ningún camino que Inspect ofrezca** | Solo `OPENAI_API_KEY` de pago por uso |

### Método

Entorno desechable en la máquina de la sesión (Linux, sin ninguna clave de
proveedor en el entorno — se verificó con `env | grep` antes de empezar):
`inspect-ai 0.3.258` instalado con `uv`, más los SDK `anthropic` y `openai`.
Ninguna llamada de pago: se midió qué credencial **pide** cada proveedor y
hasta dónde llega el arranque, no qué contesta ningún modelo.

### Lo medido, con su comando delante

**1. Sin credencial, Inspect pide claves de API — literal:**

```text
$ inspect eval tarea.py --model anthropic/claude-3-5-haiku-latest
ERROR: Unable to initialise Anthropic client
No ANTHROPIC_API_KEY defined in the environment.

$ inspect eval tarea.py --model openai/gpt-4o-mini
ERROR: Unable to initialise OpenAI client
No OPENAI_API_KEY, AZUREAI_OPENAI_API_KEY, or managed identity (Entra ID)
```

**2. PERO el proveedor `anthropic` trae un camino OAuth que la investigación
externa no mencionó** — leído en su código
(`inspect_ai/model/_providers/anthropic.py:380-394`):

```python
# Support OAuth Bearer auth via ANTHROPIC_AUTH_TOKEN. When set,
# create the client with auth_token= (sends Authorization: Bearer)
auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
if auth_token:
    return AsyncAnthropic(..., auth_token=auth_token,
        default_headers={"anthropic-beta": "oauth-2025-04-20"}, ...)
```

Ese es exactamente el mecanismo del token de suscripción de Claude Code (los
`sk-ant-oat…` que produce `claude setup-token` — el mismo tipo de token que es
`CLAUDE_CODE_OAUTH_TOKEN` en los secretos de este repositorio).

**3. El camino funciona mecánicamente de punta a punta.** Con un token OAuth
**falso**, Inspect arranca, envía la petición con `Authorization: Bearer` y la
API de Anthropic la evalúa y responde `401 … invalid`. Es decir: cliente,
cabeceras y transporte están bien; lo único que este entorno no puede comprobar
es si un token de suscripción **válido** pasa la política del servidor — aquí
no hay ningún token del propietario y no se extraen credenciales de la sesión.

**4. El proveedor `openai` NO tiene equivalente.** Se buscó
`oauth|chatgpt|subscription|auth_token` en `openai.py` y `openai_compatible.py`:
las únicas coincidencias son nombres de modelo (`is_codex()` se refiere a los
modelos codex, no a la CLI ni a su inicio de sesión). La suscripción ChatGPT
Business no da acceso a la API de OpenAI; para Inspect hace falta
`OPENAI_API_KEY`, que es pago por uso.

**5. La suscripción de Claude YA ejecuta agentes hoy, en producción de este
repositorio.** No es una promesa: el workflow del Auditor (ADR-016) corrió dos
veces el 14-08 autenticado con `claude_code_oauth_token` — un token de
suscripción, no una clave de API. Para motores que son Claude Code, la
pregunta del §4 lleva respondida desde el estreno.

**6. Dos datos más del paquete, relevantes para el plan:**
- El **Agent Bridge** de Inspect (docstring de
  `inspect_ai/agent/_bridge/bridge.py`) integra «agentes de terceros que usan
  la API de OpenAI o de Anthropic» redirigiendo su tráfico al modelo que
  Inspect gobierna — el camino natural para meter Claude Code dentro de un
  eval de Inspect sin reescribir el runbook.
- Trae proveedores **sin clave ninguna**: `ollama`, `llama_cpp_python`, `hf`
  (modelos locales). La línea multimodelo barata existe, a cambio de hardware
  propio — casa con la parte Nemotron/local de la investigación externa, y
  sigue igual de no verificada en cuanto a calidad.

### Lo que este informe NO demuestra

- Que un token de suscripción válido sea aceptado por la política del servidor
  de Anthropic para tráfico de Inspect (prueba de cierre abajo).
- Nada sobre la cuenta ChatGPT Business del propietario en sí: solo que
  Inspect no ofrece ningún camino que la use.
- Ningún coste real por ejecución: no se hizo ninguna llamada de pago.
- Calidad ni obediencia a JSON Schema de ningún modelo: fuera del encargo.

### La prueba de cierre (5 minutos, máquina del propietario)

```powershell
# 1. Generar un token de suscripción (abre el navegador):
claude setup-token
# 2. En un venv desechable con inspect-ai + anthropic instalados:
$env:ANTHROPIC_AUTH_TOKEN = "<el token>"
inspect eval tarea.py --model anthropic/claude-3-5-haiku-latest
```

Si responde, la suscripción de Claude alimenta Inspect y la línea multimodelo
arranca sin gasto nuevo en el lado Claude. Si devuelve 401/403, ese lado
también exige clave de API y la decisión de gasto es previa a todo.

### Consecuencia para el orden del §6

1. **Lado Claude:** resuelto para motores Claude Code; a una prueba de 5 min
   para Inspect. Sin gasto nuevo en ningún caso.
2. **Lado OpenAI:** multimodelo con GPT = `OPENAI_API_KEY` = pago por uso =
   decisión de gasto del propietario. **No hay atajo por la suscripción.**
3. **Lado local (Ollama/llama.cpp):** sin claves y sin gasto por uso; el coste
   es hardware y calidad por validar.

La incógnita del §4 queda **respondida en lo que este entorno puede medir**, y
reducida a una prueba de 5 minutos en Windows para el único cabo que queda.
