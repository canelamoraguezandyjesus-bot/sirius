# ADR-234 — Llevar la charla de Sirius al Ollama de este ordenador y elegir su modelo a ciegas

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza C de ADR-233; la decisión de
  que la charla vaya a un modelo local elegido a ciegas es del propietario, la 4 del
  05-10-2026 (EV-023).

## Nota de arranque

Escrita antes del primer commit de la rama de la pieza C. El criterio de parada de las
rondas es el de ADR-233: como mucho tres por PR, y dos de la misma familia paran.

1. **Dónde vive el fallo y dónde va el arreglo.** La charla solo sabía ir a OpenAI
   (`src/sirius/config/llm_provider_settings.py`, dos proveedores) y nada en Sirius dejaba
   comparar modelos. El arreglo va en el mismo sitio donde se elige proveedor: un tercer
   proveedor, `ollama`, con su adaptador, y una prueba a ciegas que guarda el modelo
   elegido en los mismos ajustes. Puede observar el fallo: las pruebas de aceptación
   PA-R02-02 y PA-R02-03 mandan la charla por el ensamblaje de verdad y miran lo que llega
   a un Ollama de mentira.
2. **Qué NO garantiza.** Que un modelo local tenga gracia: eso lo dice el propietario en
   E-R02-01. Que el modelo quepa en su gráfica de 6 GB con 8.192 tokens de contexto: se ve
   al instalarlo. La prueba a ciegas tiene sentido con la semilla del robot, la pieza B:
   con la de 0.1 compararía modelos con la identidad vieja.
3. **Criterio de parada.** El de ADR-233. Además: si para que la charla vaya por Ollama
   hubiera que tocar cómo se arma el contexto, se para, porque eso es de las piezas D y F.
4. **Qué lo haría imposible.** Que la charla salga del ordenador: la dirección es fija y
   absoluta en cada petición, no hay ajuste que la cambie y el cliente no lee los proxies
   del sistema. Que el propietario vea de quién es una respuesta antes de elegir: la hoja
   guarda la clave aparte y las respuestas no llevan el nombre del modelo.

## Contexto y problema

La versión 0.2 del plan del robot pide, en su paso 2 de personalidad, que la charla pase a
un modelo local, «sobre la pieza que ya existe para cambiar de modelo», y en su paso 9 una
prueba a ciegas: 20 preguntas a dos o tres modelos, respuestas barajadas y sin nombre, y el
propietario elige. Ollama ya estaba en Sirius, pero solo para clasificar recuerdos.

## Opciones consideradas

1. **Un adaptador nuevo detrás del puerto `LLMProvider`**, elegido con `llm_provider:
   "ollama"` como hoy se elige `openai`.
2. **Pasar por la biblioteca `ollama` de Python.** Una dependencia más para lo que ya hacen
   `httpx` y cuatro adaptadores de la casa contra la misma API.
3. **La prueba a ciegas fuera de Sirius**, en un guion que escriba una página. El
   propietario tendría que ejecutar órdenes y copiar el resultado a mano.

## Decisión

Se adoptan la opción 1 y, para la prueba, una ventana dentro de Sirius.

- **`src/sirius/adapters/llm/ollama_chat.py`**: `OllamaChatProvider` habla con
  `/api/chat` en streaming y traduce a los eventos del puerto.
  - Siempre a `http://localhost:11434`, con la dirección absoluta en cada petición y
    `trust_env=False`: un proxy configurado en Windows podría sacar del ordenador hasta lo
    que va a `localhost`. Las pruebas pasan un transporte, nunca una dirección.
  - Pide `num_ctx` explícito, 8.192 por defecto y nunca menos de 2.048, porque lo que no
    cabe en el contexto se recorta y la semilla va delante.
  - Deja el modelo cargado 30 minutos (`keep_alive`) para que la primera frase tras una
    pausa no espere a cargarlo.
  - Quita `<think>…</think>` y la sugerencia de recuerdo antes de que exista un solo
    trozo de texto, aunque lleguen partidos. El separador de la sugerencia, que vivía
    dentro del adaptador de OpenAI, pasa a `src/sirius/adapters/llm/memory_suggestion.py`
    y lo usan los dos.
  - Sin reintentos: si Ollama no contesta en este ordenador, reintentar no lo arregla.
- **Ajustes**: `llm_provider: "ollama"` y `ollama_chat_model`. Sin modelo elegido no hay
  modelo por defecto: la charla dice que falta hacer la prueba a ciegas, porque el modelo
  lo elige el propietario.
- **La prueba a ciegas**:
  - `src/sirius/domain/blind_test.py`: las 20 preguntas, el barajado y el recuento. Con
    empate en cabeza no elige: elige el propietario entre los empatados.
  - `src/sirius/application/blind_test.py`: pregunta a cada modelo con la misma
    identidad con la que conversa Sirius, en peticiones aparte que no tocan la
    conversación ni la memoria. La identidad la escribe `render_identity`, que comparten
    la charla y la prueba.
  - `src/sirius/presentation/blind_test_dialog.py`: elegir dos o tres de los modelos que
    tiene Ollama, esperar, elegir pregunta a pregunta y confirmar. Los nombres salen en el
    resultado, y nada se guarda hasta que pulsa «Usar … para la charla».
  - Se abre desde la pestaña Configuración, que dice con qué modelo conversa Sirius.
- **Al arrancar** con la charla en Ollama no se pide la clave de OpenAI, que no se usa.

## Comprobación que la sostiene

- Las cuatro pruebas de aceptación de la pieza, PA-R02-02 y PA-R02-03, pasan por el
  ensamblaje de verdad, `build_conversation_dependencies`, con un Ollama de mentira
  enchufado como transporte.
- Vistas fallar con el código estropeado a propósito: con la charla mandada a
  `ejemplo.com`, falla «solo puede ir a este ordenador»; sin barajar, falla «la hoja
  baraja»; con el nombre del modelo en cada respuesta, falla la misma.
- Pruebas unitarias del adaptador, 18, que incluyen la etiqueta `<think>` y el delimitador
  partidos entre trozos, la cancelación a mitad, el modelo que no está instalado y un
  Ollama que no contesta. Del barajado, el recuento y el caso de uso, 14. De la ventana, 7.
  De la elección de proveedor, 6 nuevas. Del arranque, 2 nuevas.

## Consecuencias

- El propietario puede elegir el modelo en cuanto tenga dos o tres instalados en Ollama.
  Con sentido, después de la pieza B: la semilla.
- `ConversationDependencies` lleva `blind_test_use_case`, y `build_conversation_dependencies`
  acepta `ollama_transport` solo para las pruebas.
- La pestaña Configuración sigue ofreciendo `openai`: el giro no borra nada que funcione.

## Alternativas descartadas y por qué

- **Un modelo por defecto si no hay ninguno elegido.** Sería elegir por el propietario,
  contra su decisión 4.
- **Leer la dirección de Ollama de los ajustes.** Abriría la puerta a que la charla saliera
  del ordenador, que es justo lo que EV-023 cierra.

## La lección

- ninguna: es la primera pieza de código de la versión y no ha mordido nada que alguien
  pudiera repetir.
