# Sirius 0.1

Repositorio privado del compañero personal de creación e ingeniería Sirius.

## Estado actual

- Producto Sirius 0.1: aprobado.
- Arquitectura Técnica 0.1 y decisiones ATD-001 a ATD-012: aprobadas.
- V7 dispone de creación, validación y restauración de copias cifradas, incluida su integración en la interfaz.
- La única validación pendiente de V7 es la comprobación manual de Windows Credential Manager en Windows real.
- V8 está iniciada únicamente en su subetapa correctiva y automatizada (V8.1), sin clave API y sin aceptación manual formal. Dentro de V8.1 están fusionados los bloques B2a/B2b (primera configuración y ruta de datos), B3a/B3b/B3c (proyecto: creación, continuidad y ciclo de vida) y B4a a B4f (memoria, decisiones, origen, corrección, sustitución, archivo, eliminación, conflictos y panel observable), siempre con proveedor simulado.
- La ventana de aceptación con proveedor real permanece bloqueada hasta superar las puertas documentadas en `docs/implementation/PLAN.md`.
- Sirius 0.1 todavía no está aceptado ni terminado.
- El alcance no debe ampliarse sin una decisión registrada y aprobada.
- La evolución post-0.1 dispone de Documento Rector v1.0 y decisiones EV-001 a EV-014 aprobadas; permanece inactiva hasta aceptar 0.1. Su estado está en `docs/evolution/STATUS.md`.
- La línea futura de cabeza robótica HEAD-R1 dispone de Documento Rector v1.1 aprobado, pero permanece físicamente inactiva y sin compras autorizadas; su estado está en `docs/robotics/head/STATUS.md`.

La arquitectura modular ya existe y está parcialmente implementada. No debe rediseñarse desde cero salvo que aparezca una contradicción material o un riesgo concreto.

## Fuentes de verdad

Antes de modificar el proyecto, lee:

1. `docs/canonical/STATUS.md`;
2. `docs/implementation/PLAN.md`;
3. `REPOSITORY_STATUS.md`;
4. `AGENTS.md`.

Para la evolución posterior a 0.1, lee además:

5. `docs/evolution/README.md`;
6. `docs/evolution/STATUS.md`.

Para la línea física futura HEAD-R1, lee además:

7. `docs/robotics/head/README.md`;
8. `docs/robotics/head/STATUS.md`.

Los documentos canónicos conservan en algunos nombres la palabra `PROPUESTO` porque son instantáneas históricas anteriores a su aprobación. Su estado vigente está fijado en `docs/canonical/STATUS.md`.

## Preparar o sincronizar el equipo Windows 11

En una copia local existente:

```powershell
git switch main
git pull --ff-only origin main
.\scripts\bootstrap.ps1
```

Para ejecutar Sirius:

```powershell
uv run sirius
```

Para ejecutar todas las comprobaciones locales:

```powershell
.\scripts\check.ps1
```

GitHub Actions ejecuta Ruff, mypy y pytest en Linux (`ubuntu-latest`, workflow `Quality`) para
cada pull request y cada cambio integrado en `main`. La validación equivalente en Windows vive
en `.github/workflows/quality-windows.yml` y es **puntual**: se lanza a mano
(`workflow_dispatch`) antes de un hito o una entrega.
