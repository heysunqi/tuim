"""Tests for the protocol handler base class."""
import asyncio

import pytest

from tuim.models import Connection, ConnectionStatus, Protocol
from tuim.protocols.base import ProtocolHandler


class DummyHandler(ProtocolHandler):
    """Concrete subclass for testing the base class."""

    @property
    def is_interactive(self):
        return True

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def send_input(self, data):
        pass

    async def check_health(self):
        return ConnectionStatus.ONLINE


@pytest.fixture
def dummy_handler():
    conn = Connection(name="test", host="localhost", protocol=Protocol.SSH, port=22)
    return DummyHandler(conn)


def test_handler_initial_state(dummy_handler):
    assert not dummy_handler.is_connected
    assert dummy_handler._on_output is None
    assert dummy_handler._on_disconnect is None


def test_handler_on_output_callback(dummy_handler):
    received = []
    dummy_handler.on_output(lambda data: received.append(data))
    dummy_handler._emit_output("hello")
    assert received == ["hello"]


def test_handler_on_disconnect_callback(dummy_handler):
    called = []
    dummy_handler.on_disconnect(lambda: called.append(True))
    dummy_handler.is_connected = True
    dummy_handler._emit_disconnect()
    assert not dummy_handler.is_connected
    assert called == [True]


@pytest.mark.asyncio
async def test_handler_connect_disconnect(dummy_handler):
    await dummy_handler.connect()
    assert dummy_handler.is_connected
    await dummy_handler.disconnect()
    assert not dummy_handler.is_connected


@pytest.mark.asyncio
async def test_handler_check_health(dummy_handler):
    status = await dummy_handler.check_health()
    assert status == ConnectionStatus.ONLINE
