# pyrefly: ignore [missing-import]

from unittest.mock import Mock

from pyAS4.AS4Client import AS4Client


def test_AS4Client():
    wsdl = "http://example.com/service?wsdl"
    transport = Mock()
    settings = Mock()
    plugins = [Mock()]

    client = AS4Client(
        wsdl=wsdl,
        transport=transport,
        settings=settings,
        plugins=plugins,
    )

    assert client.wsdl == wsdl
    assert client.transport is transport
    assert client.settings is settings
    assert client.plugins == plugins