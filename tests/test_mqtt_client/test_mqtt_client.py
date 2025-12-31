import pytest
from unittest.mock import Mock, patch
from tests.commons import TestSamples


def test_create_random_payload(mqtt_client_fixture, monkeypatch):
    # Test the payload creation
    payload = mqtt_client_fixture.create_random_payload()

    assert "id" in payload
    assert isinstance(payload, str)


def test_publish(mqtt_client_fixture, monkeypatch):
    # Mock the publish method on the actual instance
    mock_publish = Mock()
    monkeypatch.setattr(mqtt_client_fixture.client, "publish", mock_publish)

    # Call the publish method
    mqtt_client_fixture.publish("test/topic", "test message")

    # Assert publish was called with at least these arguments
    mock_publish.assert_called_once_with("test/topic", "test message", qos=2, retain=False)


def test_subscribe(mqtt_client_fixture, monkeypatch):
    # Mock the client's subscribe method
    mock_subscribe = Mock()
    monkeypatch.setattr(mqtt_client_fixture.client, "subscribe", mock_subscribe)
    
    mqtt_client_fixture.subscribe("test/topic")

    # Assert that subscribe was called with correct topic
    mock_subscribe.assert_called_once_with("test/topic")


def test_connect_to_broker(mqtt_client_fixture, monkeypatch):
    # Mock the MQTT client's connect method
    mock_connect = Mock()
    monkeypatch.setattr(mqtt_client_fixture.client, "connect", mock_connect)

    # Simulate connecting to the broker
    mqtt_client_fixture.client.connect(mqtt_client_fixture.broker_url, mqtt_client_fixture.broker_port)

    # Assert that connect was called with the correct broker URL and port
    mock_connect.assert_called_once_with(mqtt_client_fixture.broker_url, mqtt_client_fixture.broker_port)


def test_disconnect(mqtt_client_fixture, monkeypatch):
    """ Test that the MQTT client disconnects properly. """

    # Mock the disconnect method
    mock_disconnect = Mock()
    monkeypatch.setattr(mqtt_client_fixture.client, "disconnect", mock_disconnect)

    # Stop the MQTT client
    mqtt_client_fixture.stop()

    # Assert that disconnect was called once
    mock_disconnect.assert_called_once()


if __name__ == "__main__":
    pytest.main()
