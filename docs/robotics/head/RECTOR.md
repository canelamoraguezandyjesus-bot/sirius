# Documento Rector — Cabeza Robótica Sirius HEAD-R1

**Identificador:** `SIRIUS-HEAD-RECTOR-R1`  
**Versión:** 1.0  
**Estado:** APROBADO  
**Fecha:** 16 de julio de 2026  
**Autoridad final:** usuario responsable del Proyecto Sirius

> La aprobación de este documento fija la base canónica de HEAD-R1. No autoriza compras, fabricación, montaje eléctrico, firmware, aplicación de control, repositorio independiente ni integración con Sirius 0.1. La ejecución física requerirá una activación expresa y separada por fase.

## 1. Propósito y relación con Sirius

HEAD-R1 será el primer desarrollo físico robótico de Sirius: una cabeza expresiva de sobremesa, claramente robótica, modular, segura, mantenible y documentada.

HEAD-R1 pertenece a la evolución física futura de Sirius. No amplía el alcance aprobado de Sirius 0.1 ni modifica su arquitectura. La cabeza deberá poder diseñarse, construirse, probarse y validarse de forma independiente. La integración conversacional será posterior y separada.

## 2. Jerarquía ante conflictos

1. Seguridad.
2. Funcionamiento.
3. Mantenimiento y reparabilidad.
4. Tamaño y estabilidad.
5. Robustez y durabilidad.
6. Fidelidad a la referencia visual.
7. Coste.
8. Refinamiento estético.

La estética es un requisito central, pero no podrá imponerse sobre seguridad, funcionamiento o mantenimiento. El coste no justificará degradar una función crítica ni pagar por prestaciones innecesarias.

## 3. Alcance de HEAD-R1

### 3.1 Funciones obligatorias

- cuello con giro horizontal;
- cuello con inclinación vertical;
- ojos con movimiento horizontal conjunto;
- ojos con movimiento vertical conjunto;
- párpados conjuntos;
- cejas conjuntas;
- mandíbula articulada;
- sonrisa simétrica independiente de la mandíbula;
- iluminación azul de los ojos;
- reproducción de voz desde la cabeza;
- movimiento básico y convincente de mandíbula durante el habla;
- control determinista desde el ordenador.

### 3.2 Construcción y operación obligatorias

- cabeza, cuello corto y pedestal estable de sobremesa;
- carcasa desmontable;
- esqueleto interno independiente de la carcasa estética;
- módulos accesibles y sustituibles;
- mantenimiento normal sin romper pegamento, cortar cables ni desoldar;
- límites mecánicos y de control;
- referencia y calibración documentadas por eje;
- arranque y parada seguros;
- modo de mantenimiento;
- diagnóstico con actuadores desactivados;
- corte físico de alimentación de actuadores independiente del software;
- estrategia verificable ante bloqueo, sobrecarga o movimiento prolongado;
- trazabilidad entre requisitos, piezas, configuración, pruebas y evidencia.

### 3.3 Fuera de HEAD-R1

- cámaras y visión artificial;
- micrófonos integrados, escucha y cancelación de eco;
- ojos, párpados o cejas independientes;
- guiños;
- inclinación lateral del cuello;
- sincronización fonética avanzada;
- autonomía física;
- batería;
- operación desatendida;
- control directo de motores por el Sirius conversacional;
- cuerpo, torso, brazos, manos o movilidad general.

Las funciones excluidas podrán reservar espacio o interfaces cuando ello no penalice significativamente HEAD-R1, pero no se instalarán por anticipación.

## 4. Perfil de uso

HEAD-R1 será:

- un objeto de sobremesa;
- para interiores;
- alimentado externamente por cable;
- conectado por cable al ordenador;
- operado bajo supervisión;
- inmóvil sobre su base durante el funcionamiento;
- destinado a uso doméstico y de taller;
- transportable únicamente apagado y asegurado;
- no diseñado inicialmente para exposición pública continua.

## 5. Identidad visual y escala

La referencia visual maestra aprobada define una cabeza:

- claramente robótica, no humana realista;
- compacta y redondeada;
- negra y gunmetal;
- formada por placas y detalles mecánicos coherentes;
- con ojos azules, cejas visibles, mandíbula, dientes, cuello corto y pedestal Sirius.

La referencia visual guía la identidad, no constituye un plano ni garantiza fabricabilidad literal.

- altura objetivo del conjunto: **35 cm**;
- altura máxima absoluta: **39 cm**.

Las restantes dimensiones, masas y recorridos son provisionales hasta validación mediante maqueta, componentes reales, CAD y pruebas.

## 6. Arquitectura mecánica

### 6.1 Principio estructural

La arquitectura base será:

- esqueleto interno fijo;
- cara frontal extraíble;
- submódulos desmontables;
- mandíbula unida de forma independiente al esqueleto;
- cubierta posterior de acceso;
- cabeza, cuello y pedestal como módulos separables.

La carcasa será estética y de protección, no el soporte estructural principal. Los actuadores producirán movimiento, pero no serán los únicos cojinetes, ejes o apoyos de carga.

### 6.2 Módulos faciales

- módulo ocular acoplado, preparado para movimiento horizontal y vertical;
- párpados conjuntos sin roce con los ojos;
- puente de cejas con dos piezas visibles y movimiento común;
- mandíbula inferior articulada;
- mecanismo de sonrisa separado de la mandíbula;
- altavoz fijado a estructura o cámara acústica propia;
- iluminación ocular desmontable.

La mandíbula podrá hablar sin sonreír y la sonrisa podrá mantenerse con la boca cerrada.

### 6.3 Cuello y pedestal

La primera generación tendrá dos grados de libertad: giro e inclinación. No incluirá inclinación lateral.

El cuello se probará primero con masa simulada. La estructura deberá soportar la cabeza sin depender únicamente del par de los motores. El pedestal contendrá preferentemente los elementos pesados, calientes o de servicio: control principal, distribución eléctrica, protecciones, conexiones y lastre fijado.

## 7. Alimentación, electrónica y control

La primera cabeza usará baja tensión externa. No incorporará inicialmente red de 230 V ni baterías dentro del pedestal.

La arquitectura separará conceptualmente:

- lógica y comunicaciones;
- actuadores;
- audio e iluminación cuando sea necesario.

Existirán:

- interruptor general;
- corte físico independiente de actuadores;
- fusible principal y protecciones justificadas por ramas;
- cableado adecuado a la corriente;
- conectores identificados y no invertibles por error razonable;
- alivio de tensión y rutas protegidas por el cuello;
- capacidad de conservar diagnóstico con motores desactivados.

El ordenador solicitará acciones de alto nivel. El controlador local aplicará límites, velocidad, aceleración, referencia, posición segura, validación de órdenes y respuesta ante pérdida de comunicación. Ninguna salida libre de un modelo conversacional llegará directamente a los motores.

Antes de energizar un eje deberá existir una referencia de posición válida y un trayecto de inicialización demostrado como seguro. Cada actuador tendrá una ficha con módulo, puerto o ID, orientación, sentido positivo, neutral, límites, alimentación, configuración, referencia, versión y pruebas asociadas.

## 8. Audio e iluminación

La voz deberá parecer proceder de la cabeza. El altavoz estará aislado mecánicamente para no hacer vibrar ojos, dientes, párpados o carcasa.

La mandíbula acompañará el audio de forma sencilla y convincente. No se exige sincronización fonética precisa.

El azul será la identidad luminosa principal. La intensidad podrá variar suavemente por estado; el cambio habitual de color no forma parte de HEAD-R1.

La integración deberá comprobar consumo, temperatura, vibraciones, ruido eléctrico, inteligibilidad y compatibilidad con movimientos simultáneos.

## 9. Materiales, fabricación y CAD

La cabeza deberá parecer metálica sin necesidad de fabricarse íntegramente en metal.

- polímeros y placas ligeras para formas y estructura cuando cumplan;
- metal en ejes, tornillos, rodamientos, casquillos, refuerzos y cargas críticas;
- piezas de desgaste reemplazables;
- uniones desmontables como norma;
- pegamento limitado a elementos no mantenibles o decorativos;
- insertos, tuercas cautivas o tornillos pasantes en desmontajes frecuentes.

No se fabricará la carcasa definitiva antes de validar mecanismos, cableado, masa, temperatura y mantenimiento. Sí se reservará desde el principio una envolvente exterior provisional para impedir que los mecanismos crezcan fuera de la estética aprobada.

Existirá un ensamblaje maestro con sistema de referencias común, volúmenes reservados, interfaces, recorridos y accesos. Los componentes comprados se medirán físicamente antes de cerrar su geometría. Toda modificación manual que permanezca en el montaje deberá reflejarse en la configuración real.

Las herramientas, materiales, tolerancias, servos, rodamientos, conectores e impresora se decidirán mediante pruebas, no por anticipación.

## 10. Método de trabajo

### 10.1 Regla de prueba

Cada mecanismo seguirá, como mínimo:

1. inspección y movimiento manual sin energía;
2. actuador aislado y centrado;
3. unión al mecanismo con recorrido y velocidad reducidos;
4. ciclos repetidos;
5. integración con otros módulos;
6. prueba combinada y de fallo.

Si una pieza no se mueve correctamente a mano, no se utilizará el motor para obligarla. Ante un fallo se modificará una sola variable siempre que sea razonable.

### 10.2 Dirección de sesiones

Cada sesión tendrá:

- identificador;
- fase y objetivo;
- piezas y versiones;
- materiales y herramientas;
- pasos ordenados;
- elementos que no deben hacerse todavía;
- riesgos y condiciones de parada;
- captura audiovisual obligatoria;
- mediciones;
- resultado esperado;
- cierre, estado seguro y siguiente paso.

El usuario ejecutará físicamente, observará, medirá y conservará la autoridad final. El asistente preparará procedimiento, pruebas, diagnóstico, aprendizaje, nomenclatura, archivo, contenido audiovisual y siguiente paso.

### 10.3 Documentación audiovisual

Grabar forma parte de la ingeniería. Cada sesión conservará:

- apertura hablada;
- estado anterior al cambio;
- montaje o fabricación relevante;
- prueba principal desde los ángulos necesarios;
- sonido original cuando sea diagnóstico;
- fallo en su posición exacta;
- corrección;
- resultado final;
- cierre hablado.

Cada archivo tendrá nombre corto y metadatos en un índice. El archivo físico será único aunque tenga varias etiquetas. Se distinguirá material técnico, privado y publicable. Ninguna toma justificará repetir una prueba insegura.

## 11. Compras y presupuesto

La estrategia vigente es incremental:

- comprar solo lo necesario para superar la siguiente prueba;
- exigir calidad suficiente para la función real;
- probar pocas unidades antes de comprar cantidades;
- no montar un laboratorio completo por anticipación;
- no incluir soldador, impresora, cámaras, audio definitivo o servos premium antes de necesitarlos;
- revalidar precios y disponibilidad en el momento de compra.

El ciclo será:

`HIPÓTESIS → CANDIDATO → COMPARADO → AUTORIZADO PARA PRUEBA → COMPRADO → RECIBIDO → VALIDADO → INTEGRADO → SUSTITUIDO/RECHAZADO`.

Ninguna recomendación, enlace o presupuesto histórico equivale a autorización.

## 12. Fases y puertas

1. Gobernanza y requisitos.
2. Maqueta de escala y envolvente.
3. Banco eléctrico seguro.
4. Primer mecanismo expresivo.
5. Esqueleto facial provisional.
6. Iteraciones entre mecanismos y esqueleto.
7. Cuello y pedestal con masa simulada.
8. Cabeza abierta integrada.
9. Audio e iluminación.
10. Carcasa y acabado.
11. Validación de HEAD-R1.

Solo habrá un frente físico principal activo. Cada puerta deberá registrar objetivo, pruebas, evidencia, riesgos, coste real, decisión y siguiente fase autorizada. Retroceder a una fase anterior será obligatorio cuando una prueba invalide una hipótesis.

## 13. Seguridad, mantenimiento y almacenamiento

La seguridad se resolverá primero por diseño, después mediante límites, protecciones, control y procedimiento.

Reglas mínimas:

- manos fuera durante movimientos automáticos;
- velocidad y recorrido reducidos en primeras pruebas;
- corte físico accesible y comprobado;
- desconexión completa para mantenimiento;
- ninguna prueba de desarrollo sin supervisión;
- parada inmediata ante bloqueo, olor, humo, calor rápido, cable caliente, ruido anormal o reinicios repetidos;
- cuello probado con masa falsa y sujeción secundaria;
- pedestal estable y lastre fijado;
- piezas dudosas en cuarentena;
- almacenamiento sin energía, mecanismos relajados, piezas identificadas y estado fotografiado;
- incidentes y casi accidentes registrados y corregidos mediante prueba.

Las herramientas de corte, taladro, lijado, soldadura, pintura e impresión 3D requerirán procedimientos y protección adecuados cuando entren en una fase autorizada.

## 14. Verificación, validación y cierre

Todo requisito deberá estar enlazado con una prueba, configuración, evidencia y estado. No se crearán pruebas sin requisito, riesgo o decisión que las justifique.

HEAD-R1 se considerará terminado únicamente cuando:

- cumpla las funciones obligatorias;
- arranque y se detenga de forma segura;
- repita movimientos y expresiones sin depender de suerte;
- supere pruebas individuales, combinadas, prolongadas y de fallo;
- no presente riesgos críticos abiertos;
- sea estable, mantenible y desmontable;
- el montaje real coincida con CAD, cableado, firmware, parámetros y registros;
- exista documentación suficiente para operar, reparar y reconstruir la versión;
- la identidad visual sea aceptada expresamente por el usuario frente a la referencia maestra;
- se registre una aprobación final `HEAD-CLOSURE-R1`.

Ver moverse la cabeza, publicar un vídeo o completar una demostración aislada no equivale a liberar HEAD-R1.

## 15. Sistema documental y estado operativo

El sistema deberá mantener:

- `RECTOR.md` y el artefacto DOCX aprobado;
- `DECISIONS.md`;
- `STATUS.md`;
- registro de riesgos;
- matriz requisito-prueba;
- lista de piezas y revisiones;
- configuraciones completas `HEAD-BUILD-*`;
- sesiones, pruebas, incidentes y compras;
- índice audiovisual;
- backlog.

Antes de iniciar actividad física deberá existir `HEAD_STATUS.md` con fase activa, última sesión, configuración montada, piezas vigentes, riesgos, compras autorizadas, pruebas pendientes y siguiente paso exacto.

## 16. Frontera de activación vigente

Actualmente solo están autorizadas auditoría, documentación, definición, planificación, aprendizaje y bocetos conceptuales.

Para activar una fase física el usuario deberá aprobar expresamente:

- fase;
- objetivo;
- presupuesto máximo;
- compras permitidas;
- prueba de salida;
- condiciones de parada.

Hasta entonces, HEAD-R1 permanece documentalmente aprobado pero físicamente inactivo.
