"""El banco de memoria de la 0.2 del robot: 100 casos en español (pieza F de ADR-233).

Sale del paso 1 de la memoria en §4 de ``docs/evolution/PLAN_DEL_ROBOT.md``:
personas, gustos, cosas que cambian, fechas, decir «no lo sé», quién dijo qué y
«olvida eso». Sustituye al banco de 47 casos, que medía memoria de ingeniería.

Cada caso es lo que Sirius sabe antes de la pregunta (``memories``, en el orden
en que se lo dijeron), la pregunta del propietario y lo que tiene que pasar:

- ``expected``: el recuerdo que tiene que encontrar el primero. ``None`` en
  «no lo sé», donde no tiene que encontrar nada, y en «olvida eso».
- ``forget``: en «olvida eso», el recuerdo que el propietario le pide olvidar
  antes de preguntar. Después no puede aparecer.

Muchas preguntas no comparten ni una palabra con su recuerdo: es lo que la
búsqueda por significado tiene que resolver. Las personas, los sitios y las
cifras son inventados: no son los del propietario.

E-R02-04 pasa el banco en su ordenador con el modelo de huellas de verdad y
pide 90 de 100, con todos los de «olvida eso» y «quién dijo qué».
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "FAMILIES",
    "MEMORY_BANK",
    "MemoryCase",
]

PERSONAS = "personas"
GUSTOS = "gustos"
CAMBIAN = "cosas que cambian"
FECHAS = "fechas"
NO_LO_SE = "no lo sé"
QUIEN = "quién dijo qué"
OLVIDA = "olvida eso"

#: Las siete familias del plan, en su orden.
FAMILIES: tuple[str, ...] = (PERSONAS, GUSTOS, CAMBIAN, FECHAS, NO_LO_SE, QUIEN, OLVIDA)


@dataclass(frozen=True, slots=True)
class MemoryCase:
    """Un caso del banco: lo que Sirius sabe, la pregunta y lo que tiene que pasar."""

    id: str
    family: str
    memories: tuple[str, ...]
    question: str
    expected: str | None
    forget: str | None = None

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            msg = f"{self.id}: familia desconocida {self.family!r}"
            raise ValueError(msg)
        if self.expected is not None and self.expected not in self.memories:
            msg = f"{self.id}: lo esperado no está entre lo que Sirius sabe"
            raise ValueError(msg)
        if self.forget is not None and self.forget not in self.memories:
            msg = f"{self.id}: lo que hay que olvidar no está entre lo que Sirius sabe"
            raise ValueError(msg)
        sin_respuesta = self.family in (NO_LO_SE, OLVIDA)
        if sin_respuesta != (self.expected is None):
            msg = f"{self.id}: «{self.family}» no casa con lo esperado"
            raise ValueError(msg)
        if (self.family == OLVIDA) != (self.forget is not None):
            msg = f"{self.id}: solo «olvida eso» tiene algo que olvidar"
            raise ValueError(msg)


def _caso(
    numero: int,
    family: str,
    question: str,
    memories: tuple[str, ...],
    *,
    expected: str | None = None,
    forget: str | None = None,
) -> MemoryCase:
    return MemoryCase(f"MB-{numero:03d}", family, memories, question, expected, forget)


def _con(family: str, numero: int, question: str, expected: str, *otros: str) -> MemoryCase:
    """Un caso cuyo recuerdo esperado se guardó el primero, antes que los otros."""
    return _caso(numero, family, question, (expected, *otros), expected=expected)


def _sin_respuesta(numero: int, question: str, *memories: str) -> MemoryCase:
    return _caso(numero, NO_LO_SE, question, tuple(memories))


def _olvida(numero: int, question: str, forget: str, *otros: str) -> MemoryCase:
    return _caso(numero, OLVIDA, question, (*otros, forget), forget=forget)


def _cambia(numero: int, question: str, antes: str, ahora: str, otro: str) -> MemoryCase:
    """Lo de antes se dijo primero; lo esperado es lo de ahora."""
    return _caso(numero, CAMBIAN, question, (antes, otro, ahora), expected=ahora)


MEMORY_BANK: tuple[MemoryCase, ...] = (
    # --- Personas ---
    _con(
        PERSONAS,
        1,
        "¿A qué se dedica mi hermana?",
        "Su hermana Lucía es enfermera en el hospital.",
        "Tiene una moto vieja en el garaje.",
        "Le gusta el café solo.",
    ),
    _con(
        PERSONAS,
        2,
        "¿Quién es mi amigo de toda la vida?",
        "Su mejor amigo se llama Javi y lo conoce desde el colegio.",
        "El coche está en el taller.",
        "Los domingos juega al pádel.",
    ),
    _con(
        PERSONAS,
        3,
        "¿Con quién salgo?",
        "Marta es su pareja desde hace seis años.",
        "Su madre vive en un pueblo de la sierra.",
        "Tiene dos gatos.",
    ),
    _con(
        PERSONAS,
        4,
        "¿En qué trabajaba mi padre?",
        "Su padre fue mecánico toda su vida.",
        "Su sobrino Leo tiene siete años.",
        "Odia madrugar.",
    ),
    _con(
        PERSONAS,
        5,
        "¿Qué le puedo regalar al crío de mi hermana?",
        "Su sobrino Leo tiene siete años y le encantan los dinosaurios.",
        "Su vecino del quinto toca la batería.",
        "Compró una impresora 3D.",
    ),
    _con(
        PERSONAS,
        6,
        "¿Quién hace ruido en el edificio?",
        "El vecino del quinto, Ramón, toca la batería por las tardes.",
        "Su prima Ana vive en Bilbao.",
        "Le pirra el cocido madrileño.",
    ),
    _con(
        PERSONAS,
        7,
        "¿Cómo se llama la persona que me manda en el trabajo?",
        "Su jefa se llama Carmen y es muy exigente.",
        "Su abuela hacía las mejores croquetas.",
        "Tiene alergia al polen.",
    ),
    _con(
        PERSONAS,
        8,
        "¿Quién cocinaba tan bien en mi familia?",
        "Su abuela Rosa hacía las mejores croquetas del barrio.",
        "Su amigo Javi es fontanero.",
        "Tiene un huerto pequeño.",
    ),
    _con(
        PERSONAS,
        9,
        "¿Dónde vive mi prima?",
        "Su prima Ana vive en Bilbao y trabaja de profesora.",
        "Su cuñado Pedro es policía.",
        "Le gustan las series de miedo.",
    ),
    _con(
        PERSONAS,
        10,
        "¿Quién de la familia lleva uniforme?",
        "Su cuñado Pedro es policía local.",
        "Su sobrino Leo juega al fútbol.",
        "Tiene una guitarra eléctrica.",
    ),
    _con(
        PERSONAS,
        11,
        "¿Quién me echó una mano cuando cambié de casa?",
        "Su compañero de trabajo Luis le ayudó con la mudanza.",
        "Su madre cumple años en mayo.",
        "No soporta el ruido.",
    ),
    _con(
        PERSONAS,
        12,
        "¿Cómo se llama mi madre?",
        "Su madre se llama Pilar y vive en un pueblo de la sierra.",
        "Su hermana Lucía es enfermera.",
        "Tiene un perro llamado Toby.",
    ),
    _con(
        PERSONAS,
        13,
        "¿Quién me ayuda cuando los animales se ponen malos?",
        "Su amiga Sara es veterinaria y cuida de sus gatos.",
        "Su cuñado Pedro es policía.",
        "Le gusta la playa.",
    ),
    _con(
        PERSONAS,
        14,
        "¿Qué familiar tiene un negocio de hostelería?",
        "Su tío Andrés tiene un bar en el centro.",
        "Su abuela Rosa hacía croquetas.",
        "Juega al ajedrez los martes.",
    ),
    _con(
        PERSONAS,
        15,
        "¿Quién se fue a vivir al extranjero?",
        "Su antiguo compañero de piso, Dani, ahora vive en Londres.",
        "Su prima Ana es profesora.",
        "Le encanta el chocolate negro.",
    ),
    # --- Gustos ---
    _con(
        GUSTOS,
        16,
        "¿Qué comida me gusta más?",
        "Le pirra el cocido madrileño.",
        "Tiene una moto vieja en el garaje.",
        "Su hermana es enfermera.",
    ),
    _con(
        GUSTOS,
        17,
        "¿Qué música me gusta?",
        "Su grupo favorito es Extremoduro.",
        "Le gusta el café solo.",
        "Su jefa es muy exigente.",
    ),
    _con(
        GUSTOS,
        18,
        "¿Hay algo que no soporto en la comida?",
        "Odia el cilantro, dice que sabe a jabón.",
        "Le pirra el cocido.",
        "Tiene dos gatos.",
    ),
    _con(
        GUSTOS,
        19,
        "¿Qué tipo de cine me gusta?",
        "Le encantan las películas de ciencia ficción, sobre todo Blade Runner.",
        "No le gusta el fútbol.",
        "Su madre vive en la sierra.",
    ),
    _con(
        GUSTOS,
        20,
        "¿Me gusta el fútbol?",
        "No le gusta nada el fútbol.",
        "Le encanta el baloncesto.",
        "Toca la guitarra.",
    ),
    _con(
        GUSTOS,
        21,
        "¿Cómo tomo el café?",
        "Le gusta el café solo, sin azúcar.",
        "Su bebida favorita es la cerveza tostada.",
        "Tiene un huerto.",
    ),
    _con(
        GUSTOS,
        22,
        "¿Qué hago para desconectar?",
        "Le relaja montar en bici por el monte.",
        "Odia madrugar.",
        "Su amigo Javi es fontanero.",
    ),
    _con(
        GUSTOS,
        23,
        "¿A qué juego en la consola?",
        "Su videojuego preferido es el Zelda.",
        "Le gustan las series de miedo.",
        "Tiene alergia al polen.",
    ),
    _con(
        GUSTOS,
        24,
        "¿Qué series veo?",
        "Le gustan las series de miedo, cuanta más sangre mejor.",
        "No soporta las comedias románticas.",
        "Tiene un coche rojo.",
    ),
    _con(
        GUSTOS,
        25,
        "¿Qué películas me aburren?",
        "No soporta las comedias románticas.",
        "Le gustan las series de miedo.",
        "Su prima vive en Bilbao.",
    ),
    _con(
        GUSTOS,
        26,
        "¿Qué dulce me gusta?",
        "Le encanta el chocolate negro, del amargo.",
        "Odia el cilantro.",
        "Su sobrino tiene siete años.",
    ),
    _con(
        GUSTOS,
        27,
        "¿Cuál es mi color preferido?",
        "Su color favorito es el verde.",
        "Le gusta el café solo.",
        "Juega al pádel.",
    ),
    _con(
        GUSTOS,
        28,
        "¿Dónde me gusta ir de vacaciones?",
        "Prefiere la montaña a la playa.",
        "Le relaja montar en bici.",
        "Su madre vive en la sierra.",
    ),
    _con(
        GUSTOS,
        29,
        "¿Qué afición tengo con las estrellas?",
        "Le apasiona la astronomía y tiene un telescopio.",
        "Su grupo favorito es Extremoduro.",
        "Odia madrugar.",
    ),
    _con(
        GUSTOS,
        30,
        "¿Qué hago en la cocina el fin de semana?",
        "Le encanta preparar arroces los domingos.",
        "Le pirra el cocido.",
        "Tiene un perro.",
    ),
    # --- Cosas que cambian ---
    _cambia(
        31, "¿Dónde vivo ahora?", "Vive en Madrid.", "Se ha mudado a Valencia.", "Tiene dos gatos."
    ),
    _cambia(
        32,
        "¿En qué trabajo ahora?",
        "Trabaja en una tienda de informática.",
        "Ha empezado a trabajar en un taller de motos.",
        "Le gusta el café solo.",
    ),
    _cambia(
        33,
        "¿Qué coche tengo?",
        "Tiene un Seat Ibiza.",
        "Ha vendido el Seat y se ha comprado una furgoneta.",
        "Su hermana es enfermera.",
    ),
    _cambia(
        34,
        "¿Qué mascotas tengo?",
        "Su perro se llama Toby.",
        "Toby murió en verano y ahora tiene dos gatos, Luna y Sol.",
        "Odia madrugar.",
    ),
    _cambia(
        35,
        "¿Qué idioma estudio?",
        "Está aprendiendo inglés.",
        "Ha dejado el inglés y ahora estudia japonés.",
        "Le gusta el baloncesto.",
    ),
    _cambia(
        36,
        "¿Sigo fumando?",
        "Fuma un paquete al día.",
        "Ha dejado de fumar hace tres meses.",
        "Juega al pádel.",
    ),
    _cambia(
        37,
        "¿Qué teléfono uso?",
        "Su móvil es un iPhone.",
        "Se ha pasado a un Android.",
        "Tiene un huerto.",
    ),
    _cambia(
        38,
        "¿Cuándo voy al gimnasio?",
        "Va al gimnasio por las mañanas.",
        "Ahora va al gimnasio por las tardes, al salir del trabajo.",
        "Le gusta la playa.",
    ),
    _cambia(
        39,
        "¿Con quién estoy saliendo?",
        "Su pareja es Laura.",
        "Lo dejó con Laura y ahora sale con Marta.",
        "Tiene una moto.",
    ),
    _cambia(
        40, "¿Cuánto peso?", "Pesa 90 kilos.", "Ha bajado a 82 kilos.", "Le gusta el chocolate."
    ),
    _cambia(
        41,
        "¿De qué equipo soy?",
        "Su equipo es el Atlético.",
        "Ahora dice que es del Betis, por su pareja.",
        "Odia el cilantro.",
    ),
    _cambia(
        42,
        "¿Dónde duermo?",
        "Duerme en el sofá cama del salón.",
        "Ya tiene dormitorio propio desde la mudanza.",
        "Tiene un telescopio.",
    ),
    _cambia(
        43,
        "¿Trabajo desde casa algún día?",
        "Hace teletrabajo los viernes.",
        "Ya no hay teletrabajo: va a la oficina toda la semana.",
        "Su jefa es Carmen.",
    ),
    _cambia(
        44,
        "¿Cómo llevo el pelo?",
        "Lleva el pelo largo.",
        "Se ha rapado el pelo.",
        "Le gustan las series.",
    ),
    # --- Fechas ---
    _con(
        FECHAS,
        45,
        "¿Cuándo es el cumpleaños de mi madre?",
        "Su madre cumple años el 12 de mayo.",
        "Su hermana cumple en octubre.",
        "Tiene dos gatos.",
    ),
    _con(
        FECHAS,
        46,
        "¿Qué día celebramos Marta y yo lo nuestro?",
        "Su aniversario con Marta es el 3 de marzo.",
        "Su madre cumple el 12 de mayo.",
        "Odia madrugar.",
    ),
    _con(
        FECHAS,
        47,
        "¿Cuándo tengo que ir al dentista?",
        "Tiene cita con el dentista el martes 14.",
        "El coche pasa la ITV en noviembre.",
        "Le gusta el café.",
    ),
    _con(
        FECHAS,
        48,
        "¿Cuándo tengo que revisar el coche?",
        "El coche pasa la ITV en noviembre.",
        "Tiene cita con el dentista.",
        "Juega al pádel.",
    ),
    _con(
        FECHAS,
        49,
        "¿Desde cuándo estoy en el taller?",
        "Empezó a trabajar en el taller el 1 de septiembre.",
        "Se mudó en junio.",
        "Le gusta la playa.",
    ),
    _con(
        FECHAS,
        50,
        "¿Cuándo fue la boda de mi prima?",
        "Su prima Ana se casó en agosto de 2024.",
        "Su sobrino nació en 2019.",
        "Tiene un huerto.",
    ),
    _con(
        FECHAS,
        51,
        "¿Qué edad tiene Leo?",
        "Su sobrino Leo nació en abril de 2019.",
        "Su prima se casó en 2024.",
        "Odia el cilantro.",
    ),
    _con(
        FECHAS,
        52,
        "¿Cuándo me voy de vacaciones?",
        "Las vacaciones de este año son la segunda quincena de julio.",
        "Tiene cita con el dentista.",
        "Su color favorito es el verde.",
    ),
    _con(
        FECHAS,
        53,
        "¿Qué día pago el piso?",
        "El alquiler se paga el día 5 de cada mes.",
        "La factura de la luz llega a mediados de mes.",
        "Tiene un gato.",
    ),
    _con(
        FECHAS,
        54,
        "¿Cuándo perdí a mi padre?",
        "Su padre murió en enero de 2020.",
        "Su abuela Rosa murió en 2015.",
        "Juega al ajedrez.",
    ),
    _con(
        FECHAS,
        55,
        "¿Cuándo es el concierto?",
        "El concierto de Extremoduro es el 20 de junio.",
        "Las vacaciones son en julio.",
        "Le gusta el café.",
    ),
    _con(
        FECHAS,
        56,
        "¿Cuándo me toca el chequeo de salud?",
        "La revisión del médico es cada seis meses; la próxima, en diciembre.",
        "El coche pasa la ITV en noviembre.",
        "Tiene un telescopio.",
    ),
    _con(
        FECHAS,
        57,
        "¿Cuándo es mi cumpleaños?",
        "Su cumpleaños es el 29 de febrero, así que lo celebra el 28.",
        "Su madre cumple en mayo.",
        "Le gustan las series.",
    ),
    _con(
        FECHAS,
        58,
        "¿Cuándo regresa mi pareja?",
        "Marta vuelve de su viaje a Roma el domingo.",
        "Su aniversario es en marzo.",
        "Odia madrugar.",
    ),
    # --- No lo sé ---
    _sin_respuesta(
        59,
        "¿Cómo se llama mi dentista?",
        "Su hermana Lucía es enfermera.",
        "Le gusta el café solo.",
        "Tiene dos gatos.",
    ),
    _sin_respuesta(
        60,
        "¿Cuál es mi número de pie?",
        "Su madre cumple el 12 de mayo.",
        "Juega al pádel los domingos.",
        "Tiene una moto vieja.",
    ),
    _sin_respuesta(
        61,
        "¿Qué marca de lavadora tengo?",
        "Le pirra el cocido.",
        "Su jefa se llama Carmen.",
        "Prefiere la montaña a la playa.",
    ),
    _sin_respuesta(
        62,
        "¿A qué colegio fui de pequeño?",
        "Su amigo Javi es fontanero.",
        "Le encanta el chocolate.",
        "Vive en Valencia.",
    ),
    _sin_respuesta(
        63,
        "¿Cuánto me costó el sofá?",
        "Su sobrino Leo tiene siete años.",
        "Odia el cilantro.",
        "Tiene un telescopio.",
    ),
    _sin_respuesta(
        64,
        "¿Cuál es la contraseña del wifi?",
        "Su cuñado Pedro es policía.",
        "Le gustan las series de miedo.",
        "Va al gimnasio por las tardes.",
    ),
    _sin_respuesta(
        65,
        "¿Qué tiempo hará mañana?",
        "Su prima Ana vive en Bilbao.",
        "Su color favorito es el verde.",
        "Tiene un huerto.",
    ),
    _sin_respuesta(
        66,
        "¿Cómo se llama el perro de mi vecina?",
        "Su abuela Rosa hacía croquetas.",
        "Le relaja montar en bici.",
        "Tiene alergia al polen.",
    ),
    _sin_respuesta(
        67,
        "¿En qué hospital nací?",
        "Su tío Andrés tiene un bar.",
        "Le encanta preparar arroces.",
        "Su grupo favorito es Extremoduro.",
    ),
    _sin_respuesta(
        68,
        "¿Qué estudié en la universidad?",
        "Marta es su pareja.",
        "Su padre fue mecánico.",
        "Le apasiona la astronomía.",
    ),
    _sin_respuesta(
        69,
        "¿Cuál es mi grupo sanguíneo?",
        "Su antiguo compañero Dani vive en Londres.",
        "No soporta las comedias románticas.",
        "Tiene un coche rojo.",
    ),
    _sin_respuesta(
        70,
        "¿A qué hora sale mi tren?",
        "Su amiga Sara es veterinaria.",
        "Su bebida favorita es la cerveza tostada.",
        "Se ha rapado el pelo.",
    ),
    _sin_respuesta(
        71,
        "¿Cuántos metros tiene el salón?",
        "Su compañero Luis le ayudó con la mudanza.",
        "Le encanta el baloncesto.",
        "Tiene dos gatos.",
    ),
    _sin_respuesta(
        72,
        "¿Qué me regalaron por mi santo?",
        "Su vecino Ramón toca la batería.",
        "Su videojuego preferido es el Zelda.",
        "Ya tiene dormitorio propio.",
    ),
    # --- Quién dijo qué ---
    _con(
        QUIEN,
        73,
        "¿Quién dijo que cerraba la panadería?",
        "Marta dijo que el sábado cierra la panadería.",
        "Sirius dijo que el sábado iba a hacer sol.",
        "Tiene dos gatos.",
    ),
    _con(
        QUIEN,
        74,
        "¿Quién se ha comprado un barco, según me contaron?",
        "Javi contó que se ha comprado un barco.",
        "Sirius dijo que los barcos dan mareo.",
        "Le gusta el café.",
    ),
    _con(
        QUIEN,
        75,
        "¿Quién dijo que venía a comer?",
        "Su madre dijo que vendrá a comer el domingo.",
        "Lucía dijo que no puede venir el domingo.",
        "Juega al pádel.",
    ),
    _con(
        QUIEN,
        76,
        "¿Qué dije yo de Plutón?",
        "El propietario dijo que Plutón siempre será su planeta favorito.",
        "Sirius dijo que Plutón no es un planeta.",
        "Tiene un telescopio.",
    ),
    _con(
        QUIEN,
        77,
        "¿Quién dijo que la reunión se aplazaba?",
        "Luis dijo que la reunión se aplaza.",
        "Carmen, su jefa, dijo que habrá reunión el lunes a las nueve.",
        "Odia madrugar.",
    ),
    _con(
        QUIEN,
        78,
        "¿Quién me avisó del radar?",
        "Pedro contó que han puesto un radar nuevo en la rotonda.",
        "Sirius dijo que conducir de noche es más tranquilo.",
        "Tiene una furgoneta.",
    ),
    _con(
        QUIEN,
        79,
        "¿Qué dijo la veterinaria de Luna?",
        "Sara, la veterinaria, dijo que Luna tiene que comer pienso especial.",
        "Marta dijo que Luna está gorda.",
        "Su color favorito es el verde.",
    ),
    _con(
        QUIEN,
        80,
        "¿Voy a ir a la cena de empresa?",
        "El propietario dijo que este año no va a ir a la cena de empresa.",
        "Sirius dijo que la cena de empresa sería divertida.",
        "Le encanta el chocolate.",
    ),
    _con(
        QUIEN,
        81,
        "¿Quién viene en Navidad?",
        "Ana dijo que vendrá en Navidad con su marido.",
        "Dani dijo que no vuelve de Londres hasta el verano.",
        "Tiene un huerto.",
    ),
    _con(
        QUIEN,
        82,
        "¿Qué prometió el vecino?",
        "Ramón, el vecino, prometió no tocar la batería después de las diez.",
        "Sirius dijo que la batería es el mejor instrumento.",
        "Ya tiene dormitorio propio.",
    ),
    _con(
        QUIEN,
        83,
        "¿Qué decía mi abuela del cocido?",
        "Su abuela Rosa decía que el cocido se hace a fuego lento.",
        "Sirius dijo que el cocido se come en tres vuelcos.",
        "Le gusta la playa.",
    ),
    _con(
        QUIEN,
        84,
        "¿Quién dijo que cerraba en agosto?",
        "Andrés dijo que el bar cierra en agosto por vacaciones.",
        "Marta dijo que en agosto se van a la sierra.",
        "Juega al ajedrez.",
    ),
    _con(
        QUIEN,
        85,
        "¿Qué quiere ser mi sobrino de mayor?",
        "Leo dijo que de mayor quiere ser paleontólogo.",
        "Sirius dijo que los dinosaurios tenían plumas.",
        "Tiene una guitarra.",
    ),
    _con(
        QUIEN,
        86,
        "¿Quién me debe dinero?",
        "Luis dijo que le debe 20 euros al propietario.",
        "El propietario dijo que le debe una cena a Javi.",
        "Le gustan las series.",
    ),
    # --- Olvida eso ---
    _olvida(
        87,
        "¿Por qué número empieza la contraseña del banco?",
        "Su contraseña del banco empieza por 47.",
        "Le gusta el café solo.",
        "Tiene dos gatos.",
    ),
    _olvida(
        88,
        "¿Qué le dije a Marta de mi suegra?",
        "Le dijo a Marta que no aguanta a su suegra.",
        "Su madre vive en la sierra.",
        "Juega al pádel.",
    ),
    _olvida(
        89,
        "¿Cuánto dinero debo?",
        "Tiene una deuda de 3.000 euros con su hermano.",
        "Le pirra el cocido.",
        "Tiene una moto.",
    ),
    _olvida(
        90,
        "¿Estoy buscando otro trabajo?",
        "Está buscando otro trabajo sin que lo sepa su jefa.",
        "Su jefa se llama Carmen.",
        "Le gusta el verde.",
    ),
    _olvida(
        91,
        "¿Cuál era mi número de móvil antiguo?",
        "Su número de móvil antiguo era el 600 111 222.",
        "Se ha pasado a un Android.",
        "Odia madrugar.",
    ),
    _olvida(
        92,
        "¿Qué me da miedo al volante?",
        "Le confesó a Sirius que le da miedo conducir de noche.",
        "Tiene una furgoneta.",
        "Le encanta el chocolate.",
    ),
    _olvida(
        93,
        "¿Quién rompió la ventana?",
        "Su sobrino rompió la ventana del vecino jugando al fútbol.",
        "Su sobrino Leo tiene siete años.",
        "Tiene un huerto.",
    ),
    _olvida(
        94,
        "¿Cuál es el código de la alarma?",
        "El código de la alarma de casa es 1234.",
        "Vive en Valencia.",
        "Tiene un telescopio.",
    ),
    _olvida(
        95,
        "¿Cuántas veces suspendí el carné?",
        "Suspendió el carné de conducir tres veces.",
        "Tiene un coche rojo.",
        "Le gustan las series de miedo.",
    ),
    _olvida(
        96,
        "¿Cuánto costó el anillo de Marta?",
        "Le regaló a Marta un anillo que costó 800 euros.",
        "Marta es su pareja.",
        "Juega al ajedrez.",
    ),
    _olvida(
        97,
        "¿Con quién me peleé en la boda?",
        "Tuvo una pelea con Javi en la boda de Ana.",
        "Su prima Ana se casó en agosto.",
        "Le gusta la playa.",
    ),
    _olvida(
        98,
        "¿Tomo algo para dormir?",
        "Toma pastillas para dormir desde el verano.",
        "Odia madrugar.",
        "Tiene dos gatos.",
    ),
    _olvida(
        99,
        "¿Dónde vive mi ex?",
        "Su ex vive en la calle del Pez, número 3.",
        "Su prima vive en Bilbao.",
        "Le pirra el cocido.",
    ),
    _olvida(
        100,
        "¿Qué excusa le puse a mi jefa?",
        "Le dijo a su jefa que estaba enfermo y se fue al concierto.",
        "Su jefa se llama Carmen.",
        "Le gusta el café solo.",
    ),
)
