# Patrones de fallo conocidos

Reglas del catálogo: un patrón ENTRA cuando ha mordido dos veces; se PODA lo
que lleve un trimestre sin invocarse. Cada patrón lleva origen y fecha. La
revisión es trimestral, de quince minutos, y decide el propietario.

## El observador dentro de lo observado (PR #136 → incidencia #138, 2026-08)

Un proceso que muere no puede informar de su propia muerte. Siete correcciones
seguidas vivieron dentro del run que podía morir, y cada una movió la ventana
de fallo en vez de cerrarla: el diagnóstico podía tumbar el job que observaba;
la «última acción» no existe si un tope de turnos corta antes; el veredicto
provisional no sirve si nadie vive para leerlo; los topes parciales dejan
pasos sin acotar; el corte externo no produce desenlace; el plazo interno no
interrumpe un cuelgue; y el checkout puede morir antes que todo lo demás.

Pregunta que lo caza en el minuto uno: **¿puede el sitio del arreglo OBSERVAR
el fallo que arregla?** Si no, el arreglo tiene que vivir fuera — o aceptar y
dejar escrito lo que no garantiza.

## Pruebas que nacen vacuas (PR #136, cuatro casos, más uno en el diseño del ADR-001, 2026-08)

Formas vistas, todas reales:

1. Enumerar grafías o posiciones en vez de la propiedad: una lista negra de
   nombres de pasos («diagnóstico») se esquiva renombrando el paso; un
   detector de `gh` por prefijos dejaba pasar `sirius_retry gh`, la forma más
   común del repositorio.
2. Afirmar sobre una palabra que también aparece en otros valores del mismo
   objeto («indeterminado»): la aserción pasa con la guarda borrada.
3. Extraer el trozo equivocado antes de afirmar sobre él (un slice entre
   marcadores mal cortado): la aserción pasa en vacío.
4. Puerta global donde hacía falta puerta por unidad: «existe algún ADR en el
   repo» queda abierta para siempre con el primero. La evidencia es POR RAMA.

Antídoto: mutación en las dos direcciones —la versión vieja pasa con la
mutación, la nueva falla— antes de fiarse de ninguna prueba.

## Garantía puesta donde no puede cumplirse (PR #136, familia B, 2026-08)

«Escribe el veredicto como última acción» es inalcanzable si `--max-turns`
corta antes. Un presupuesto de tiempo no es real si un solo paso queda sin
acotar. Un plazo que se comprueba entre reintentos no interrumpe un cuelgue.
Acotar desde fuera corta, pero no produce desenlace.

Pregunta que lo caza: **¿quién tiene que seguir vivo para que esta promesa se
cumpla?**

## El revisor de diffs no ve el enfoque (PR #136, 2026-08)

Cuatro rondas seguidas con un P1 cada una, todos dentro del arreglo de la
ronda anterior: eso es una cadena, no una cola que se agota. El revisor tenía
razón en cada eslabón y aun así el conjunto iba mal, porque solo se le pedía
opinión de parche.

Antídoto: la regla de las dos rondas, y desde la ronda 2 cambiar la pregunta
(«¿está mal el enfoque?»).
