# Nota de arranque de la mina v2 (escrita ANTES de ver resultados, ADR-001)

Fecha: 2026-09-03, 18:50 UTC. Autor: el propietario (sesión Claude Code).
Materia prima: los siete encargos de la ola de criticidad (M18a → M21b),
sus incidencias y PR, el diario del motor, los runs de Actions y la
bitácora de fallos del ciclo.

## Cuatro preguntas y su predicción

1. **Rondas y goteo.** ¿Cuántas rondas de revisión por encargo, y qué
   fracción de los hallazgos de rondas N>1 es goteo (fichero y líneas
   citadas sin cambio desde el head de la ronda 1)? Predicción: goteo
   ≥ 30 % en los hallazgos de CLAUDE y < 10 % en los de CODEX, como en la
   mina de agosto (30,6 % frente a 2,2 %).
2. **Familias.** ¿Qué familia de defecto se repite en más encargos
   distintos? Predicción: «estado de la interfaz frente a transiciones
   asíncronas» (M21b, cuatro rondas) y «adaptador calcado sin sus guardas»
   (M21a: ruta relativa, sin `think: false`), y en tercer lugar «suelo de
   prueba que no puede fallar» (M20).
3. **Muertes del corrector.** ¿Cuánto costó cada ejecución del corrector
   que terminó sin commit, y qué condición las predice? Predicción: las
   muertes ocurren solo en rondas con dos o más hallazgos que exigen
   pruebas de interfaz (Qt); cero muertes en rondas sin interfaz.
4. **Guardianes mecánicos.** ¿Qué comprobación simple (grep o prueba
   automática) habría cazado más defectos reales de esta ola con menos
   falsos positivos? Predicción: (a) «constante `_MINIMO_*` a 0 o aserción
   `>= 0`», (b) «adaptador Ollama sin `think: false` o con ruta relativa a
   `base_url`», (c) «orden que dice 'calcado de X' sin enumerar las guardas
   de X».

## Criterio de parada (escrito antes de decidir)

- Toda cifra del informe cita el comentario, commit o run concreto del que
  sale; una cifra sin cita se descarta, no se estima.
- Toda afirmación de goteo o de muerte del corrector la verifican dos
  agentes independientes con instrucción de refutarla; si uno la refuta con
  evidencia, se elimina del cómputo y se registra como refutada.
- Si los datos brutos no cubren un encargo (comentarios truncados, runs
  fuera de la ventana), el informe declara el hueco; no se rellena.
- Las propuestas se ordenan por (defectos reales cazados − falsos positivos
  estimados) sobre ESTA muestra; ninguna se implementa en la mina.
- Si la extracción de dos agentes sobre la misma incidencia difiere en el
  número de rondas o de hallazgos, se para y se resuelve a mano antes de
  agregar.
