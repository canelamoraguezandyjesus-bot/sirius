"""Formato común de los comandos de comprobación de Sirius.

Los dos —la prueba de voz y la conexión con OBS— existen por el mismo motivo:
diagnosticar a distancia, pidiéndole a alguien que copie líneas de consola, no
funciona. Y para que sirvan tienen que salir igual, porque quien los lee no es
quien los escribió: una lista de ``[OK]`` y ``[FALLA]``, y al final un resumen
de una línea por paso, pensado para copiar entero.

Aquí no se comprueba nada. Esto solo es cómo se cuenta.
"""

from __future__ import annotations

from dataclasses import dataclass

SEPARADOR = "=" * 62


@dataclass(frozen=True, slots=True)
class Paso:
    """El resultado de una comprobación, listo para imprimir y para copiar."""

    titulo: str
    correcto: bool
    detalle: str

    def linea(self) -> str:
        return f"[{self.marca()}] {self.titulo}\n        {self.detalle}"

    def marca(self) -> str:
        return "OK  " if self.correcto else "FALLA"


def cabecera(titulo: str) -> None:
    print(f"\n{SEPARADOR}\n{titulo}\n{SEPARADOR}\n")


def resumen(pasos: list[Paso], exito: str) -> int:
    """Imprime el resumen y devuelve el código de salida.

    El primer fallo se nombra explícitamente: es la única línea que hace falta
    leer para saber por dónde seguir, y va al final para que quede a la vista
    aunque la consola haya escupido cosas por el camino.
    """
    print(f"\n{SEPARADOR}\nRESUMEN · copia esto entero y mándamelo\n{SEPARADOR}")
    for paso in pasos:
        print(f"[{paso.marca()}] {paso.titulo} — {paso.detalle}")

    fallos = [paso for paso in pasos if not paso.correcto]
    if not fallos:
        print(f"\n{exito}")
        return 0
    print(f"\nPrimer punto que falla: {fallos[0].titulo}.")
    return 1


def preguntar(pregunta: str) -> bool:
    """Pregunta sí o no, y da por «no» si nadie contesta.

    Sin la salvaguarda, ejecutar esto con la entrada redirigida lanzaría
    ``EOFError`` y se llevaría por delante el resumen, que es lo único que de
    verdad importa de todo el recorrido.
    """
    try:
        respuesta = input(f"{pregunta} (s/n): ").strip().lower()
    except EOFError:
        print("  (sin respuesta: se anota como no)")
        return False
    return respuesta.startswith("s")


def contar_fallo_inesperado(error: Exception) -> int:
    """Un comando de comprobación que revienta no comprueba nada."""
    print(
        f"\n[FALLA] La prueba se ha interrumpido: {type(error).__name__}: {error}\n"
        "Copia esta línea y mándamela: dice exactamente dónde se paró."
    )
    return 1
