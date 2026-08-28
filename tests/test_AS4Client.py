# pyrefly: ignore [missing-import]

import base64
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from pymtom_xop import MtomAttachment, MtomTransport
from zeep import Client
from zeep.exceptions import Fault

from pyAS4.AS4Client import AS4Client, AS4Receive, AS4Send, _norm_cid, _open_io, attachment, get_payload
from pyAS4.header import Header


class TestOpenIO:
    def test_open_io_with_string(self):
        result = _open_io("test content")
        assert isinstance(result, BytesIO)
        assert result.getvalue() == b"test content"

    def test_open_io_with_bytes(self):
        result = _open_io(b"test bytes")
        assert isinstance(result, BytesIO)
        assert result.getvalue() == b"test bytes"

    def test_open_io_with_bytes_base64_encoded(self):
        result = _open_io(b"test bytes", encoding_b64=True)
        assert isinstance(result, BytesIO)
        assert result.getvalue() == base64.b64encode(b"test bytes")

    def test_open_io_with_none_raises_error(self):
        with pytest.raises(ValueError, match="Content cannot be None"):
            _open_io(None)


class TestNormCid:
    def test_norm_cid_with_string(self):
        assert _norm_cid("test-cid") == "test-cid"

    def test_norm_cid_with_bytes(self):
        assert _norm_cid(b"test-cid") == "test-cid"

    def test_norm_cid_with_angle_brackets(self):
        assert _norm_cid("<test-cid>") == "test-cid"

    def test_norm_cid_with_cid_prefix(self):
        assert _norm_cid("cid:test-cid") == "test-cid"

    def test_norm_cid_with_all_prefixes(self):
        assert _norm_cid("<cid:test-cid>") == "test-cid"


class TestAttachment:
    def test_attachment_single_file(self):
        files: list[dict[str, str | bytes]] = [
            {"content": b"test content", "content_type": "text/plain", "cid": "test-cid"}
        ]
        result = attachment(files)
        assert len(result) == 1
        assert isinstance(result[0], MtomAttachment)
        assert result[0].content_type == "text/plain"

    def test_attachment_multiple_files(self):
        files: list[dict[str, str | bytes]] = [
            {"content": b"file1", "content_type": "text/plain", "cid": "cid1"},
            {"content": b"file2", "content_type": "application/xml", "cid": "cid2"},
        ]
        result = attachment(files)
        assert len(result) == 2
        assert result[0].content_type == "text/plain"
        assert result[1].content_type == "application/xml"

    def test_attachment_with_auto_generated_cid(self):
        result = attachment([{"content": b"test", "content_type": "text/plain"}])
        assert len(result) == 1
        assert result[0].get_cid().decode()

    def test_attachment_appends_to_existing_list(self):
        existing = [Mock(spec=MtomAttachment)]
        result = attachment([{"content": b"new", "content_type": "text/plain", "cid": "new-cid"}],
                            attachments=existing)
        assert len(result) == 2
        assert result[0] == existing[0]


class TestGetPayload:
    def test_get_payload_single_payload(self):
        user_message = {"PayloadInfo": [{"href": "cid:payload-1", "PartProperties": {"Property": []}}]}
        mock_payload = Mock()
        mock_payload.payloadId = "cid:payload-1"
        mock_payload.value = b"test payload content"
        body = Mock()
        body.payload = mock_payload
        result = get_payload(user_message, body)
        assert result == [{"href": "cid:payload-1", "content": "test payload content"}]

    def test_get_payload_multiple_payloads(self):
        user_message = {
            "PayloadInfo": [
                {"href": "cid:payload-1", "PartProperties": {"Property": []}},
                {"href": "cid:payload-2", "PartProperties": {"Property": []}},
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


class TestAS4Client:
    def test_as4client_initialization(self):
        client = AS4Client("http://example.com/service?wsdl", Mock(spec=MtomTransport), [],
                           Mock(spec=Header))
        assert client.client is None


class TestHeader:
    @staticmethod
    def _make_header(**kwargs):
        return Header(
            "c1", "type-1", "c2", "type-2", "c3", "type-3", "c4", "type-4", **kwargs
        )

    def test_default_conversation_id_is_unique_per_header(self):
        first = self._make_header()
        second = self._make_header()

        assert first.conversationid != second.conversationid

    def test_service_type_is_written_to_xml(self):
        header = self._make_header(service_type="custom-service-type")
        service = header.element.find(".//{http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/}Service")

        assert service is not None
        assert service.get("type") == "custom-service-type"


class TestAS4Send:
    def test_as4send_invalid_transport_raises_error(self):
        with pytest.raises(TypeError, match="Transport must be an instance of MtomTransport"):
            AS4Send("http://example.com/wsdl", Mock(), [], Mock(spec=Header))

    @patch("pyAS4.AS4Client.Client")
    @patch("pyAS4.AS4Client.attachment")
    def test_as4send_send_message(self, mock_attachment_func, mock_client_class):
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.element = Mock()
        mock_attach = Mock(spec=MtomAttachment)
        mock_attach.get_cid.return_value = b"test-cid"
        mock_attach.content_type = "text/plain"
        mock_attachment_func.return_value = [mock_attach]
        mock_zeep_client = Mock(spec=Client)
        mock_zeep_client.get_type.return_value = Mock
        mock_zeep_client.service.submitMessage.return_value = "success"
        mock_client_class.return_value = mock_zeep_client
        client = AS4Send("http://example.com/wsdl", transport, [], header)
        assert client.send_message([{"content": b"test", "content_type": "text/plain"}]) == "success"


class TestAS4Receive:
    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_get_pending(self, mock_client_class):
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"
        mock_zeep_client = Mock(spec=Client)
        mock_zeep_client.service.listPendingMessages.return_value = [Mock(messageId="msg-1")]
        mock_client_class.return_value = mock_zeep_client
        client = AS4Receive("http://example.com/wsdl", transport, [], header)
        assert len(client._get_pending()) == 1

    @patch("pyAS4.AS4Client.get_dict_header")
    @patch("pyAS4.AS4Client.get_payload")
    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_receive_message(
            self,
            mock_client_class, mock_get_payload, mock_get_dict_header):
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"
        mock_zeep_client = Mock(spec=Client)
        mock_pending_item = Mock()
        mock_pending_item.messageId = "msg-1"
        mock_zeep_client.service.listPendingMessages.return_value = [mock_pending_item]
        mock_retrieved = Mock()
        mock_retrieved.header.ebMSHeaderInfo.UserMessage = Mock()
        mock_retrieved.body = Mock()
        mock_zeep_client.service.retrieveMessage.return_value = mock_retrieved
        mock_client_class.return_value = mock_zeep_client
        mock_get_dict_header.return_value = {"key": "value"}
        mock_get_payload.return_value = [{"payload": "data"}]
        client = AS4Receive("http://example.com/wsdl", transport, [], header)
        messages = list(client.receive_message())
        assert messages[0]["messageId"] == "msg-1"

    # @patch("pyAS4.AS4Client.Client")
    # def test_as4receive_receive_message_skips_items_without_message_id(self, mock_client_class):
    #     transport = Mock(spec=MtomTransport)
    #     header = Mock(spec=Header)
    #     header.c4_party_id = "party-4"
    #     mock_zeep_client = Mock(spec=Client)
    #     mock_zeep_client.service.listPendingMessages.return_value = [object()]
    #     mock_client_class.return_value = mock_zeep_client
    #     client = AS4Receive("http://example.com/wsdl", transport, [], header)
    #     assert list(client.receive_message()) == []

    @patch("pyAS4.AS4Client.Client")
    def test_as4receive_get_pending_soap_fault(self, mock_client_class):
        transport = Mock(spec=MtomTransport)
        header = Mock(spec=Header)
        header.c4_party_id = "party-4"
        mock_zeep_client = Mock(spec=Client)
        mock_zeep_client.service.listPendingMessages.side_effect = Fault("Test fault")
        mock_client_class.return_value = mock_zeep_client
        client = AS4Receive("http://example.com/wsdl", transport, [], header)
        with pytest.raises(Fault):
            client._get_pending()
