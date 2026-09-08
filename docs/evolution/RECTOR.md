# Documento Rector - Evolución de Sirius después de 0.1

**Identificador:** `SIRIUS-RECTOR-EVOLUCION-POST-0.1`  
**Versión:** 1.0  
**Estado:** APROBADO  
**Fecha:** 22 de julio de 2026  
**Autoridad final:** usuario responsable del Proyecto Sirius

> Este documento fija la dirección canónica posterior a Sirius 0.1. No modifica 0.1, no autoriza implementación futura y no sustituye las definiciones de producto, pruebas o arquitecturas técnicas que deberán aprobarse por versión.

## 1. Propósito

Sirius evolucionará desde un compañero persistente de texto hacia el punto personal de contacto entre el usuario, sus proyectos, especialistas, aplicaciones, automatizaciones y dispositivos.

Sirius interpretará la intención, recuperará el contexto necesario, decidirá si debe responder directamente o delegar, limitará permisos y recursos, supervisará la ejecución, reunirá resultados y los presentará de forma coherente. La identidad, la memoria y la responsabilidad permanecerán en Sirius.

## 2. Qué es Sirius en esta evolución

Sirius es:

- el compañero personal con identidad reconocible y criterio propio;
- la interfaz principal con el ecosistema digital y físico;
- el propietario de la memoria canónica y del mapa de contexto;
- el responsable de permisos, trazabilidad y continuidad;
- el integrador de resultados producidos por modelos, agentes y herramientas;
- un sistema independiente de cualquier proveedor concreto.

Sirius no es:

- un modelo LLM concreto;
- una secretaria pasiva;
- un simple router de peticiones;
- un gestor de proyectos con chat;
- una colección de copias de productos externos;
- un conjunto permanente de agentes hablando entre sí;
- un controlador de motores o seguridad física.

## 3. Mapa de responsabilidades

| Categoría | Responsabilidad |
|---|---|
| Sirius | Identidad, relación, criterio, memoria canónica, permisos, seguimiento, síntesis y responsabilidad final. |
| Orquestación interna | Coordinar tareas, estados, errores, presupuestos, cancelación y reintentos. |
| Inteligencia | Interpretar, razonar y generar mediante modelos sustituibles. |
| Especialista o agente | Realizar una tarea temporal y delimitada con rol, contexto, herramientas y criterio de terminado. |
| Herramienta | Consultar o modificar un sistema mediante una operación concreta. |
| Automatización | Ejecutar un flujo definido, reproducible y observable. |
| Protocolo | Conectar capacidades sin convertirse por sí mismo en producto. |
| Controlador físico | Aplicar límites, tiempos, estados seguros y parada; nunca se sustituye por un modelo. |
| Producto físico | Dispositivo independiente, como HEAD-R1, con requisitos, pruebas y autoridad propios. |

Los proveedores son sustituibles. Los roles se definen por capacidad y contrato, no por nombres comerciales.

## 4. Modelo de interacción

El modelo principal es híbrido.

1. El usuario habla normalmente con Sirius.
2. Sirius determina si puede resolver la tarea o necesita un especialista.
3. Cuando sea útil, abre una sesión especializada visible y acotada.
4. El usuario puede dialogar directamente con el especialista dentro de ese marco.
5. Sirius conserva el paquete de contexto, permisos, presupuesto y trazabilidad.
6. Al cerrar, Sirius sintetiza el resultado y propone qué debe conservarse.

Una sesión especializada no transfiere la propiedad del proyecto ni de la memoria. El usuario siempre sabe qué agente o herramienta está actuando.

## 5. Memoria, contexto y procedencia

- Sirius mantiene una única memoria canónica.
- Los especialistas reciben únicamente el contexto necesario para la tarea.
- Todo resultado delegado conserva autor, herramienta, fecha, alcance y evidencias.
- Ningún agente convierte una exploración en decisión aprobada.
- Los candidatos a memoria o decisión deben seguir las reglas canónicas de origen, confirmación, versión, sustitución, archivo, eliminación y conflicto.
- Los contextos temporales de trabajo pueden descartarse al cerrar una tarea.
- Los modelos externos no se convierten en fuente autoritativa del proyecto.

## 6. Habilidades, permisos y autonomía

La progresión aprobada conserva los niveles conceptuales:

1. consultar;
2. proponer;
3. preparar;
4. ejecutar una acción reversible;
5. ejecutar una acción sensible.

Cada capacidad deberá declarar:

- recursos accesibles;
- operaciones permitidas;
- duración del permiso;
- presupuesto y tiempo máximos;
- confirmaciones necesarias;
- posibilidad de cancelación y reversión;
- evidencia y registro resultantes;
- comportamiento ante fallo.

Los permisos generales e indefinidos no son el valor predeterminado.

## 7. Delegación supervisada

Una tarea delegada contendrá como mínimo:

- objetivo;
- resultado esperado;
- contexto mínimo;
- rol del especialista;
- herramientas autorizadas;
- presupuesto y plazo;
- límites de recurrencia o subdelegación;
- criterio de terminado;
- condiciones de parada;
- formato de evidencia.

El ciclo será:

`INTENCIÓN -> TAREA DELIMITADA -> CONTEXTO -> PERMISOS -> EJECUCIÓN -> EVIDENCIA -> REVISIÓN -> SÍNTESIS -> CIERRE`.

Sirius podrá rechazar o detener una delegación si el alcance se expande, el coste supera el límite, faltan permisos o el resultado no es verificable.

## 8. Condiciones para multiagente

El multiagente no es una meta por sí mismo. Antes debe funcionar la delegación a un especialista.

Podrá justificarse cuando exista evidencia de:

- subtareas realmente independientes;
- necesidad de competencias diferentes;
- revisión separada del autor;
- paralelismo que reduzca tiempo de forma material;
- fallos recurrentes del especialista único;
- necesidad de comparar conclusiones incompatibles.

Todo flujo multiagente tendrá límites de agentes, rondas, tiempo, coste y profundidad. Los desacuerdos no se ocultarán: Sirius elegirá cuando exista criterio aprobado o presentará la discrepancia al usuario.

RAG, embeddings, grafos y frameworks multiagente seguirán siendo alternativas técnicas, no requisitos de producto.

## 9. Roadmap aprobado

### 9.1 Sirius 0.2 - Memoria útil

**Problema:** 0.1 demuestra persistencia, pero no todavía selección y recuperación de alta calidad.  
**Incluye:** búsqueda mejorada, sugerencias confirmadas, conflictos asistidos, mejor recuperación y proyectos históricos consultables.  
**Excluye:** agentes, herramientas externas, voz y automatización.  
**Evidencia:** recupera información correcta a través de varias sesiones sin aumentar ruido.  
**Puerta:** puede construir un paquete de contexto fiable y trazable para una tarea externa.

### 9.2 Sirius 0.3 - Habilidades y permisos

**Problema:** Sirius aconseja, pero no ayuda operativamente.  
**Incluye:** contrato de habilidades, permisos acotados, consulta y una primera acción reversible, estado visible, cancelación y registro.  
**Excluye:** agentes autónomos, control general del ordenador y hardware.  
**Evidencia:** una habilidad real completa repetidamente una tarea sin acceder a recursos no autorizados.  
**Puerta:** Sirius puede supervisar una operación individual de principio a fin.

### 9.3 Sirius 0.4 - Delegación supervisada

**Problema:** algunas tareas necesitan capacidad especializada.  
**Incluye:** un especialista por tarea, paquete de contexto, presupuesto, seguimiento, artefactos, revisión y síntesis.  
**Excluye:** equipos permanentes, delegación recursiva y conversaciones abiertas entre agentes.  
**Evidencia:** una tarea real mejora mediante delegación sin fragmentar identidad, memoria o permisos.  
**Puerta:** la identidad y continuidad permanecen reconocibles durante sesiones especializadas.

### 9.4 Sirius 0.5 - Voz

**Problema:** la relación sigue limitada a teclado y pantalla.  
**Incluye:** entrada y salida de voz, interrupción, misma conversación, memoria e identidad, escucha explícita.  
**Excluye:** escucha ambiental continua, cámara y control físico.  
**Evidencia:** conversación natural, interrumpible y coherente con el historial escrito.  
**Puerta:** el usuario puede ordenar y supervisar habilidades sin tocar el teclado.

### 9.5 Sirius 0.6 - Percepción y automatización digital

**Problema:** Sirius no comprende el estado visible del ordenador ni coordina flujos entre sistemas.  
**Incluye:** captura o ventana bajo demanda, automatizaciones seleccionadas, notificaciones, tareas programadas y control limitado de aplicaciones.  
**Excluye:** grabación continua, observación silenciosa y acciones sensibles desatendidas.  
**Evidencia:** un flujo digital entre varias aplicaciones se completa con vista previa, confirmación, recuperación y trazabilidad.  
**Puerta:** Sirius representa un sistema externo y actúa sobre él de forma reversible.

### 9.6 Sirius 0.7 - Puente de laboratorio y dispositivos

**Problema:** Sirius sigue separado del espacio físico.  
**Incluye:** registro de dispositivos, lectura de estado, sensores autorizados, intenciones semánticas, puente de permisos y controladores deterministas.  
**Excluye:** control directo de motores, autonomía desatendida y movimientos sensibles decididos por un modelo.  
**Evidencia:** una intención de alto nivel se valida y ejecuta dentro de límites, y la pérdida de comunicación termina en estado seguro.  
**Puerta:** presencia física estable y útil.

### 9.7 Sirius 1.0 - Compañero en la habitación

Sirius 1.0 reunirá voz estable, memoria útil, identidad reconocible, presencia física y apoyo de extremo a extremo en un proyecto real.

El multiagente no es un requisito obligatorio de 1.0.

## 10. Voz, percepción y ordenador

La voz será otro canal del mismo Sirius, no otro asistente.

La percepción de pantalla, cámara o sensores será explícita, temporal, visible y cancelable. No habrá observación silenciosa ni captura continua por defecto.

Para operar el ordenador se preferirán integraciones estructuradas. El control visual se reservará para sistemas sin interfaz segura y requerirá confirmaciones y recuperación.

## 11. Automatización y proactividad

Sirius podrá ejecutar rutinas, vigilar condiciones y avisar cuando exista valor real, siempre con:

- origen y propósito visibles;
- frecuencia y duración limitadas;
- recursos autorizados;
- coste controlado;
- posibilidad de pausar o eliminar;
- ausencia de cambios sensibles silenciosos.

La proactividad no convierte a Sirius en un sistema autónomo con autoridad propia sobre la vida digital del usuario.

## 12. Laboratorio, dispositivos y HEAD-R1

HEAD-R1 es un producto físico hermano, no un módulo interno de Sirius.

Sirius será responsable de intención, permisos, contexto y presentación. HEAD-R1 será responsable de mecánica, electrónica, firmware local, calibración, límites, pruebas y seguridad física. Entre ambos existirá un puente de integración con autenticación, capacidades declaradas, validación, timeout, cancelación y registro.

Ningún modelo enviará ángulos, pulsos o secuencias libres a actuadores. El controlador local conservará límites, velocidad, aceleración, neutral, estado seguro y parada física.

HEAD-R1 puede avanzar independientemente mediante su herramienta determinista. La integración conversacional esperará a que Sirius disponga de habilidades, permisos y trazabilidad maduros.

## 13. Sirius participando en su desarrollo

Sirius podrá:

- preparar planes y cambios;
- coordinar un agente de programación;
- ejecutar pruebas autorizadas;
- leer resultados y logs minimizados;
- preparar firmware para revisión;
- colaborar en diagnóstico de hardware;
- proponer la siguiente iteración.

Sirius no podrá aprobar sus propios cambios, ampliar alcance sin decisión, publicar, fusionar, cargar firmware activo o ejecutar movimientos físicos sensibles sin el nivel de autorización correspondiente.

## 14. Referencias externas

Productos, protocolos y experiencias observadas se clasificarán como:

- referencia de comportamiento;
- proveedor o modelo;
- herramienta;
- motor de automatización;
- protocolo;
- patrón de interfaz;
- advertencia o antipatrón.

No se creará "un módulo por cada aplicación" ni se copiará su arquitectura sin una necesidad aprobada.

## 15. Riesgos de deriva y señales de parada

Debe detenerse una propuesta cuando:

- convierte a Sirius en router o secretaria;
- fragmenta la memoria entre proveedores;
- exige permisos generales;
- introduce arquitectura multiagente sin evidencia;
- mezcla varias versiones en una entrega;
- convierte proyectos en el centro administrativo;
- introduce control físico directo por modelos;
- amplía 0.1 por preparación futura;
- depende de un proveedor como identidad permanente;
- carece de una prueba observable de valor.

## 16. Gobernanza documental

Jerarquía aplicable:

1. Manual de Visión e Identidad.
2. Registro de Decisiones.
3. Este Documento Rector de Evolución.
4. Definición de Producto de cada versión.
5. Plan de Pruebas y Trazabilidad de esa versión.
6. Arquitectura Técnica de esa versión.
7. Implementación.

Este documento guía qué versiones crear y qué preguntas deben responder. No autoriza una capacidad por sí mismo.

## 17. Regla de activación

Una etapa post-0.1 solo comienza cuando:

- la etapa anterior produce la evidencia requerida o su hipótesis se revisa explícitamente;
- existe una Definición de Producto aprobada;
- existen pruebas de aceptación reproducibles;
- se aprueba la arquitectura técnica correspondiente;
- el alcance no se mezcla con etapas posteriores.

## 18. Aprobación

El usuario aprobó el 22 de julio de 2026 este documento y las decisiones EV-001 a EV-014. La aprobación fija dirección y gobernanza, pero no activa ninguna implementación posterior a Sirius 0.1.

## 19. Enmienda del 8 de septiembre de 2026 — separación entre Sirius y su motor

> **Por qué esta enmienda está al final y no en su sitio.** Los apartados que
> modifica están citados por número de línea desde la Arquitectura Técnica 0.2,
> el Plan de Pruebas 0.2, la Definición de Producto 0.2, `docs/evolution/STATUS.md`
> y ADR-102. Insertar texto antes de esas líneas las desplazaría y falsearía
> citas ya publicadas que no son de este trabajo. Es la misma restricción que
> `docs/evolution/STATUS.md` se aplicó a sí mismo, y por el mismo motivo. Este
> apartado **continúa** el documento; no lo sustituye.

**Origen:** dirección del propietario, recogida y comprobada en
`docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md` §7.1.
**Registro:** ADR-158 y ADR-159 en `docs/decisions/`.
**Decisiones canónicas:** EV-015 a EV-019 en `docs/evolution/DECISIONS.md`.
**Aprobación:** la fusión de la Pull Request que introduce esta enmienda, por el
propietario.
**Relación con las decisiones canónicas anteriores:** **EV-015 precisa EV-001, EV-016 sustituye EV-002 y acota EV-003, y EV-004 se
mantiene vigente sin enmienda.**
**Estado documental: ENMIENDA PREPARADA.** Entra en vigor con la fusión de la
Pull Request que la introduce, por el propietario, conforme al procedimiento
establecido en este repositorio. **Aprobación documental y retirada técnica son
cosas distintas**: la retirada de los carriles de investigación y auditoría
(ADR-159) sigue sin ejecutar incluso después de fusionar.

### 19.1 Qué queda enmendado

| Apartado de este documento | Qué decía | Qué dice desde esta enmienda |
|---|---|---|
| §2, «Sirius es… la interfaz principal con el ecosistema digital y físico» y «el integrador de resultados» | Sirius es el paso obligatorio y el integrador | Sirius es **una** interfaz —la personal, de ingeniería y del robot—, no el paso obligatorio; integra resultados **cuando se le pide** (EV-015, EV-016) |
| §4, punto 1: «El usuario habla normalmente con Sirius» | El modelo híbrido es el único | El trabajo habitual del propietario se realiza **directamente con las IAs externas**; el modelo híbrido queda como capacidad, no como camino obligatorio (EV-016) |
| §4, punto 6: «Al cerrar, Sirius sintetiza el resultado» | Síntesis obligatoria al cerrar | La síntesis es **a petición** (EV-016) |
| §5, «Sirius mantiene una única memoria canónica» | Una sola memoria canónica | Sigue siendo cierto **de la memoria canónica de Sirius**. Junto a ella existen el diario operativo del motor y el **conocimiento común del trabajo y los proyectos**, que no es memoria canónica (EV-018) |
| §9.3, etapa 0.4 «Delegación supervisada» | Un especialista por tarea, como capacidad futura de Sirius | Se conserva **la delegación de una consulta de ingeniería del propietario**; la delegación de *encargos de trabajo* la hace el motor (EV-019) |

### 19.2 Qué NO queda enmendado

Se dice explícitamente para que no se deduzca de más:

- **§17, la regla de activación**, entera. Ninguna etapa post-0.1 empieza sin
  Definición de Producto aprobada, pruebas de aceptación reproducibles y
  arquitectura técnica aprobada. Esta enmienda **no autoriza implementar nada**.
- **§9, el roadmap**: no cambia el orden, ni el alcance, ni la numeración de
  ninguna versión. El conocimiento común **no recibe etapa**.
- **§12**, HEAD-R1 y el control físico; **§15**, las señales de parada; **§16**,
  la jerarquía documental.
- **EV-004**: sigue vigente sin enmienda, porque el conocimiento común no es la
  memoria canónica de Sirius.

