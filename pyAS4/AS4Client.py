import base64
import logging
import uuid
from email import message
from io import BytesIO

# pyrefly: ignore [missing-import]
from header import Header, get_dict_header
from pymtom_xop import MtomAttachment, MtomTransport
from requests import Session
from zeep import Client, Settings, Transport
from zeep.cache import InMemoryCache
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin

_logger = logging.getLogger(__name__)


def _open_io(content: bytes | str, encoding_b64: bool = False) -> BytesIO:
    """Повертає `BytesIO` для payload; за потреби кодує вміст у base64."""
    _logger.debug(f"open_io - > {type(content)}")
    if content is None:
        raise ValueError("Content cannot be None")

    if isinstance(content, str):
        content: bytes = content.encode("utf-8")

    if encoding_b64:
        content: bytes = base64.b64encode(content)

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
    files: list[dict[str, str | bytes]], attachments: list[MtomAttachment]
) -> list[MtomAttachment]:
    """
    Додає вкладення до списку `attachments` на основі переданих файлів.
    Кожен файл у списку `files` повинен бути словником з ключами
    `content`, `content_type` та необов'язковим `cid`.
    :param files:
    :param attachments:
    :return:
    """
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
    def __init__(
        self,
        wsdl: str,
        transport: Transport,
        settings: Settings,
        plugins: list[HistoryPlugin],
    ):
        self.wsdl = wsdl
        self.transport = transport
        self.settings = settings
        self.plugins = plugins


class AS4Send(AS4Client):
    def __init__(
        self,
        wsdl: str,
        transport: Transport,
        settings: Settings,
        plugins: list[HistoryPlugin],
    ):
        super().__init__(wsdl, transport, settings, plugins)

        self.client = Client(
            wsdl=self.wsdl,
            transport=self.transport,
            settings=self.settings,
            plugins=self.plugins,
        )


class AS4Receive(AS4Client):
    def __init__(
        self,
        wsdl: str,
        transport: Transport,
        settings: Settings,
        plugins: list[HistoryPlugin],
        c4_party_id: str,
    ):
        super().__init__(wsdl, transport, settings, plugins)
        self.c4_party_id = c4_party_id

        self.client = Client(
            wsdl=self.wsdl,
            transport=self.transport,
            settings=self.settings,
            plugins=self.plugins,
        )

    def _get_pending(self) -> list:
        try:
            response = self.client.service.listPendingMessages(finalRecipient=self.c4_party_id)
            _logger.info(f"Received message: {len(response)}")
            return response
        except Fault:
            _logger.exception("SOAP Fault occurred")
            raise
        except Exception:
            _logger.exception("Error receiving message")
            raise

    def get_message(self) -> list[dict]:

        for item in self._get_pending():
            message_id = getattr(item, "messageId", None) or str(item)
            if not message_id:
                _logger.warning("Message ID not found in pending item")
                continue

            try:
                retrieved = self.client.service.retrieveMessage(messageID=message_id)
            except Fault:
                _logger.exception(f"SOAP Fault occurred while retrieving message {message_id}")
                continue
            except Exception:
                _logger.exception(f"Error retrieving message {message_id}")
                continue

            message = {"messageId": message_id}
            message["header"] = get_dict_header(retrieved.header.ebMSHeaderInfo.UserMessage)
            message["payload"] = get_payload(message["header"], retrieved.body)

            _logger.debug(f"Retrieved message: {message}")
            yield message
