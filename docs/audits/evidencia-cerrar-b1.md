# Evidencia — cerrar B1

Fecha: 2026-08-28. Esta rama no cambia comportamiento: registra un cierre. Su
evidencia es la vuelta real en el servidor, y aquí queda atada con sus
comprobaciones.

## La afirmación

B1 pedía: *«que una orden de clase investigacion produzca un resultado»*. Se
afirma: **una orden real la produjo entera, sin intervención manual entre la
orden y la PR del informe.**

## La comprobación, eslabón a eslabón (todo verificable en el servidor)

| eslabón | evidencia |
|---|---|
| la orden entró por la vía normal | `despachar-orden.yml` con `ejecutar=true`, 28-08-2026 ~05:43 UTC |
| el despachador la clasificó y despachó | incidencia **#386**, cuerpo con `Perfil: investigador@1` y `## Objetivo` con la pregunta |
| el ejecutor la atendió solo | run de `investigar-orden.yml` sobre el evento `labeled`; el implementador NO la tomó (su puerta excluye el perfil) |
| investigó con fuentes | `docs/investigaciones/2026-08-28-orden-386-….md` en la rama `sirius/investigacion-386`: 12.150 bytes, **23 fuentes** listadas, cabecera de caducidad completa (leída y verificada contra el parser del guardián) |
| habló el idioma del ciclo | PR **#387** abierta, comentario literal `PR abierta:` en #386, veredicto `READY_FOR_REVIEW` aplicado |
| el ciclo siguió solo | #386 quedó en `sirius:ci-pending` (3 comentarios de la maquinaria) |

## Criterio de parada del cierre

- (a) B1 NO se cerraba con la PR #385 fusionada: el registro exigía la vuelta
  real, mismo criterio que C2 con la #331. Se cerró SOLO al verla.
- (b) El cierre no afirma más de lo visto: la revisión documental y la fusión
  del informe siguen su curso normal y quedan fuera de la afirmación; fusionar
  es del propietario (§8). El examen «lado a lado contra ChatGPT» queda
  declarado como siguiente paso, no como hecho.

## Verificación de la rama

La batería de registros (`-k "bloques or registro"`) en verde: 83 passed. El
cambio es una entrada del registro de bloques y este documento.
