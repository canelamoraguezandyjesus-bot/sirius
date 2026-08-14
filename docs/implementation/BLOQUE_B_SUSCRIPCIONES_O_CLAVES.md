# Bloque B — ¿Sirven las suscripciones para un runner multimodelo, o hacen falta claves de API?

- **Fecha:** 15 de agosto de 2026
- **Pregunta que responde:** la del §4 de
  [`AGENTES_SUPERFICIE_DE_INVOCACION.md`](AGENTES_SUPERFICIE_DE_INVOCACION.md),
  la única incógnita que bloquea toda la línea multimodelo.
- **Encargo:** el Bloque B del §7 de ese documento. No construye el adaptador
  ni convierte el runbook: solo responde la pregunta, con la comprobación
  delante.

## Nota de arranque (escrita y comprometida ANTES del experimento)

1. **¿Dónde vive la respuesta y dónde puede observarse?** En el propio
   paquete Inspect AI: qué credenciales exigen sus proveedores es un hecho de
   su código y de sus errores de arranque, observable instalándolo en un
   entorno desechable y pidiéndole un modelo sin credencial puesta. No hace
   falta gastar dinero en oír responder a ningún modelo: la pregunta es qué
   PIDE, no qué contesta.

2. **¿Qué NO va a garantizar este informe?** No prueba la cuenta de ChatGPT
   Business del propietario (aquí no hay forma de iniciar su sesión, y no se
   va a intentar); no mide el coste real por ejecución de ningún proveedor
   (eso exige llamadas reales de pago); y no prueba tokens que este entorno
   no posee — no se extrae ni se reutiliza ninguna credencial de la sesión.

3. **Criterio de parada:** si la instalación de Inspect no es posible en este
   entorno (red, proxy), el experimento se declara NO CONCLUYENTE y se deja
   escrito qué máquina lo puede responder — no se sustituye la medición por
   lo que diga la documentación de nadie, que es justo lo que la
   investigación externa dejó sin verificar.

4. **¿Qué haría el fallo imposible en vez de improbable?** Cada afirmación de
   la tabla de resultados lleva al lado el comando ejecutado y su salida
   literal recortada. Una afirmación sin su comando no entra en la tabla.

## Resultado

*(Pendiente: se rellena tras el experimento. Este compromiso existe para que
la nota de arriba quede fechada antes de ver ningún resultado.)*
