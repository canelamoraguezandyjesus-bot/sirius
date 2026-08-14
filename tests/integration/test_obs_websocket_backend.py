"""El adaptador de OBS contra un servidor WebSocket de mentira.

No hay OBS, ni cámaras, ni red externa: se levanta un servidor mínimo en la
propia máquina que habla el protocolo y responde lo que se le diga. Sirve para
comprobar lo que sí se puede comprobar sin el programa real —el saludo, el
enmascarado de los marcos, la autenticación, la traducción de estados y el
comportamiento ante fallos— y **no sustituye** al plan de verificación de
`SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md`.

Lo que estas pruebas NO demuestran: que OBS entienda estos nombres de petición,
que grabe de verdad, ni que el archivo resultante exista.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import socket
import struct
import threading
from collections.abc import Iterator
from typing import Any

import pytest

from sirius.adapters.capture.obs_websocket import ObsWebSocketBackend
from sirius.domain.model_studio import StudioCaptureState
from sirius.ports.capture_backend import CaptureError, CaptureErrorKind, CaptureStatus

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class _FakeObsServer:
    """Servidor WebSocket mínimo que imita a OBS. Un cliente, un hilo."""

    def __init__(
        self,
        *,
        password: str | None = None,
        recording: bool = False,
        paused: bool = False,
        scene: str = "Pantalla",
        reject_requests: bool = False,
        never_identify: bool = False,
        consultas_hasta_confirmar: int = 0,
        eventos_antes_de_responder: int = 0,
    ) -> None:
        self._password = password
        self.recording = recording
        self.paused = paused
        self.scene = scene
        self._reject = reject_requests
        self._never_identify = never_identify
        # OBS acepta la orden y tarda en ejecutarla: durante unas cuantas
        # consultas sigue informando del estado anterior.
        self._consultas_hasta_confirmar = consultas_hasta_confirmar
        # Eventos que se emiten ANTES de contestar a la primera petición. Con
        # más de `_MAXIMUM_HANDSHAKE_MESSAGES` el cliente se rinde y la
        # respuesta queda encolada, que es el desfase de FINDING-001 (#154).
        self._eventos_antes_de_responder = eventos_antes_de_responder
        self._pendientes = 0
        self._request_id = ""
        self.received: list[str] = []

        self._listener = socket.socket()
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self.port: int = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._listener.close()

    # --- Servidor --------------------------------------------------------

    def _serve(self) -> None:
        try:
            connection, _ = self._listener.accept()
        except OSError:
            return
        try:
            self._handshake(connection)
            self._identify(connection)
            while True:
                message = self._receive(connection)
                if message is None:
                    return
                self._handle(connection, message)
        except OSError, ValueError:
            return
        finally:
            with contextlib.suppress(OSError):
                connection.close()

    def _handshake(self, connection: socket.socket) -> None:
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = connection.recv(4096)
            if not chunk:
                raise OSError
            request += chunk
        key = ""
        for line in request.decode("latin-1").split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + _GUID).encode("ascii")).digest()).decode()
        connection.sendall(
            (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            ).encode("ascii")
        )

    def _identify(self, connection: socket.socket) -> None:
        hello: dict[str, Any] = {"op": 0, "d": {"rpcVersion": 1}}
        if self._password is not None:
            hello["d"]["authentication"] = {"salt": "sal", "challenge": "reto"}
        self._send(connection, hello)

        identify = self._receive(connection)
        if identify is None:
            raise OSError
        self.received.append("identify")

        if self._password is not None:
            secret = base64.b64encode(hashlib.sha256((self._password + "sal").encode()).digest())
            expected = base64.b64encode(hashlib.sha256(secret + b"reto").digest()).decode()
            if identify.get("d", {}).get("authentication") != expected:
                raise ValueError("autenticación incorrecta")

        if self._never_identify:
            # Manda eventos para siempre y nunca se identifica.
            for _ in range(20):
                self._send(connection, {"op": 5, "d": {"eventType": "Ruido"}})
            raise ValueError("nunca identifica")
        self._send(connection, {"op": 2, "d": {"negotiatedRpcVersion": 1}})

    def _handle(self, connection: socket.socket, message: dict[str, Any]) -> None:
        data = message.get("d", {})
        request_type = data.get("requestType", "")
        # OBS devuelve el identificador que recibió; el servidor de mentira
        # también, o no podría exhibir un desfase entre petición y respuesta.
        self._request_id = str(data.get("requestId", ""))
        self.received.append(request_type)

        if self._eventos_antes_de_responder > 0:
            eventos, self._eventos_antes_de_responder = self._eventos_antes_de_responder, 0
            for _ in range(eventos):
                self._send(connection, {"op": 5, "d": {"eventType": "Ruido"}})

        if self._reject:
            self._respond(connection, request_type, result=False)
            return

        if request_type == "GetRecordStatus":
            grabando = self.recording
            if self._pendientes > 0:
                self._pendientes -= 1
                grabando = not self.recording  # todavía no ha cambiado de verdad
            self._respond(
                connection,
                request_type,
                response={
                    "outputActive": grabando,
                    "outputPaused": self.paused,
                    "outputDuration": 95_000,
                },
            )
        elif request_type == "GetCurrentProgramScene":
            self._respond(
                connection, request_type, response={"currentProgramSceneName": self.scene}
            )
        elif request_type == "StartRecord":
            self.recording = True
            self._pendientes = self._consultas_hasta_confirmar
            self._respond(connection, request_type)
        elif request_type == "StopRecord":
            self.recording = False
            self._pendientes = self._consultas_hasta_confirmar
            self._respond(connection, request_type, response={"outputPath": "C:/videos/toma-1.mkv"})
        elif request_type == "PauseRecord":
            self.paused = True
            self._respond(connection, request_type)
        elif request_type == "ResumeRecord":
            self.paused = False
            self._respond(connection, request_type)
        elif request_type == "GetSceneList":
            self._respond(
                connection,
                request_type,
                response={
                    "currentProgramSceneName": self.scene,
                    "scenes": [{"sceneName": "Pantalla"}, {"sceneName": "Cámara frontal"}],
                },
            )
        elif request_type == "SetCurrentProgramScene":
            self.scene = data.get("requestData", {}).get("sceneName", self.scene)
            self._respond(connection, request_type)
        else:
            self._respond(connection, request_type, result=False)

    def _respond(
        self,
        connection: socket.socket,
        request_type: str,
        *,
        result: bool = True,
        response: dict[str, Any] | None = None,
    ) -> None:
        self._send(
            connection,
            {
                "op": 7,
                "d": {
                    "requestType": request_type,
                    "requestId": self._request_id,
                    "requestStatus": {"result": result, "code": 100 if result else 204},
                    "responseData": response or {},
                },
            },
        )

    # --- Marcos ----------------------------------------------------------

    @staticmethod
    def _send(connection: socket.socket, payload: dict[str, Any]) -> None:
        # El servidor NO enmascara: solo el cliente lo hace.
        data = json.dumps(payload).encode("utf-8")
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(len(data))
        else:
            header.append(126)
            header.extend(struct.pack("!H", len(data)))
        connection.sendall(bytes(header) + data)

    @staticmethod
    def _receive(connection: socket.socket) -> dict[str, Any] | None:
        def read(count: int) -> bytes:
            buffer = b""
            while len(buffer) < count:
                chunk = connection.recv(count - len(buffer))
                if not chunk:
                    raise OSError
                buffer += chunk
            return buffer

        first, second = read(2)
        if first & 0x0F == 0x8:
            return None
        length = second & 0x7F
        if length == 126:
            (length,) = struct.unpack("!H", read(2))
        elif length == 127:
            (length,) = struct.unpack("!Q", read(8))
        mask = read(4) if second & 0x80 else b""
        payload = read(length) if length else b""
        if mask:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        result: dict[str, Any] = json.loads(payload.decode("utf-8"))
        return result


@pytest.fixture
def server() -> Iterator[_FakeObsServer]:
    instance = _FakeObsServer()
    yield instance
    instance.close()


def _backend(server: _FakeObsServer, password: str = "") -> ObsWebSocketBackend:
    return ObsWebSocketBackend(password=password, port=server.port, timeout_seconds=5.0)


# --- Conexión ------------------------------------------------------------


@pytest.mark.integration
def test_it_connects_and_identifies(server: _FakeObsServer) -> None:
    backend = _backend(server)
    try:
        assert backend.connect() is None
        assert backend.is_connected()
    finally:
        backend.disconnect()


@pytest.mark.integration
def test_connecting_twice_does_not_open_a_second_session(server: _FakeObsServer) -> None:
    backend = _backend(server)
    try:
        backend.connect()
        assert backend.connect() is None
        assert server.received.count("identify") == 1
    finally:
        backend.disconnect()


@pytest.mark.integration
def test_the_password_challenge_is_answered_correctly() -> None:
    server = _FakeObsServer(password="secreta")
    backend = ObsWebSocketBackend(password="secreta", port=server.port)
    try:
        assert backend.connect() is None
        assert backend.is_connected()
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_a_wrong_password_is_reported_as_authentication() -> None:
    server = _FakeObsServer(password="secreta")
    backend = ObsWebSocketBackend(password="otra", port=server.port)
    try:
        error = backend.connect()
        assert isinstance(error, CaptureError)
        assert not backend.is_connected()
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_a_missing_password_when_required_is_rejected() -> None:
    server = _FakeObsServer(password="secreta")
    backend = ObsWebSocketBackend(password="", port=server.port)
    try:
        error = backend.connect()
        assert isinstance(error, CaptureError)
        assert error.kind is CaptureErrorKind.AUTHENTICATION
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_a_closed_program_is_reported_not_raised() -> None:
    """OBS cerrado: el chat escrito no se puede enterar de esto."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    free_port = listener.getsockname()[1]
    listener.close()

    backend = ObsWebSocketBackend(port=free_port, timeout_seconds=1.0)
    error = backend.connect()

    assert isinstance(error, CaptureError)
    assert not backend.is_connected()


@pytest.mark.integration
def test_a_server_that_never_identifies_does_not_hang() -> None:
    server = _FakeObsServer(never_identify=True)
    backend = ObsWebSocketBackend(port=server.port, timeout_seconds=2.0)
    try:
        error = backend.connect()
        assert isinstance(error, CaptureError)
    finally:
        backend.disconnect()
        server.close()


# --- Estado --------------------------------------------------------------


@pytest.mark.integration
def test_a_stopped_program_reports_ready_never_recording(server: _FakeObsServer) -> None:
    backend = _backend(server)
    try:
        backend.connect()
        status = backend.get_status()

        assert isinstance(status, CaptureStatus)
        assert status.state is StudioCaptureState.PREPARADO
        assert not status.state.is_recording_confirmed
    finally:
        backend.disconnect()


@pytest.mark.integration
def test_only_an_active_output_reports_recording() -> None:
    server = _FakeObsServer(recording=True)
    backend = _backend(server)
    try:
        backend.connect()
        status = backend.get_status()

        assert isinstance(status, CaptureStatus)
        assert status.state is StudioCaptureState.GRABANDO
        assert status.recording_seconds == pytest.approx(95.0)
        assert status.active_scene_name == "Pantalla"
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_a_paused_output_is_not_recording() -> None:
    server = _FakeObsServer(recording=True, paused=True)
    backend = _backend(server)
    try:
        backend.connect()
        status = backend.get_status()

        assert isinstance(status, CaptureStatus)
        assert status.state is StudioCaptureState.PAUSADO
        assert not status.state.is_recording_confirmed
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_asking_without_connecting_is_reported(server: _FakeObsServer) -> None:
    backend = _backend(server)

    outcome = backend.get_status()

    assert isinstance(outcome, CaptureError)
    assert outcome.kind is CaptureErrorKind.NOT_CONNECTED


# --- Órdenes -------------------------------------------------------------


@pytest.mark.integration
def test_starting_and_stopping_reaches_the_program(server: _FakeObsServer) -> None:
    backend = _backend(server)
    try:
        backend.connect()

        started = backend.start_recording()
        assert isinstance(started, CaptureStatus)
        assert started.state is StudioCaptureState.GRABANDO

        stopped = backend.stop_recording()
        assert isinstance(stopped, CaptureStatus)
        assert stopped.state is StudioCaptureState.PREPARADO
        # El archivo solo lo dice la respuesta de la parada.
        assert stopped.output_path == "C:/videos/toma-1.mkv"
    finally:
        backend.disconnect()


@pytest.mark.integration
def test_switching_scene_reaches_the_program(server: _FakeObsServer) -> None:
    backend = _backend(server)
    try:
        backend.connect()

        outcome = backend.switch_scene("Cámara frontal")

        assert isinstance(outcome, CaptureStatus)
        assert outcome.active_scene_name == "Cámara frontal"
        assert server.scene == "Cámara frontal"
    finally:
        backend.disconnect()


@pytest.mark.integration
def test_listing_scenes_returns_what_the_program_has(server: _FakeObsServer) -> None:
    backend = _backend(server)
    try:
        backend.connect()

        scenes = backend.list_scenes()

        assert not isinstance(scenes, CaptureError)
        assert [scene.name for scene in scenes] == ["Pantalla", "Cámara frontal"]
        assert scenes[0].is_active
    finally:
        backend.disconnect()


@pytest.mark.integration
def test_a_rejected_pause_is_reported_as_unsupported() -> None:
    """MS-007: o pausa, o se dice que ese formato no puede."""
    server = _FakeObsServer(reject_requests=True)
    backend = _backend(server)
    try:
        backend.connect()

        outcome = backend.pause_recording()

        assert isinstance(outcome, CaptureError)
        assert outcome.kind is CaptureErrorKind.UNSUPPORTED_OPERATION
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_a_rejected_command_never_claims_success() -> None:
    server = _FakeObsServer(reject_requests=True)
    backend = _backend(server)
    try:
        backend.connect()

        outcome = backend.start_recording()

        assert isinstance(outcome, CaptureError)
        assert outcome.kind is CaptureErrorKind.REJECTED
    finally:
        backend.disconnect()
        server.close()


@pytest.mark.integration
def test_disconnecting_does_not_stop_the_recording() -> None:
    """Cerrar Sirius no puede llevarse por delante una toma en curso."""
    server = _FakeObsServer(recording=True)
    backend = _backend(server)
    try:
        backend.connect()
        backend.disconnect()

        assert server.recording
        assert "StopRecord" not in server.received
    finally:
        server.close()


@pytest.mark.integration
def test_the_password_never_travels_in_an_error_message() -> None:
    server = _FakeObsServer(password="contraseña-secretísima")
    backend = ObsWebSocketBackend(password="equivocada", port=server.port)
    try:
        error = backend.connect()

        assert isinstance(error, CaptureError)
        assert "equivocada" not in error.message
        assert "secretísima" not in error.message
    finally:
        backend.disconnect()
        server.close()


# --- OBS acepta la orden y la ejecuta después ---------------------------


def test_a_recording_that_takes_a_moment_to_start_is_still_confirmed() -> None:
    """El fallo visto contra OBS real: «aceptó la orden pero dice CAPTURA LISTA».

    Entre aceptar y grabar, OBS inicializa el codificador y abre el archivo.
    Preguntar en ese hueco devuelve el estado anterior, y creérselo hace que
    Sirius dé por fallida una grabación que sí está en marcha.
    """
    server = _FakeObsServer(consultas_hasta_confirmar=3)
    backend = ObsWebSocketBackend(port=server.port, settle_timeout_seconds=5.0)
    backend.connect()

    resultado = backend.start_recording()

    assert isinstance(resultado, CaptureStatus)
    assert resultado.state is StudioCaptureState.GRABANDO
    backend.disconnect()
    server.close()


def test_a_stop_that_takes_a_moment_is_also_waited_for() -> None:
    """Y el archivo resultante no se pierde por el camino."""
    server = _FakeObsServer(recording=True, consultas_hasta_confirmar=3)
    backend = ObsWebSocketBackend(port=server.port, settle_timeout_seconds=5.0)
    backend.connect()

    resultado = backend.stop_recording()

    assert isinstance(resultado, CaptureStatus)
    assert resultado.state is StudioCaptureState.PREPARADO
    assert resultado.output_path == "C:/videos/toma-1.mkv"
    backend.disconnect()
    server.close()


def test_when_obs_never_confirms_nothing_is_invented() -> None:
    """Agotada la espera se dice lo que OBS diga, no lo que convendría.

    Es la mitad importante de la regla: esperar no puede convertirse en dar
    por buena una grabación que nunca arrancó.
    """
    server = _FakeObsServer(consultas_hasta_confirmar=10_000)
    backend = ObsWebSocketBackend(port=server.port, settle_timeout_seconds=0.3)
    backend.connect()

    resultado = backend.start_recording()

    assert isinstance(resultado, CaptureStatus)
    assert resultado.state is StudioCaptureState.PREPARADO
    backend.disconnect()
    server.close()


def test_una_peticion_que_se_rinde_no_desplaza_las_siguientes() -> None:
    """Una respuesta atrasada no puede pasar por la respuesta de otra petición.

    Es FINDING-001 de la auditoría #154. El adaptador pedía todo con el mismo
    identificador y aceptaba la primera respuesta que llegara, así que en cuanto
    una petición se rendía —por plazo agotado o, como aquí, porque OBS emite más
    eventos de los que se leen— su respuesta quedaba en el socket y la siguiente
    petición la tomaba por suya. Las respuestas iban desplazadas desde entonces,
    y como la de `StartRecord` no lleva `outputActive`, el estado se reconstruía
    como PREPARADO con OBS grabando: exactamente lo que ADR-009 declara
    imposible y lo que dejaba el botón de parar inerte.

    Sin reloj de por medio: el desfase se provoca con eventos, no con esperas.
    """
    server = _FakeObsServer(eventos_antes_de_responder=9)
    backend = ObsWebSocketBackend(port=server.port, settle_timeout_seconds=0.3)
    backend.connect()

    # Se rinde: nueve eventos agotan el presupuesto de mensajes de la petición.
    rendida = backend.start_recording()
    assert isinstance(rendida, CaptureError)
    assert rendida.kind is CaptureErrorKind.TIMEOUT

    # El servidor sí ejecutó la orden: está grabando de verdad.
    assert server.recording is True

    # La consulta siguiente debe decir la verdad, no heredar la respuesta vieja.
    resultado = backend.get_status()

    assert isinstance(resultado, CaptureStatus)
    assert resultado.state is StudioCaptureState.GRABANDO
    backend.disconnect()
    server.close()
