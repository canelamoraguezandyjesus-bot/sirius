# Incorporación de Claude al Proyecto Sirius

## Propósito

Este documento sirve como puerta de entrada operativa para Claude, Claude Code o Cowork. No sustituye a las fuentes canónicas ni al estado vivo del repositorio. Su función es indicar qué debe leer, en qué orden, cómo resolver contradicciones y qué debe producir antes de modificar código.

## Regla principal

El repositorio es la fuente técnica viva de Sirius. El estado real de implementación se determina por `main`, `REPOSITORY_STATUS.md`, `docs/implementation/PLAN.md`, las pruebas y GitHub Actions.

La visión, el alcance, las decisiones, la arquitectura y la aceptación se determinan por las fuentes canónicas versionadas en `docs/canonical/` y por `docs/canonical/STATUS.md`.

No se debe usar una conversación, una propuesta o un documento histórico para contradecir una fuente canónica vigente.

## Orden obligatorio de lectura

1. `README.md`
2. `docs/canonical/STATUS.md`
3. `REPOSITORY_STATUS.md`
4. `docs/implementation/PLAN.md`
5. `AGENTS.md`
6. `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` si la tarea afecta agentes, Claude Code, Cowork, Routines, GitHub, permisos, automatización o revisiones automáticas.
7. Todos los documentos de `docs/canonical/` aplicables a la tarea.
8. Los documentos de ejecución específicos de la vertical activa en `docs/implementation/`.
9. Código, migraciones y pruebas relacionados.
10. Historial de Git, incidencias y pull requests vinculados.

Para la línea física futura HEAD-R1, leer además:

- `docs/robotics/head/README.md`
- `docs/robotics/head/STATUS.md`
- el Documento Rector vigente y su plan de desarrollo.

HEAD-R1 no forma parte de Sirius 0.1 y permanece físicamente inactiva salvo aprobación expresa registrada.

## Jerarquía de autoridad

1. Instrucciones vigentes del proyecto.
2. Manual de Visión e Identidad.
3. Definición de Producto Sirius 0.1.
4. Registro de Decisiones.
5. Plan de Pruebas y Trazabilidad.
6. Arquitectura Técnica Sirius 0.1 y decisiones ATD aprobadas.
7. `docs/canonical/STATUS.md` para el estado de aprobación.
8. `docs/implementation/PLAN.md`, `REPOSITORY_STATUS.md`, Git y pruebas para el estado material de implementación.
9. Auditorías, conversaciones y documentos históricos como evidencia secundaria.

Cuando una fuente antigua contiene `PROPUESTO`, prevalece `docs/canonical/STATUS.md`, que registra la aprobación explícita del paquete canónico y de la arquitectura.

## Estado ejecutivo a 20 de julio de 2026

- Producto Sirius 0.1: aprobado.
- Arquitectura Técnica 0.1 y ATD-001 a ATD-012: aprobadas.
- Implementación autorizada por verticales, sin ampliar alcance.
- Sirius 0.1 todavía no está aceptado ni terminado.
- V0 a V6B: infraestructura implementada.
- V7A y V7: implementación automatizada terminada; queda validación manual real de Windows Credential Manager y validaciones de empaquetado/Windows.
- V8: iniciada en corrección documental, corrección funcional y automatización sin clave API.
- B4a a B4f: memoria, decisiones, origen, corrección, sustitución, archivo, eliminación, conflictos y panel observable implementados y cubiertos automáticamente con proveedor simulado.
- B5 y B6 siguen pendientes según el plan vivo.
- La aceptación con proveedor real permanece bloqueada hasta superar las puertas documentadas.

Antes de actuar, confirmar siempre este resumen contra los archivos vivos, porque puede quedar obsoleto.

## Qué es Sirius

Sirius es un compañero personal de creación e ingeniería con identidad estable, memoria propia y portable, criterio, continuidad y autoridad final del usuario.

Sirius 0.1 valida una experiencia de escritorio para Windows 11, centrada en texto, con:

- una conversación principal persistente;
- una identidad reconocible y versionada;
- un proyecto activo mínimo;
- memoria manual trazable y decisiones versionadas;
- proveedor de IA sustituible mediante contratos propios;
- persistencia local, seguridad, copias y recuperación;
- pruebas funcionales, de personalidad, privacidad y extremo a extremo.

## Fuera de alcance de Sirius 0.1

No introducir sin decisión aprobada:

- voz, cámara, sensores o robótica;
- navegación web o investigación autónoma dentro del producto;
- ejecución de comandos, archivos o automatizaciones externas;
- múltiples conversaciones o múltiples proyectos activos;
- RAG, embeddings, bases vectoriales, grafos o multiagente;
- nube propia, sincronización, cuentas o aplicación móvil;
- segundo proveedor productivo visible en la interfaz;
- interfaz galáctica avanzada, avatar o cabeza robótica.

## Arquitectura aprobada

Sirius 0.1 es un monolito modular local de un solo proceso:

- Presentación: PySide6 / Qt Widgets.
- Aplicación: casos de uso, DTO, orquestación y puertos.
- Dominio: reglas puras y entidades propias.
- Infraestructura: SQLite, SQLAlchemy, Alembic, OpenAI, credenciales, copias y logs.
- Dependencias hacia dentro.
- La interfaz no accede directamente a SQLite, OpenAI ni secretos.
- El dominio no importa PySide6, SQLAlchemy, OpenAI ni detalles del sistema.
- SQLite es la fuente canónica local.
- Las operaciones lentas no bloquean la interfaz.
- Las pruebas normales usan proveedores simulados y no realizan llamadas reales de red.

## Reglas de trabajo para Claude

Claude puede:

- leer todo el repositorio;
- modificar código y documentación dentro de una tarea autorizada;
- crear, mover y eliminar archivos del repositorio cuando sea necesario y reversible;
- ejecutar Ruff, mypy, pytest, Alembic y scripts oficiales;
- usar Git local para inspección y preparación de cambios;
- decidir detalles ordinarios de implementación compatibles con producto y arquitectura;
- proponer correcciones documentales o técnicas.

Claude debe detenerse y pedir decisión cuando la tarea implique:

- ampliar Sirius 0.1;
- cambiar una decisión aprobada;
- alterar arquitectura, modelo de datos, privacidad, proveedor o presupuesto de forma material;
- enviar más datos a terceros;
- introducir otro proceso, servidor, agente, base de datos o dependencia estructural;
- ejecutar acciones externas autónomas;
- reducir controles de seguridad;
- hacer una operación irreversible o destructiva;
- no poder resolver una contradicción mediante la jerarquía documental.

## Git, GitHub y seguridad

Por defecto:

- no hacer `push`, `merge`, `rebase`, `reset --hard` ni `clean` sin autorización explícita;
- no modificar secretos ni credenciales;
- no usar una clave API real durante pruebas normales;
- no publicar, desplegar ni activar automatizaciones nuevas sin la puerta correspondiente;
- no dar por terminada una tarea sin evidencia.

Toda entrega debe indicar:

- archivos modificados;
- decisiones técnicas tomadas;
- pruebas ejecutadas y resultado;
- riesgos y limitaciones;
- requisitos y pruebas de aceptación afectados;
- siguiente paso recomendado;
- acciones que no se realizaron.

## Comandos oficiales

En Windows 11:

```powershell
git switch main
git pull --ff-only origin main
.\scripts\bootstrap.ps1
uv run sirius
.\scripts\check.ps1
```

Antes de entregar cambios debe pasar `scripts/check.ps1` o explicarse con precisión por qué no pudo ejecutarse.

## Auditoría inicial obligatoria para una nueva sesión principal

Antes de programar por primera vez, Claude debe realizar una incorporación integral:

1. Inventariar documentación, código, pruebas, migraciones, Git, issues y PR relevantes.
2. Confirmar el estado de aprobación y la vertical activa.
3. Comparar documentación con implementación real.
4. Detectar contradicciones, duplicados, requisitos sin prueba y código fuera de alcance.
5. Ejecutar comprobaciones no destructivas.
6. Crear un informe fechado y referenciado al commit de `main`.
7. No modificar código durante esta primera auditoría, salvo autorización específica.

## Documentos externos y fuentes de proyecto

Antes de añadir documentos externos al repositorio, comparar versión, fecha y estado con lo ya versionado.

No duplicar documentos históricos ni volver a introducir como vigentes archivos sustituidos. Si una fuente externa contiene información que no existe en el repositorio:

1. clasificarla como canónica, operativa, histórica o exploratoria;
2. verificar que no contradice decisiones vigentes;
3. incorporar solo la información faltante en el documento responsable;
4. registrar procedencia, fecha y relación de sustitución;
5. revisar y aprobar el cambio mediante pull request.

Las conversaciones de ChatGPT o Claude son evidencia de trabajo, no autoridad documental por sí solas.

## Resultado esperado de la incorporación

Al terminar la auditoría inicial, Claude debe poder explicar con referencias:

- qué es Sirius y qué no es;
- qué está aprobado;
- qué está implementado;
- qué está pendiente;
- qué vertical está activa;
- qué riesgos y bloqueos existen;
- cuál es el siguiente trabajo correcto;
- qué decisiones puede tomar sin escalar;
- qué acciones requieren aprobación del usuario.

## Mantenimiento

Este documento es un mapa operativo. Debe actualizarse solo cuando cambien reglas de incorporación, jerarquía, permisos o flujo de trabajo. El estado detallado de implementación debe seguir viviendo en `REPOSITORY_STATUS.md` y `docs/implementation/PLAN.md`, no duplicarse aquí de forma exhaustiva.
