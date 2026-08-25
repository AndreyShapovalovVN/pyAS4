# pyrefly: ignore [missing-import]

from pyAS4.AS4Client import AS4Client

def test_AS4Client():
    # Create an instance of AS4Client with test parameters
    wsdl = "http://example.com/service?wsdl"
    session = None  # Replace with a mock or actual Session object if needed
    plugins = None  # Replace with a list of plugins if needed
    cache = None  # Replace with a cache object if needed
    files = None  # Replace with a list of files if needed

    client = AS4Client(
        wsdl=wsdl,
        session=session,
        plugins=plugins,
        cache=cache,
        files=files,
        c1_party_id="C1_ID",
        c1_party_id_type="C1_TYPE",
        c2_party_id="C2_ID",
        c2_party_id_type="C2_TYPE",
        c3_party_id="C3_ID"
    )

    # Assert that the client is initialized correctly
    assert client.wsdl == wsdl
    assert isinstance(client.transport, type(client.transport))
    assert isinstance(client.header, type(client.header))