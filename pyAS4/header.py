import logging
import uuid

from lxml import etree

_logger = logging.getLogger(__name__)

_NS = {
    "query": "urn:oasis:names:tc:ebxml-regrep:xsd:query:4.0",
    "rs": "urn:oasis:names:tc:ebxml-regrep:xsd:rs:4.0",
    "rim": "urn:oasis:names:tc:ebxml-regrep:xsd:rim:4.0",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "sdg": "http://data.europa.eu/sdg#",  # NOSONAR
    "s12": "http://www.w3.org/2003/05/soap-envelope",
    "eu": "http://eu.domibus.wsplugin/",  # NOSONAR
    "eb3": "http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/",
}


def _nsmap(ns: str, tag: str) -> str:
    return f"{{{_NS[ns]}}}{tag}"


class Header:
    """
    Represents an ebXML-compatible messaging header, allowing for configuration of
    various party identifiers, service/action details, and payload-related data.

    This class is designed to facilitate the construction and management of an
    ebXML AS4-compliant messaging XML, including functionality to dynamically
    append payload information. The primary purpose of this class is to support
    eDelivery-compliant systems by structuring the metadata and delivering
    message-based document exchange.

    :ivar c1_party_id: Identifier for Party 1 involved in the message exchange.
    :ivar c1_party_id_type: The type of the identifier used for Party 1.
    :ivar c2_party_id: Identifier for Party 2 involved in the message exchange.
    :ivar c2_party_id_type: The type of the identifier used for Party 2.
    :ivar c3_party_id: Identifier for Party 3 involved in the message exchange.
    :ivar c3_party_id_type: The type of the identifier used for Party 3.
    :ivar c4_party_id: Identifier for Party 4 involved in the message exchange.
    :ivar c4_party_id_type: The type of the identifier used for Party 4.
    :ivar conversationid: Unique identifier for the conversation thread.
    :ivar service: Service URL to describe the functionality invoked.
    :ivar service_type: Specific type of the service provided.
    :ivar action: Action URL defining the invoked operation.
    :ivar role: Role URL describing the role of the communicating party.
    """

    def __init__(self,
                 c1_party_id: str,
                 c1_party_id_type: str,
                 c2_party_id: str,
                 c2_party_id_type: str,
                 c3_party_id: str,
                 c3_party_id_type: str,
                 c4_party_id: str,
                 c4_party_id_type: str,
                 conversationid: str | None = None,
                 service: str = "http://docs.oasis-open.org/ebxml-msg/as4/200902/service",  # NOSONAR
                 service_type: str = "urn:oasis:names:tc:ebcore:ebrs:ebms:binding:1.0",
                 action: str = "http://docs.oasis-open.org/ebxml-msg/as4/200902/action",  # NOSONAR
                 role: str = "http://sdg.europa.eu/edelivery/gateway"  # NOSONAR
                 ):
        """
        Initializes an instance of the class with required and optional attributes to configure
        a messaging context as per the specified standards. It validates non-None constraints
        for mandatory parameters.

        :param c1_party_id: Identifier for Party 1 involved in the message exchange.
        :param c1_party_id_type: The type of the identifier used for Party 1.
        :param c2_party_id: Identifier for Party 2 involved in the message exchange.
        :param c2_party_id_type: The type of the identifier used for Party 2.
        :param c3_party_id: Identifier for Party 3 involved in the message exchange.
        :param c3_party_id_type: The type of the identifier used for Party 3.
        :param c4_party_id: Identifier for Party 4 involved in the message exchange.
        :param c4_party_id_type: The type of the identifier used for Party 4.
        :param conversationid: (Optional) Unique identifier for the conversation thread.
            Defaults to a random UUID.
        :param service: (Optional) Service URL to describe the functionality invoked.
            Defaults to "http://docs.oasis-open.org/ebxml-msg/as4/200902/service".
        :param service_type: (Optional) Specific type of the service provided.
            Defaults to "urn:oasis:names:tc:ebcore:ebrs:ebms:binding:1.0".
        :param action: (Optional) Action URL defining the invoked operation.
            Defaults to "http://docs.oasis-open.org/ebxml-msg/as4/200902/action".
        :param role: (Optional) Role URL describing the role of the communicating party.
            Defaults to "http://sdg.europa.eu/edelivery/gateway".
        :raises ValueError: If any of the mandatory `c1_party_id`, `c2_party_id`,
            `c3_party_id`, or `c4_party_id` parameters are None.
        """
        if None in (c1_party_id, c2_party_id, c3_party_id, c4_party_id):
            raise ValueError("Parameters must not be None")

        self._xml = etree.Element(_nsmap('eb3', 'Messaging'), nsmap=_NS)

        self.c1_party_id = c1_party_id
        self.c1_party_id_type = c1_party_id_type
        self.c2_party_id = c2_party_id
        self.c2_party_id_type = c2_party_id_type
        self.c3_party_id = c3_party_id
        self.c3_party_id_type = c3_party_id_type
        self.c4_party_id = c4_party_id
        self.c4_party_id_type = c4_party_id_type
        self.service = service
        self.service_type = service_type
        self.action = action
        self.conversationid = conversationid or str(uuid.uuid4())
        self.role = role
        self.pay_load_info = self.__toxml()

    def __toxml(self) -> etree._Element:
        """
        Generates and returns an XML element representing a `PayloadInfo` node with nested
        structure for UserMessage, PartyInfo, CollaborationInfo, and MessageProperties
        based on the provided instance attributes.

        This method uses the lxml.etree library to structure an XML tree,
        populating the sub-elements with instance-specific data.

        :return: An XML element 'PayloadInfo' with the nested structure.
        :rtype: etree._Element
        """

        user_message = etree.SubElement(self._xml, _nsmap('eb3', 'UserMessage'))

        party_info = etree.SubElement(user_message, _nsmap('eb3', 'PartyInfo'))
        froms = etree.SubElement(party_info, _nsmap('eb3', 'From'))
        etree.SubElement(froms, _nsmap('eb3', 'PartyId'),
                         attrib={'type': self.c2_party_id_type},
                         ).text = self.c2_party_id
        etree.SubElement(froms, _nsmap('eb3', 'Role'),
                         ).text = self.role

        to = etree.SubElement(party_info, _nsmap('eb3', 'To'))
        etree.SubElement(to, _nsmap('eb3', 'PartyId'),
                         attrib={'type': self.c3_party_id_type},
                         ).text = self.c3_party_id
        etree.SubElement(to, _nsmap('eb3', 'Role'),
                         ).text = self.role

        collaboration_info = etree.SubElement(user_message, _nsmap('eb3', 'CollaborationInfo'))
        etree.SubElement(collaboration_info, _nsmap('eb3', 'Service'),
                         type=self.service_type,
                         ).text = self.service
        etree.SubElement(collaboration_info, _nsmap('eb3', 'Action'),
                         ).text = self.action
        etree.SubElement(collaboration_info, _nsmap('eb3', 'ConversationId'),
                         ).text = self.conversationid

        message_proportis = etree.SubElement(user_message, _nsmap('eb3', 'MessageProperties'))
        etree.SubElement(message_proportis, _nsmap('eb3', 'Property'),
                         attrib={
                             'name': 'originalSender',
                             'type': self.c1_party_id_type},
                         ).text = self.c1_party_id
        etree.SubElement(message_proportis, _nsmap('eb3', 'Property'),
                         attrib={
                             'name': 'finalRecipient',
                             'type': self.c4_party_id_type},
                         ).text = self.c4_party_id

        self.pay_load_info = etree.SubElement(user_message, _nsmap('eb3', 'PayloadInfo'))

    def payload_append(self, payloads: list[dict[str, str]]) -> None:
        """
        Appends payload information to the internal XML structure.

        This method processes a list of payload dictionaries and appends their
        information into an internal XML structure represented by `self.pay_load_info`.
        Each dictionary in the input list contains details about a single payload, such
        as its `href`, `mimetype`, and optionally its `CompressionType`.

        :param payloads: List of dictionaries, where each dictionary represents a
            payload with at least the keys `href` (str) and `mimetype` (str). The key
            `CompressionType` (str) is optional.
        :return: None
        """
        for payload in payloads:
            pl = etree.SubElement(self.pay_load_info, _nsmap('eb3', 'PartInfo'),
                                  attrib={'href': payload['href']})
            pp = etree.SubElement(pl, _nsmap('eb3', 'PartProperties'), )
            etree.SubElement(pp, _nsmap('eb3', 'Property'),
                             attrib={'name': "MimeType"},
                             ).text = payload['mimetype']
            if payload.get('CompressionType', None):
                etree.SubElement(pp, _nsmap('eb3', 'Property'),
                                 attrib={'name': "CompressionType"},
                                 ).text = payload['CompressionType']

    @property
    def element(self) -> etree._Element:
        """
        Returns the underlying XML element associated with this object.

        This property provides access to the root XML element, enabling direct
        manipulation or query of the XML structure represented by it.

        :return: The root XML element of the object.
        :rtype: etree._Element
        """
        return self._xml

    @property
    def xml(self) -> bytes:
        """
        Provides a property to retrieve the XML representation of an element.

        This property generates and returns the XML content of the associated
        element in a byte string format with pretty-print formatting applied.

        :return: A byte string containing the XML representation of the element
            with pretty-print formatting.
        :rtype: Bytes
        """
        return etree.tostring(self.element, pretty_print=True)


def get_dict_header(source_message) -> dict:
    """
    Перетворює заголовок повідомлення на словник для зручності обробки.
    :param source_message:
    :return:
    """
    headers = {
        "messageId": source_message.MessageInfo.MessageId,
        "timestamp": source_message.MessageInfo.Timestamp,
        "Party": {
            "From": {
                "name": source_message.PartyInfo.From.PartyId._value_1,
                "type": source_message.PartyInfo.From.PartyId.type,
                "role": source_message.PartyInfo.From.Role,
            },
            "To": {
                "name": source_message.PartyInfo.To.PartyId._value_1,
                "type": source_message.PartyInfo.To.PartyId.type,
                "role": source_message.PartyInfo.To.Role,
            },
        },
        "CollaborationInfo": {
            "service": source_message.CollaborationInfo.Service._value_1,
            "serviceType": source_message.CollaborationInfo.Service.type,
            "action": source_message.CollaborationInfo.Action,
            "conversationId": source_message.CollaborationInfo.ConversationId,
        },
    }
    parts = source_message.PayloadInfo.PartInfo
    if isinstance(parts, list):
        _logger.info("Received %d parts in message", len(parts))
    else:
        parts = [parts]
        _logger.info("Received a single part in a message, wrapping in lists")

    meta_parts = []
    for part in parts:
        m = {"href": part.href.strip('"')}

        for proporty in part.PartProperties.Property:
            m.update({proporty.name: proporty._value_1})

        meta_parts.append(m)

    headers["PayloadInfo"] = meta_parts
    return headers
