---
name: adr
description: >-
  Crea un ADR nuevo en docs/decisions/ con el número correcto (el máximo
  existente más uno, nunca un hueco histórico), el nombre según el convenio del
  registro y la plantilla ya rellenada. Úsala SIEMPRE que vayas a registrar una
  decisión, en vez de elegir el número leyendo el listado: así nacieron los dos
  ADR-016 que hoy conviven en el registro.
---

# Crear un ADR

**No elijas el número a ojo.** Ejecuta:

```powershell
uv run python scripts/siguiente_adr.py "Título en imperativo de la decisión"
```

Imprime la ruta del archivo creado. Para ver solo qué número tocaría, sin crear
nada:

```powershell
uv run python scripts/siguiente_adr.py --solo-numero
```

## La regla

El número es **el máximo existente más uno**. Los huecos históricos —hoy 017 y
018— **no se reutilizan nunca**: rellenarlos haría que un mismo número apuntara
a decisiones distintas según la fecha del clon (ADR-032).

El nombre queda `ADR-NNN-titulo-normalizado.md`: tres dígitos, minúsculas, sin
diacríticos, guiones por separador. Es el convenio que ya siguen los ADR del
registro —`automatizacion`, `periodica`, `limite`— y lo aplica el guion, no tú.

## Después de crearlo

El guion pone número, título y fecha. El contenido es tuyo, y hay dos secciones
que no son relleno:

- **Criterio de parada**: se escribe ANTES de decidir, no después. Lo que ata no
  es tenerlo, es haberlo publicado (ADR-001, skill `disciplina-evidencia`).
- **Comprobación que la sostiene**: comandos concretos y sus resultados. Sin
  ella, el ADR afirma más de lo que el dato sostiene.

Si el ADR es además la nota de arranque de la rama, dilo en el encabezado y
confírmalo antes del primer cambio de código.

## Qué NO hace esto

- **No es una puerta.** Nada impide crear un ADR a mano con otro número.
- **No coordina ramas paralelas.** Solo ve el árbol local: dos ramas abiertas a
  la vez sobre el mismo `main` pueden obtener ambas el mismo número. Es el modo
  exacto en que nacieron los dos ADR-016, y el guion no lo cierra.
- **No corrige el pasado** ni juzga el contenido del ADR.

Lo que sí cierra el agujero es
`tests/automation/test_registro_de_decisiones.py`, que falla si dos ADR
comparten número. El guion quita fricción; **la prueba es la garantía**. No las
confundas al hablar de esto.
