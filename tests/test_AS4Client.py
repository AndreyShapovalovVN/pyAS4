# pyrefly: ignore [missing-import]

import base64
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from pymtom_xop import MtomAttachment, MtomTransport
from zeep import Client
from zeep.exceptions import Fault

from pyAS4.AS4Client import (
    AS4Client,
    AS4Receive,
    AS4Send,
    _norm_cid,
    _open_io,
    attachment,
    get_payload,
)
from pyAS4.header import Header


class TestOpenIO:
    """Tests for _open_io function."""

    def test_open_io_with_string(self):
        """Test conversion of string content to BytesIO."""
        content = "test content"
        result = _open_io(content)
        assert isinstance(result, BytesIO)
        assert result.getvalue() == b"test content"

    def test_open_io_with_bytes(self):
        """Test conversion of bytes content to BytesIO."""
        content = b"test bytes"
        result = _open_io(content, encoding_b64=False)
        assert isinstance(result, BytesIO)
        assert result.getvalue() == b"test bytes"

    def test_open_io_with_bytes_base64_encoded(self):
        """Test conversion of bytes with base64 encoding."""
        content = b"test bytes"
        result = _open_io(content, encoding_b64=True)
        assert isinstance(result, BytesIO)
        expected = base64.b64encode(b"test bytes")
        assert result.getvalue() == expected

    def test_open_io_with_none_raises_error(self):
        """Test that None content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be None"):
            _open_io(None)

    def test_open_io_with_empty_string(self):
        """Test conversion of empty string."""
        result = _open_io("")
        assert isinstance(result, BytesIO)
        assert result.getvalue() == b""


class TestNormCid:
    """Tests for _norm_cid function."""

    def test_norm_cid_with_string(self):
        """Test normalization of string CID."""
        result = _norm_cid("test-cid")
        assert result == "test-cid"

    def test_norm_cid_with_bytes(self):
        """Test normalization of bytes CID."""
        result = _norm_cid(b"test-cid")
        assert result == "test-cid"

    def test_norm_cid_with_angle_brackets(self):
        """Test removal of angle brackets."""
        result = _norm_cid("<test-cid>")
        assert result == "test-cid"

    def test_norm_cid_with_cid_prefix(self):
        """Test removal of 'cid:' prefix."""
        result = _norm_cid("cid:test-cid")
        assert result == "test-cid"

    def test_norm_cid_with_all_prefixes(self):
        """Test removal of all prefixes."""
        result = _norm_cid("<cid:test-cid>")
        assert result == "test-cid"

    def test_norm_cid_case_insensitive_prefix(self):
        """Test case-insensitive CID prefix removal."""
        result = _norm_cid("CID:test-cid")
        assert result == "test-cid"

    def test_norm_cid_with_empty_string(self):
        """Test with empty string."""
        result = _norm_cid("")
        assert result == ""

    def test_norm_cid_with_whitespace(self):
        """Test handling of whitespace."""
        result = _norm_cid("  test-cid  ")
        assert result == "test-cid"


class TestAttachment:
    """Tests for attachment function."""

    def test_attachment_single_file(self):
        """Test attachment creation with single file."""
        files = [
            {
                "content": b"test content",
                "content_type": "text/plain",
                "cid": "test-cid",
            }
        ]
        result = attachment(files)
        assert len(result) == 1
        assert isinstance(result[0], MtomAttachment)
        assert result[0].content_type == "text/plain"

    def test_attachment_multiple_files(self):
        """Test attachment creation with multiple files."""
        files = [
            {
                "content": b"file1",
                "content_type": "text/plain",
                "cid": "cid1",
            },
            {
                "content": b"file2",
                "content_type": "application/xml",
                "cid": "cid2",
            },
        ]
        result = attachment(files)
        assert len(result) == 2
        assert result[0].content_type == "text/plain"
        assert result[1].content_type == "application/xml"

    def test_attachment_with_auto_generated_cid(self):
        """Test attachment with auto-generated CID."""
        files = [
            {
                "content": b"test",
                "content_type": "text/plain",
            }
        ]
        result = attachment(files)
        assert len(result) == 1
        # CID should be auto-generated as a UUID
        cid = result[0].get_cid()
        # get_cid() returns bytes that should be a valid UUID
        assert isinstance(cid, bytes)
        # Should be decodable as a UUID string
        cid_str = cid.decode()
        assert len(cid_str) == 36  # Standard UUID format length

    def test_attachment_appends_to_existing_list(self):
        """Test appending to existing attachments list."""
        existing = [Mock(spec=MtomAttachment)]
        files = [
            {
                "content": b"new",
                "content_type": "text/plain",
                "cid": "new-cid",
            }
        ]
        result = attachment(files, attachments=existing)
        assert len(result) == 2
        assert result[0] == existing[0]

    def test_attachment_string_content(self):
        """Test attachment with string content."""
        files = [
            {
                "content": "string content",
                "content_type": "text/plain",
                "cid": "test-cid",
            }
        ]
        result = attachment(files)
        assert len(result) == 1
        assert result[0].content_type == "text/plain"


class TestGetPayload:
    """Tests for get_payload function."""

    def test_get_payload_single_payload(self):
        """Test extraction of single payload."""
        user_message = {
            "PayloadInfo": [
                {
                    "href": "cid:payload-1",
                    "PartProperties": {"Property": []},
                }
            ]
        }

        mock_payload = Mock()
        mock_payload.payloadId = "cid:payload-1"
        mock_payload.value = b"test payload content"

        body = Mock()
        body.payload = mock_payload

        result = get_payload(user_message, body)
        assert len(result) == 1
        assert result[0]["href"] == "cid:payload-1"
        assert result[0]["content"] == "test payload content"

    def test_get_payload_multiple_payloads(self):
        """Test extraction of multiple payloads."""
        user_message = {
            "PayloadInfo": [
                {
                    "href": "cid:payload-1",
                    "PartProperties": {"Property": []},
                },
                {
                    "href": "cid:payload-2",
                    "PartProperties": {"Property": []},
                },
            ]
        }

        mock_payload1 = Mock()
        mock_payload1.payloadId = "cid:payload-1"
        mock_payload1.value = b"content 1"

        mock_payload2 = Mock()
        mock_payload2.payloadId = "cid:payload-2"
        mock_payload2.value = b"content 2"

        body = Mock()
        body.payload = [mock_payload1, mock_payload2]

        result = get_payload(user_message, body)
        assert len(result) == 2
        assert result[0]["content"] == "content 1"
        assert result[1]["content"] == "content 2"

    def test_get_payload_with_properties(self):
        """Test payload extraction with part properties."""
        user_message = {
            "PayloadInfo": [
                {
                    "href": "cid:payload-1",
                    "PartProperties": {
                        "Property": [
                            {"name": "prop1", "_value_1": "value1"},
                            {"name": "prop2", "_value_1": "value2"},
                        ]
                    },
                }
            ]
        }

        mock_payload = Mock()
        mock_payload.payloadId = "cid:payload-1"
        mock_payload.value = b"content"

        body = Mock()
        body.payload = mock_payload

        result = get_payload(user_message, body)
        assert len(result) == 1
        assert result[0]["prop1"] == "value1"
        assert result[0]["prop2"] == "value2"

    def test_get_payload_missing_content(self):
        """Test that missing content is skipped."""
        user_message = {
            "PayloadInfo": [
                {
                    "href": "cid:missing-payload",
                    "PartProperties": {"Property": []},
                }
            ]
        }

        mock_payload = Mock()
        mock_payload.payloadId = "cid:other-payload"
        mock_payload.value = b"content"

        body = Mock()
        body.payload = mock_payload

        result = get_payload(user_message, body)
        assert len(result) == 0

    def test_get_payload_empty_payload_info(self):
        """Test with empty PayloadInfo."""
        user_message = {"PayloadInfo": []}
        body = Mock()
        body.payload = Mock()

        result = get_payload(user_message, body)
        assert len(result) == 0

    def test_get_payload_no_payload_info(self):
        """Test with missing PayloadInfo key."""
        user_message = {}
        body = Mock()
        body.payload = Mock()

        result = get_payload(user_message, body)
        assert len(result) == 0


class TestAS4Client:
    """Tests for AS4Client base class."""

    def test_as4client_initialization(self):
        """Test AS4Client initialization."""
        wsdl = "http://example.com/service?wsdl"
        transport = Mock(spec=MtomTransport)
        plugins = []
        header = Mock(spec=Header)

        client = AS4Client(wsdl, transport, plugins, header)

        assert client.wsdl == wsdl
        assert client.transport == transport
        assert client.plugins == plugins
        assert client.header == header
        assert client.client is None

    def test_as4client_settings(self):
        """Test AS4Client settings are configured."""
        client = AS4Client(
            "http://example.com/wsdl",
            Mock(spec=MtomTransport),
            [],
            Mock(spec=Header),
        )
        assert client.settings.strict is False
        assert client.settings.xml_huge_tree is True


class TestAS4Send:
    """Tests for AS4Send class."""

    def test_as4send_initialization(self):
        """Test AS4Send initialization."""
        wsdl = "http://example.com/service?wsdl"
        transport = Mock(spec=MtomTransport)
        plugins = []
        header = Mock(spec=Header)

        client = AS4Send(wsdl, transport, plugins, header)

        assert client.wsdl == wsdl
        assert isinstance(client, AS4Client)

    def test_as4send_invalid_transport_raises_error(self):
        """Test that non-MtomTransport raises TypeError."""
        with pytest.raises(TypeError, match="Transport must be an instance of MtomTransport"):
            AS4Send(
                "http://example.com/wsdl",
                Mock(),  # Not MtomTransport
                [],
                Mock(spec=Header),
            )

    @patch("pyAS4.AS4Client.Client")
    @patch("pyAS4.AS4Client.attachment")
    def test_as4send_send_message(self, mock_attachment_func, mock_client_class):
        """Test sending a message."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.element = Mock()

        client = AS4Send(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        # Mock attachment function
        mock_attach = Mock(spec=MtomAttachment)
        mock_attach.get_cid.return_value = "test-cid"
        mock_attach.content_type = "text/plain"
        mock_attachment_func.return_value = [mock_attach]

        # Mock client service
        mock_zeep_client = Mock(spec=Client)
        mock_zeep_client.get_type.return_value = Mock
        mock_zeep_client.service.submitMessage.return_value = "success"
        mock_client_class.return_value = mock_zeep_client

        payload = [{"content": b"test", "content_type": "text/plain"}]
        result = client.send_message(payload)

        assert result == "success"
        transport.add_files.assert_called_once()
        mock_zeep_client.service.submitMessage.assert_called_once()


class TestAS4Receive:
    """Tests for AS4Receive class."""

    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_initialization(self, mock_client_class):
        """Test AS4Receive initialization creates client."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)

        mock_zeep_client = Mock(spec=Client)
        mock_client_class.return_value = mock_zeep_client

        client = AS4Receive(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        assert client.client is not None
        mock_client_class.assert_called_once()

    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_get_pending(self, mock_client_class):
        """Test retrieving pending messages."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"

        mock_zeep_client = Mock(spec=Client)
        mock_response = [Mock(messageId="msg-1"), Mock(messageId="msg-2")]
        mock_zeep_client.service.listPendingMessages.return_value = mock_response
        mock_client_class.return_value = mock_zeep_client

        client = AS4Receive(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        result = client._get_pending()
        assert len(result) == 2
        mock_zeep_client.service.listPendingMessages.assert_called_once_with(
            finalRecipient="party-4"
        )

    @patch("pyAS4.AS4Client.get_dict_header")
    @patch("pyAS4.AS4Client.get_payload")
    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_receive_message(
        self, mock_client_class, mock_get_payload, mock_get_dict_header
    ):
        """Test receiving a message."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"

        mock_zeep_client = Mock(spec=Client)

        # Mock pending messages
        mock_pending_item = Mock()
        mock_pending_item.messageId = "msg-1"
        mock_zeep_client.service.listPendingMessages.return_value = [mock_pending_item]

        # Mock retrieved message
        mock_retrieved = Mock()
        mock_retrieved.header.ebMSHeaderInfo.UserMessage = Mock()
        mock_retrieved.body = Mock()
        mock_zeep_client.service.retrieveMessage.return_value = mock_retrieved

        mock_client_class.return_value = mock_zeep_client
        mock_get_dict_header.return_value = {"key": "value"}
        mock_get_payload.return_value = [{"payload": "data"}]

        client = AS4Receive(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        messages = list(client.receive_message())
        assert len(messages) == 1
        assert messages[0]["messageId"] == "msg-1"
        assert messages[0]["header"] == {"key": "value"}
        assert messages[0]["payload"] == [{"payload": "data"}]

    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_get_pending_soap_fault(self, mock_client_class):
        """Test handling of SOAP Fault during get_pending."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"

        mock_zeep_client = Mock(spec=Client)
        mock_zeep_client.service.listPendingMessages.side_effect = Fault("Test fault")
        mock_client_class.return_value = mock_zeep_client

        client = AS4Receive(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        with pytest.raises(Fault):
            client._get_pending()

    @patch("pyAS4.AS4Client.get_dict_header")
    @patch("pyAS4.AS4Client.get_payload")
    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_receive_message_fault(
        self, mock_client_class, mock_get_payload, mock_get_dict_header
    ):
        """Test handling of SOAP Fault during receive_message."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"

        mock_zeep_client = Mock(spec=Client)

        # Mock pending messages
        mock_pending_item = Mock()
        mock_pending_item.messageId = "msg-1"
        mock_zeep_client.service.listPendingMessages.return_value = [mock_pending_item]

        # Mock fault on retrieval
        mock_zeep_client.service.retrieveMessage.side_effect = Fault("Retrieve fault")

        mock_client_class.return_value = mock_zeep_client

        client = AS4Receive(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        messages = list(client.receive_message())
        assert len(messages) == 0  # Fault is caught, no message yielded

    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_receive_message_no_message_id(self, mock_client_class):
        """Test handling of pending item without messageId."""
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"

        mock_zeep_client = Mock(spec=Client)

        # Create a mock that returns empty string for str()
        mock_pending_item = Mock()
        mock_pending_item.messageId = None

        def mock_str(self):
            return ""

        mock_pending_item.__class__.__str__ = mock_str
        mock_zeep_client.service.listPendingMessages.return_value = [mock_pending_item]

        mock_client_class.return_value = mock_zeep_client

        client = AS4Receive(
            "http://example.com/wsdl",
            transport,
            [],
            header,
        )

        messages = list(client.receive_message())
        assert len(messages) == 0  # Item without messageId is skipped
