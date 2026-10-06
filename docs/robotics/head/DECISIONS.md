# Decisiones canónicas - Sirius HEAD-R1 (desde el 06-10-2026 manda D-HEAD-14, al final)

**Estado:** APROBADO  
**Fecha de aprobación vigente:** 22 de julio de 2026  
**Documento:** SIRIUS HEAD-R1 v1.1  
**Autoridad final:** usuario responsable del Proyecto Sirius

## D-HEAD-01 - Alcance funcional de R1

HEAD-R1 incluirá:

- cuello con giro horizontal e inclinación vertical;
- ojos conjuntos con movimiento horizontal y vertical;
- párpados conjuntos;
- cejas conjuntas;
- mandíbula articulada;
- voz desde un altavoz interno;
- movimiento creíble de mandíbula durante el habla;
- iluminación azul uniforme en los ojos;
- control determinista desde el ordenador.

Quedan fuera: sonrisa mecánica, cámaras, visión, micrófonos, escucha, movimientos faciales independientes, inclinación lateral, batería, autonomía, cuerpo, brazos y movilidad.

**Sustitución:** la sonrisa independiente incluida en v1.0 se pospone a HEAD-R2.

## D-HEAD-02 - Ojos diseñados a medida

El mecanismo ocular se diseñará desde cero para reproducir la expresividad de Sirius. Se acepta que será la fase técnica más difícil y que exigirá varias iteraciones.

## D-HEAD-03 - Perfil de uso y escala

HEAD-R1 será un objeto de sobremesa para interiores, conectado por cable al ordenador y a la corriente, siempre bajo supervisión.

- altura objetivo: 35 cm;
- altura máxima absoluta: 39 cm;
- parte móvil objetivo: 1,3-1,8 kg, máximo 2,2 kg;
- peso total orientativo: 3,5-5 kg.

## D-HEAD-04 - Separación respecto de Sirius

HEAD-R1 debe construirse y validarse independientemente de Sirius 0.1. Usará control determinista. La integración conversacional será posterior y pasará por una capa de permisos, intenciones de alto nivel y seguridad local.

## D-HEAD-05 - Frontera de activación

Cada fase necesita autorización expresa del usuario. Solo entonces se compran materiales y se inicia trabajo físico. Ninguna fase está activa actualmente.

## D-HEAD-06 - Jerarquía ante conflictos

1. Seguridad.
2. Funcionamiento.
3. Mantenimiento y reparabilidad.
4. Tamaño y estabilidad.
5. Robustez y duración.
6. Parecido con la referencia visual.
7. Coste.
8. Refinamiento estético.

## D-HEAD-07 - Plan por fases

Se aprueba la secuencia F0-F11:

- F0 preparación y aprendizaje CAD;
- F1 primer servo y corte físico;
- F2 maqueta de escala;
- F3 banco eléctrico seguro;
- F4 ojos a medida;
- F5 párpados y cejas;
- F6 mandíbula;
- F7 cuello y pedestal;
- F8 integración con cabeza abierta;
- F9 audio e iluminación;
- F10 carcasa y acabado;
- F11 validación final y cierre de R1.

Cada fase tiene una prueba de salida y no se pasa hasta superarla.

## D-HEAD-08 - Presupuesto y compras

El presupuesto orientativo total es 900-2.500 EUR. Las compras se realizan solo para la fase activa y se verifican en el momento de comprar. La impresora 3D se considera herramienta permanente del proyecto.

## D-HEAD-09 - Plazo y carga de trabajo

El plazo realista es 12-30 meses a tiempo parcial. Solo habrá un frente físico principal abierto a la vez.

## D-HEAD-10 - Seguridad práctica

El corte físico de actuadores existe desde F1 hasta el final. Se trabaja a baja tensión, con fusibles, polaridad verificada, manos fuera de mecanismos energizados y estado seguro al cerrar cada sesión.

## D-HEAD-11 - Método de sesiones

Claude prepara objetivo, pasos, seguridad y diagnóstico; el usuario monta, observa, mide y conserva la autoridad final. Las cifras críticas se verifican con documentación del fabricante o medición real.

## D-HEAD-12 - Grabación dirigida

Cada sesión incluirá una indicación “Qué grabar hoy”. Se registrarán apertura, cambio, prueba, fallo si lo hay y cierre. Antes de publicar se revisará privacidad.

## D-HEAD-13 - Documentación mínima

La burocracia operativa se limita a:

- `DEC-###` decisiones;
- `COMP-###` compras;
- `TEST-###` pruebas;
- `INC-###` incidentes;
- una plantilla de sesión;
- `HEAD_STATUS` de una página.

## Aprobación vigente

El usuario aprobó expresamente el Documento Rector HEAD-R1 v1.1 el 22 de julio de 2026. La aprobación sustituye v1.0, pero no activa ejecución física.

## D-HEAD-14 - HEAD-R1 es el cuerpo de Sirius (6 de octubre de 2026)

**Sustituye a D-HEAD-04.** El 05-10-2026 el propietario decidió que Sirius pasa a ser solo
el software del robot y que primero se hace el cerebro, sin cuerpo (ADR-232; EV-020 y §20
del Rector de evolución). HEAD-R1 deja de construirse aparte de Sirius: es su cuerpo, y su
integración espera a que termine la versión 0.5 del plan del robot.

**Sigue igual:** este conjunto de documentos manda en mecánica, electrónica, firmware,
calibración, límites y seguridad física; el control es determinista; ningún modelo envía
ángulos, pulsos ni secuencias libres; y cada fase necesita autorización expresa, como dice
D-HEAD-05.

**A revisar al reactivarla:** D-HEAD-01 deja fuera cámaras, micrófonos y escucha. Con la
decisión del propietario de que Sirius escuche y mire siempre (EV-022), eso se decide con
la fase que lo toque, no ahora.
