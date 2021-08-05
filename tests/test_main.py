""" Tests for main.py """

from hl7.mllp import start_hl7_server
import pytest
from asyncio import IncompleteReadError
from unittest.mock import AsyncMock, Mock
import os
from whpa_cdp_hl7_listener_service import main
import importlib
from nats.aio.client import Client as NATS_Client
from nats.aio.errors import ErrNoServers

_hl7_messages_relative_dir = "./tests/resources/hl7_messages/"


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    os.environ["WHPA_CDP_CLIENT_GATEWAY_HL7_MLLP_HOST"] = "hl7-mllp-host"
    os.environ["WHPA_CDP_CLIENT_GATEWAY_HL7_MLLP_PORT"] = "4444"
    os.environ["WHPA_CDP_CLIENT_GATEWAY_NATS_SERVER_URL"] = "nats-server"

    os.environ["WHPA_CDP_CLIENT_GATEWAY_TIMEZONE"] = "some-timezone"
    os.environ["WHPA_CDP_CLIENT_GATEWAY_TENANT"] = "tenant1"

    importlib.reload(main)


@pytest.mark.asyncio
async def test_nc_connect(mocker):
    mocker.patch.object(NATS_Client, "connect")
    result = await main.nc_connect()
    assert result == True

    NATS_Client.connect.side_effect = ErrNoServers()
    with pytest.raises(ErrNoServers) as exp:
        await main.nc_connect()


@pytest.mark.asyncio
async def test_send_msg_to_nats(mocker):
    mocker.patch.object(main, "_nc")
    my_asyncmock = AsyncMock()
    mocker.patch.object(main._nc, "request", new=my_asyncmock)
    await main.send_msg_to_nats("test message")
    my_asyncmock.assert_awaited()


""" See TODOs--Don't run.
@pytest.mark.asyncio
async def test_processed_received_hl7_messages(mocker):
    with open(_hl7_messages_relative_dir + "adt-a01-sample01.hl7", "r") as file:
        hl7_text = str(file.read())

    # Mock reader input parameter.
    # TODO: temp notes:
    # - For my manual testing, as described in the README, some hl7_reader and some
    #   hl7_writer methods are async and some are not (e.g., reader.at_eof() writer.drain(),
    #   writer.close(). Can an AyncMock have a mix of async and non-async methods?
    asyncmock_reader = AsyncMock()
    mocker.patch.object(asyncmock_reader, "at_eof", return_value=[False, True])
    asyncmock_reader.at_eof.not_async = True  # Does not appear to work.
    # Note side_effect applys to async methos.
    # asyncmock_reader.at_eof.side_effect = [False, True]
    mock_hl7_message = Mock()
    mocker.patch.object(mock_hl7_message, "__str__", return_value=hl7_text)
    # Last param needed to save mock calls.
    mocker.patch.object(mock_hl7_message, "create_ack", mock_hl7_message)
    mocker.patch.object(asyncmock_reader, "readmessage", return_value=mock_hl7_message)

    # Mock writer input parameter.
    asyncmock_writer = AsyncMock()
    mocker.patch.object(
        asyncmock_writer, "get_extra_info", return_value="test_hl7_peername"
    )
    mocker.patch.object(asyncmock_writer, "writemessage")
    mocker.patch.object(asyncmock_writer, "drain")

    mocker.patch.object(main, "send_msg_to_nats", new=AsyncMock())

    # Above mocks setup to test the "happy" path.
    #
    await main.process_received_hl7_messages(asyncmock_reader, asyncmock_writer)
    # Expect default "Application Accept" (AA) ack_code.
    assert "ack_code='AA'" in str(mock_hl7_message.mock_calls[0])

    # Test force hl7 parse exception.
    # The exception should be handled and an Application Reject (AR) ack_code returned.
    #
    asyncmock_reader.reset_mock()
    asyncmock_reader.at_eof.side_effect = [False, True]
    asyncmock_writer.reset_mock()
    mock_hl7_message.reset_mock()
    # Last param needed to save mock calls.
    mocker.patch.object(mock_hl7_message, "create_ack", mock_hl7_message)
    mocker.patch.object(mock_hl7_message, "__str__", return_value="not an hl7 message")
    await main.process_received_hl7_messages(asyncmock_reader, asyncmock_writer)
    assert "ack_code='AR'" in str(mock_hl7_message.mock_calls[0])

    # Test asyncio.IncompleteReadError.
    # The exception is raised with this scenario.
    #
    asyncmock_reader.reset_mock()
    asyncmock_reader.at_eof.side_effect = [False, False]
    asyncmock_reader.readmessage.side_effect = IncompleteReadError(
        "some bytes".encode(), 22
    )
    with pytest.raises(IncompleteReadError):
        await main.process_received_hl7_messages(asyncmock_reader, asyncmock_writer)

    # Test general Exception after hl7_message is defined. This should result in
    # an Application Error (AE) ack_code and no raised exception.
    #
    asyncmock_reader.reset_mock()
    asyncmock_reader.at_eof.side_effect = [False, True]
    asyncmock_reader.readmessage.side_effect = None
    asyncmock_writer.reset_mock()
    mock_hl7_message.reset_mock()
    # Last param needed to save mock calls.
    mocker.patch.object(mock_hl7_message, "create_ack", mock_hl7_message)
    mocker.patch.object(mock_hl7_message, "__str__", return_value=hl7_text)
    main.send_msg_to_nats.side_effect = Exception("force exception from mock")
    await main.process_received_hl7_messages(asyncmock_reader, asyncmock_writer)
    assert "ack_code='AE'" in str(mock_hl7_message.mock_calls[0])
"""


@pytest.mark.asyncio
async def test_hl7_receiver_exception(mocker):
    # Session config parameters should result in a connection error that raises an Exception.
    with pytest.raises(Exception):
        await main.hl7_receiver()
