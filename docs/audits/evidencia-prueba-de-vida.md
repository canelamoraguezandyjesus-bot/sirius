# Evidencia — Existir no es poder usarse

Rama `prueba-de-vida`, 27-08-2026. Sin ADR: no hay decisión nueva, es completar
el instrumento con la mitad que le faltaba.

## Afirmación

El preflight comprobaba que un modelo **estuviera en el catálogo**. Eso no
demuestra que se pueda usar, y son dos preguntas distintas:

- puede estar listado y **fuera de la cuota gratuita** de la cuenta;
- puede exigir un campo que la llamada no manda. El vectorizador de NVIDIA pide
  `input_type: query|passage`, y **una llamada compatible con OpenAI estándar no
  lo lleva**. Ese detalle no se ve en ninguna lista: solo llamando.

Quedarse en «figura en la lista» sería la misma familia de defecto que ya mordió
tres veces esta noche: un verde que no significa que funcione.

## Comprobación

Se USA cada modelo configurado, una vez: una frase de generación, una palabra de
vectorización. Decenas de tokens por proveedor.

El código de salida deja de conformarse con la existencia: sale en rojo si algún
proveedor no contesta, si un modelo configurado no existe, **o si existe y no
responde**.

## Criterio de parada (escrito antes)

- Si la prueba de vida gastara más que céntimos, no vale: su razón de ser es
  costar menos que el fallo que evita.
- Si un modelo que responde con error HTTP contara como usable, no vale: sería
  exactamente el verde falso que este paso viene a cerrar.

## Lo que NO hace

No mide calidad. Dice «me contesta», no «contesta bien». El número del 80 % sigue
siendo el paso siguiente.
