# Nota de arranque — H-25: el contador declara su precondición (§11.2)

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). El propietario ordenó
rematar lo pendiente; la propia incidencia #376 deja dicho el camino sensato:
«(A o B) ahora y (C) como bloque propio». Aquí se hace (B); (C) —cablear el
desenlace de GitHub de vuelta al almacén— queda como bloque propio que el
propietario ordena aparte.

## Afirmación a corregir (verificada en #376 con el registro real)

La pasada diaria compara el estado del motor con el de la incidencia para
clases cuyo estado el motor NO mantiene todavía (nada escribe el desenlace de
GitHub en su almacén: los seis WorkItems reales tienen exactamente
creado+activado y nada más). El §11.2 dice literal que el contador «no puede
empezar antes de que el motor lleve el estado por sí mismo», así que cada rojo
significa «esta etapa no ha empezado» y se lee «el motor se equivocó». Es la
segunda ronda de la familia de H-24: el verificador mete en DIVERGENCIA todo
lo que no coincide, y cada caso nuevo se tapó con una ventana más (la
siguiente sería la 5).

## Lo que se decide construir (decidido ahora, antes de ver resultados)

La raíz, no la ventana 5: la precondición del §11.2 pasa a ser un HECHO
DECLARADO y legible por máquina, no una inferencia por caso.

1. `projection_verifier.CLASES_CON_ESTADO_PROPIO: frozenset[WorkItemClass]`
   — vacío hoy, porque hoy es la verdad. Una clase entra SOLO desde el bloque
   que cablee el desenlace de GitHub al almacén (la (C) de #376), con su
   evidencia; jamás a mano para «poner verde».
2. `verificar_dia` exige un parámetro NUEVO Y OBLIGATORIO
   `clases_con_estado_propio` (sin valor por defecto: nadie compara sin
   declarar jurisdicción, la misma lección que la tercera guarda del
   supervisor). Si la clase no está en el conjunto: los dos ejes salen
   `NO_COMPARABLE` con motivo que cita el §11.2 y dice que la etapa no ha
   empezado — opción (B): se conserva la traza de la pasada sin acusar a
   nadie, y el día SIGUE sin ser verde (D1 sigue bloqueado, que es la
   verdad).
3. El CLI (`sirius-racha`) pasa la constante real. Los tests existentes de
   mecánica de comparación declaran su clase en el conjunto: la mecánica
   sigue midiéndose entera (cada eje conserva su caso rojo).

## Las preguntas

1. ¿El caso EXACTO de producción (motor ACTIVE, incidencia DELIVERED, clase
   sin estado propio) se ve hoy como DIVERGENCIA y tras el arreglo como
   NO_COMPARABLE citando el §11.2? (test visto FALLAR primero)
2. ¿Una clase DECLARADA en el conjunto sigue produciendo DIVERGENCIA real con
   los mismos datos? (el instrumento conserva los dientes; mutación:
   ignorar el conjunto y tratar todo como con-estado-propio → cae 1;
   tratar todo como sin-estado-propio → cae 2)
3. ¿El CLI pasa la constante real (cableado contado en código, no en
   comentarios — receta de la familia vacua)?
4. ¿`evaluar_racha` y `authority_reversion` tratan las líneas NO_COMPARABLE
   como ya está probado (día no verde; sin reversión)? — se comprueba, no se
   supone.

## Criterio de parada

- (a) Si algún test existente dependiera de que verificar_dia funcione SIN
  declarar jurisdicción de forma que el cambio le cambie el SIGNIFICADO (no
  solo la firma), traerlo aquí y decidir con él delante.
- (b) Si `authority_reversion` reaccionara a NO_COMPARABLE de forma
  inesperada, parar: la salida de emergencia no se toca a la ligera.
- (c) Dos rondas con defectos de la misma familia → parar (ADR-001).
- (d) Nada de claves; `CLAVES_QUE_OBLIGAN_A_PARAR` no aplica.
