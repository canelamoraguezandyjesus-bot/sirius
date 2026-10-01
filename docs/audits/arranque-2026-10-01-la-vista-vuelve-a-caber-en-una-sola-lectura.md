# Nota de arranque — la vista de memoria vuelve a caber en una sola lectura (segunda vez)

Rama `claude/bitacora-y-mina-septiembre`, 01-10-2026, 06:50 UTC. Publicada **antes
del primer commit de arreglo**, como exige ADR-001; las cifras «con el arreglo»
de abajo son predicciones, y el ADR que salga dirá cuánto se desviaron.

## El suceso

Quality falló sobre la PR #664 (cabeza `6fe018a2`), la que trae la bitácora del
ciclo a `main` (ADR-217):

```
FAILED tests/engine/test_memoria.py::test_la_memoria_cabe_en_una_sola_lectura
AssertionError: MEMORIA.md pesa 125587 bytes: por encima de 120000 deja de
leerse entera de una vez y vuelve a ser un corpus (ADR-171, criterio (c))
```

No es culpa de la PR sola: sobre `main` (`a60c059a`) la vista pesa ya **116.854
bytes**, **3.146** de margen. ADR-196 compró el 14-09 «unos 22 ADR»; han entrado
21 (del 197 al 217) y el margen se ha ido en 17 días, como dijo. La diferencia
hasta 125.587 son las **138 filas** de `docs/audits/` que la bitácora y su
familia añaden al índice de documentos.

## Las cuatro preguntas, con la predicción escrita antes de medir

1. **¿De dónde sale el peso?** Medido sobre este árbol antes de tocar nada:
   tabla de decisiones 59.228 bytes (de ellos 23.035 son rutas), lecciones
   23.813 (de ellos 10.992 son rutas de ADR que la tabla de arriba ya enlaza),
   documentos 27.009, de los que `docs/audits/` son 20.446 (138 filas, 82 sin
   fecha declarada).
2. **¿Cuánto ahorran los dos cortes?** El que ADR-196 dejó declarado como
   siguiente —el índice de `docs/audits/` fuera, a una vista generada aparte—
   y el de no repetir en las lecciones una ruta que la tabla ya enlaza.
   Predicción: unos 20.000 + 11.000 = **31.000 bytes**, menos el recuento y el
   puntero que se quedan: la vista queda cerca de **95.000 bytes**.
3. **¿Cuánto compra, en ADR?** Crecimiento medido sobre las últimas ocho
   fusiones de `main` (96.964 → 116.854): **2.486 bytes por fusión**. Tras el
   corte, cada ADR deja de añadir sus filas de `docs/audits/` y el enlace de su
   lección; predicción: **entre 650 y 800 bytes por ADR**, es decir, **entre 30
   y 38 ADR de margen**.
4. **¿Hay techo?** Predicción: no. Solo la fila del índice completo de
   decisiones —que ADR-196 protege y una prueba fija— pesa unos 240 bytes por
   ADR; septiembre produjo 91 ADR. A ese ritmo, el índice completo él solo
   crece unos 22.000 bytes al mes, y ningún corte de los que ADR-171 permite
   (resúmenes más cortos, una sección fuera) lo detiene. Eso es una decisión
   de producto —qué encuentra quien entra— y no se toma aquí.

## Criterio de parada (antes de medir nada)

- **No se sube el límite** (ADR-196 lo dejó prohibido y este arreglo no lo toca).
- **No se borra nada.** Cada fila que salga de `MEMORIA.md` tiene que estar en
  el índice generado, y una prueba lo mide por los dos lados: la fila ausente
  en la vista y presente en el índice.
- El índice generado se escribe con **el mismo comando** y lo vigila **la misma
  guardia** que la vista: una vista aparte que nadie regenera sería la familia
  `pieza-sin-lector` otra vez.
- Si con los dos cortes el margen queda **por debajo de 20 ADR** al crecimiento
  medido tras el cambio, **no se inventa un tercer corte en este ADR**: se
  declara con la cifra y la pregunta estructural pasa a la hoja de decisiones
  del propietario.
- **Tres mutaciones tienen que caer** antes de confirmar: M1 las filas de
  `docs/audits/` de vuelta en la vista; M2 la guardia que deja de mirar el
  índice; M3 el enlace de vuelta en las lecciones.
- Dos rondas de revisión externa con defectos de la misma familia → parar y
  buscar la raíz, no seguir parcheando.
