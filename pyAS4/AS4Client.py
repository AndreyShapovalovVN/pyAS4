import base64
import logging
import uuid
from io import BytesIO
from typing import Generator

from pymtom_xop import MtomAttachment, MtomTransport
from zeep import Client, Settings, Transport
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin

from pyAS4.header import Header, get_dict_header

_logger = logging.getLogger(__name__)


def _open_io(content: bytes | str | None, encoding_b64: bool = False) -> BytesIO:
    """Повертає `BytesIO` для payload; за потреби кодує вміст у base64."""
    _logger.debug(f"open_io - > {type(content)}")

    if content is None:
        raise ValueError("Content cannot be None")

    if isinstance(content, str):
        return BytesIO(content.encode("utf-8"))

    if encoding_b64:
        return BytesIO(base64.b64encode(content))

    return BytesIO(content)


def _norm_cid(cid: str | bytes) -> str:
    """Нормалізує Content-ID для використання в SOAP payloadId."""
    # CID у payloadId має бути без кутових дужок і без префікса `cid:`.
    cid = cid.decode() if isinstance(cid, bytes) else cid

    if not cid:
        return ""
    cid = cid.strip().strip("<>").strip()
    if cid.lower().startswith("cid:"):
        cid = cid[4:]
    return cid


def attachment(
        files: list[dict[str, str | bytes]], attachments: list[MtomAttachment] | None = None
) -> list[MtomAttachment]:
    """
    Додає вкладення до списку `attachments` на основі переданих файлів.
    Кожен файл у списку `files` повинен бути словником з ключами
    `content`, `content_type` та необов'язковим `cid`.
    :param files:
    :param attachments:
    :return:
    """
    if attachments is None:
        attachments = []
    for file in files:
        attachments.append(
            MtomAttachment(
                file=_open_io(file.get("content")),
                content_type=file.get("content_type"),
                cid=f"<{_norm_cid(file.get('cid', str(uuid.uuid4())))}>",
            )
        )
    return attachments


def get_payload(user_message: dict, body) -> list[dict[str, str]]:
    """
    Перетворює частини повідомлення та payload на список словників для зручності обробки.
    :param user_message:
    :param body:
    :return:
    """

    payloads = body.payload
    if isinstance(payloads, list):
        _logger.info(f"Received {len(payloads)} payloads in part")
    else:
        payloads = [payloads]
        _logger.info("Received a single payload in part, wrapping in lists")

    meta_parts = []
    for part in user_message.get("PayloadInfo", []):
        m = {"href": part.get("href", "").strip('"')}

        for proporty in part.get("PartProperties", {}).get("Property", []):
            m.update({proporty.get("name"): proporty.get("_value_1")})

        for payload in payloads:
            if payload.payloadId == part.get("href", "").strip('"'):
                m.update({"content": payload.value.decode()})
        if not m.get("content"):
            _logger.error(f"Part {part.get('href', '')} has no content, skipping")
            continue
        meta_parts.append(m)
    return meta_parts


class AS4Client:
    """
    Summary of what the class does.

    The AS4Client class is responsible for creating and managing an AS4 client
    instance. It initializes the necessary elements such as WSDL, transport,
    plugins, and header to set up the client properly. This class serves to
    facilitate communication in the context of AS4-based message exchange by
    leveraging the provided configuration data.

    :ivar wsdl: The URL or path to the WSDL describing the service. This is a
        critical component for initializing the client.
    :type wsdl: str
    :ivar transport: The transport object that handles the communication layer for
        the AS4 client.
    :type transport: Transport
    :ivar plugins: A list of plugins, such as HistoryPlugin, used for message
        handling, logging, or other custom processing needs.
    :type plugins: list[HistoryPlugin]
    :ivar header: The AS4-specific header required for processing and transmitting
        requests through the client.
    :type header: Header
    """

    def __init__(
            self,
            wsdl: str,
            transport: Transport,
            plugins: list[HistoryPlugin],
            header: Header,
    ):
        self.wsdl = wsdl
        self.transport = transport
        self.plugins = plugins
        self.header = header

        self.settings = Settings(strict=False, xml_huge_tree=True)
        self.client: Client | None = None


class AS4Send(AS4Client):
    def __init__(
            self,
            wsdl: str,
            transport: Transport,
            plugins: list[HistoryPlugin],
            header: Header,
    ):
        """
        Initializes the client with a specific WSDL, transport, plugin list, and header.
        The transport must be an instance of MtomTransport. This class is a specialized
        client designed for handling SOAP requests with MTOM support by extending the
        base client functionality.

        :param wsdl: WSDL file location as a string for constructing the SOAP client.
        :param transport: Transport layer used for communication, which must be an
            instance of MtomTransport.
        :param plugins: List of `HistoryPlugin` used to capture and manipulate outgoing
            or incoming messages within the client.
        :param header: SOAP request header to include in all outgoing requests.
        :raises TypeError: If the provided `transport` is not an instance of
            `MtomTransport`.
        """
        if not isinstance(transport, MtomTransport):
            raise TypeError("Transport must be an instance of MtomTransport")

        super().__init__(wsdl, transport, plugins, header)

    def send_message(self, payload: list[dict]):
        """
        Sends a message by preparing and attaching payload data to the transport, then
        initializing a SOAP client for further communication.

        This method prepares the provided payload, converts it into attachments, and
        adds these attachments to the transport mechanism. The SOAP client is then
        initialized utilizing the configured WSDL, transport, settings, and plugins.

        :param payload: A list of dictionaries, where each dictionary contains the
            necessary data to be sent as part of the operation.
        :type payload: list[dict]
        """
        attach = attachment(payload)
        self.transport.add_files(files=attach)  # type: ignore

        self.client = Client(
            wsdl=self.wsdl,
            transport=self.transport,
            settings=self.settings,
            plugins=self.plugins,
        )
        PayloadType = self.client.get_type("ns0:LargePayloadType")
        bodyload_obj = None
        payload_objs = []

        for idx, file in enumerate(attach):
            payload_id = f"cid:{_norm_cid(file.get_cid())}"
            obj = PayloadType(
                value=file.get_cid(),
                payloadId=payload_id,
                contentType=file.content_type,
            )
            self.header.payload_append(
                [{"href": payload_id, "mimetype": file.content_type}]
            )
            payload_objs.append(obj)
        try:
            response = self.client.service.submitMessage(
                _soapheaders=[self.header.element],
                body=payload_objs,
                bodyload=bodyload_obj,
            )
        except Fault:
            _logger.exception("SOAP Fault occurred while sending message")
            raise
        except Exception:
            _logger.exception("Error sending message")
            raise
        _logger.info(f"Message sent successfully: {response}")
        return response


class AS4Receive(AS4Client):
    def __init__(
            self,
            wsdl: str,
            transport: Transport,
            plugins: list[HistoryPlugin],
            header: Header,
    ):
        """
        Initializes a new instance of the class.

        This constructor establishes the core components required for the proper
        functioning of the object by accepting necessary parameters including WSDL
        configuration, transport layer, plugins, and header data. These components
        are essential for initializing the client object which enables interaction
        with specified SOAP endpoints.

        :param wsdl: WSDL URL or file path to be used for client configuration.
            Represents the Web Services Description Language definition for the SOAP
            service.
        :type wsdl: str
        :param transport: A transport instance that handles HTTP requests and responses
            for the SOAP client.
        :type transport: Transport
        :param plugins: A list of plugins to be used by the SOAP client for functionalities
            such as logging or request/response alterations.
        :type plugins: list[HistoryPlugin]
        :param header: The header object used to define additional metadata or
            authentication details for SOAP requests.
        :type header: Header
        """
        super().__init__(wsdl, transport, plugins, header)

        self.client = Client(
            wsdl=self.wsdl,
            transport=self.transport,
            settings=self.settings,
            plugins=self.plugins,
        )

    def _get_pending(self) -> list:
        try:
            if self.client is None:
                raise RuntimeError("Client not initialized")
            response = self.client.service.listPendingMessages(
                finalRecipient=self.header.c4_party_id
            )
            _logger.info(f"Received message: {len(response)}")
            return response
        except Fault:
            _logger.exception("SOAP Fault occurred")
            raise
        except Exception:
            _logger.exception("Error receiving message")
            raise

    def receive_message(self) -> Generator[dict, None, None]:
        """
        Retrieve and process messages.

        Iterates over pending items and attempts to retrieve their corresponding messages via a SOAP service.
        Each retrieved message is processed, extracting its header and payload. Log messages are generated for success,
        warnings, and errors during the process.

        :raises Fault: If a SOAP fault occurs while attempting to retrieve a message.
        :raises Exception: If an unexpected error occurs during message retrieval.
        :return: A generator yielding dictionaries containing retrieved message details including message ID,
                header, and payload.
        :rtype: Generator[dict, None, None]
        """

        for item in self._get_pending():
            message_id = getattr(item, "messageId", None) or str(item)
            if not message_id:
                _logger.warning("Message ID not found in pending item")
                continue

            try:
                if self.client is None:
                    raise RuntimeError("Client not initialized")
                retrieved = self.client.service.retrieveMessage(messageID=message_id)
            except Fault:
                _logger.exception(
                    f"SOAP Fault occurred while retrieving message {message_id}"
                )
                continue
            except Exception:
                _logger.exception(f"Error retrieving message {message_id}")
                continue

            message = {"messageId": message_id}
            header_data = get_dict_header(
                retrieved.header.ebMSHeaderInfo.UserMessage
            )
            message["header"] = header_data
            message["payload"] = get_payload(header_data, retrieved.body)

            _logger.debug(f"Retrieved message: {message}")
            yield message
        _logger.info("No more messages to retrieve")
