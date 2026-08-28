# Nota de arranque — ¿Está el motor preparado para recibir órdenes reales?

Fecha: 2026-08-28. ANTES de verificar (ADR-001). Lo pide el propietario,
literal: comprobar «si el motor está preparado, y si tengo todo preparado
para hacer esto» — que las órdenes (implementa / documenta / investiga /
audita) las ejecute EL MOTOR por su ciclo, dictadas desde una sesión que no
tiene red propia, y que la sesión solo despache y guíe.

## Las preguntas (decididas antes de mirar)

1. ¿Puede entrar una orden REAL desde esta sesión? El camino exacto de
   despacho que se usó en B1 (issue #386): qué comando corrió, contra qué
   diario, con qué credencial, y si ESTE entorno puede repetirlo hoy tal
   cual — o qué alternativa existe (un workflow que despache).
2. ¿Cada clase despachable de la TABLA_ACTIVACION llega a un ejecutor que
   existe? Cruce completo tabla × puerta de workflow × manifiesto de
   prompts: programacion, documentacion, auditoria, investigacion. La
   sospecha a refutar o confirmar: `auditoria` despacha pero muere en ROJO
   en el resolver (auditor@1 sin fila en el manifiesto) — se comprueba con
   el resolver real, no leyendo a ojo.
3. ¿El ciclo completo tras el despacho está probado con ejecuciones REALES,
   no con suites? Citar por clase el último ciclo de verdad (incidencia →
   PR → revisión → fusión) con sus números.
4. ¿Qué queda fuera y hay que decirlo sin adornos? (cadencia del motor
   apagada; supervisor a mano; la racha en NO_COMPARABLE hasta la (C);
   cualquier clase sin carril.)

## Criterio de parada

- (a) Si el despacho no puede correr desde esta sesión NI existe vía
  alternativa operativa, el veredicto es NO PREPARADO y el primer arreglo es
  esa entrada — antes que ninguna orden de memoria.
- (b) Si algo exigiera una clave nueva: parar y decirlo
  (CLAVES_QUE_OBLIGAN_A_PARAR); jamás claves de OpenAI/Anthropic.
- (c) Dos rondas de defectos de la misma familia → parar y nombrar la raíz.
- (d) Esta comprobación NO arregla nada por su cuenta: produce el veredicto
  y las órdenes propuestas; los arreglos, si los hay, los ordena el
  propietario (él mandó comprobar, no reconstruir).
