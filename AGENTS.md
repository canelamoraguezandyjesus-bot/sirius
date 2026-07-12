# Instrucciones para agentes de programación

Este repositorio implementa Sirius 0.1. El producto y la arquitectura están aprobados.

## Antes de modificar código

1. Lee `docs/canonical/STATUS.md`.
2. Lee `docs/implementation/PLAN.md`.
3. Identifica la vertical activa.
4. No añadas funciones fuera de alcance.

## Reglas obligatorias

- No inventes requisitos ni decisiones.
- No cambies arquitectura, modelo de datos, privacidad, costes o alcance sin registrar una propuesta y obtener aprobación.
- Mantén las dependencias hacia dentro: presentación -> aplicación -> dominio; los adaptadores implementan puertos del dominio/aplicación.
- No accedas a SQLite, OpenAI o secretos desde la interfaz.
- No guardes claves en código, SQLite, logs o archivos de texto.
- No uses el proveedor externo en pruebas normales; usa adaptadores simulados.
- Añade o actualiza pruebas con cada cambio.
- Ejecuta `scripts/check.ps1` antes de entregar.
- Haz cambios pequeños, trazables y reversibles.
- Actualiza la documentación cuando cambie el comportamiento aprobado.

## Criterio de parada

Detente y pide decisión cuando una tarea implique:

- ampliar Sirius 0.1;
- cambiar una decisión aprobada;
- enviar más datos a terceros;
- introducir otro proceso, servidor, agente o base de datos;
- ejecutar acciones externas autónomas;
- aumentar el presupuesto o reducir controles de seguridad.
