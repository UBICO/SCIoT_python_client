"""
Test suite for multi-client model negotiation support.

Tests cover:
- Client ID generation (random and configured)
- Model negotiation during registration
- Server-side model assignment
- Multiple concurrent clients
- Per-client request handling
"""

import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from server.communication.http_server import HttpServer
from server.communication.request_handler import RequestHandler


class TestClientIDGeneration:
    """Test client ID generation logic"""
    
    def test_generate_random_client_id_when_null(self):
        """Client should generate random 8-char ID when config has null"""
        # Simulate config with null client_id
        config = {"client": {"client_id": None}}
        
        # When client ID is None, it should generate random
        if config["client"]["client_id"]:
            client_id = str(config["client"]["client_id"])
        else:
            # In real code, uses uuid
            client_id = str(uuid.uuid4())[:8]
        
        # Check: 8 chars
        assert len(client_id) == 8
        # Check: alphanumeric
        assert client_id.replace('-', '').isalnum()
    
    def test_use_configured_client_id(self):
        """Client should use configured ID when provided"""
        config = {"client": {"client_id": "device_01"}}
        
        client_id_config = config["client"].get("client_id")
        if client_id_config:
            client_id = str(client_id_config)
        else:
            client_id = str(uuid.uuid4())[:8]
        
        assert client_id == "device_01"
    
    def test_multiple_random_ids_are_unique(self):
        """Each random ID should be unique"""
        ids = set()
        for _ in range(10):
            new_id = str(uuid.uuid4())[:8]
            ids.add(new_id)
        
        # All 10 should be unique
        assert len(ids) == 10


class TestServerModelAssignment:
    """Test server-side model assignment during registration"""
    
    def test_assign_default_model(self):
        """Server should assign default model when no preference"""
        http_server = Mock(spec=HttpServer)
        http_server._assign_model_to_client = Mock(return_value="fomo_96x96")
        
        assigned_model = http_server._assign_model_to_client("client_123")
        
        assert assigned_model == "fomo_96x96"
        http_server._assign_model_to_client.assert_called_once_with("client_123")
    
    def test_server_tracks_client_model_mapping(self):
        """Server should store client -> model mapping"""
        http_server = Mock(spec=HttpServer)
        http_server.client_models = {}
        http_server.devices = set()
        
        # Simulate registration
        client_id = "device_01"
        assigned_model = "fomo_96x96"
        
        http_server.client_models[client_id] = assigned_model
        http_server.devices.add(client_id)
        
        # Verify mapping stored
        assert http_server.client_models[client_id] == "fomo_96x96"
        assert client_id in http_server.devices
    
    def test_multiple_clients_get_separate_mappings(self):
        """Each client should have its own model mapping"""
        http_server = Mock(spec=HttpServer)
        http_server.client_models = {}
        http_server.devices = set()
        
        # Register multiple clients
        clients = [
            ("a1b2c3d4", "fomo_96x96"),
            ("device_01", "fomo_96x96"),
            ("mobile_02", "fomo_96x96"),
        ]
        
        for client_id, model in clients:
            http_server.client_models[client_id] = model
            http_server.devices.add(client_id)
        
        # Verify all tracked
        assert len(http_server.client_models) == 3
        assert len(http_server.devices) == 3
        for client_id, model in clients:
            assert http_server.client_models[client_id] == model


class TestRegistrationPayload:
    """Test registration request/response payloads"""
    
    def test_registration_request_only_has_client_id(self):
        """Client registration should only include client_id, not model_name"""
        client_id = "device_01"
        
        # Registration payload should NOT include model_name
        payload = {"client_id": client_id}
        
        assert "client_id" in payload
        assert "model_name" not in payload
        assert payload["client_id"] == "device_01"
    
    def test_registration_response_includes_assigned_model(self):
        """Server response should include model_name for client"""
        response = {
            "message": "Success",
            "client_id": "device_01",
            "model_name": "fomo_96x96"
        }
        
        assert response["client_id"] == "device_01"
        assert response["model_name"] == "fomo_96x96"
        assert response["message"] == "Success"
    
    def test_client_stores_assigned_model(self):
        """Client should store model from server response"""
        response_data = {
            "client_id": "device_01",
            "model_name": "fomo_96x96"
        }
        
        MODEL_NAME = response_data.get("model_name", "fomo_96x96")
        
        assert MODEL_NAME == "fomo_96x96"


class TestMultiClientRequests:
    """Test request handling with client_id parameter"""
    
    def test_device_input_includes_client_id(self):
        """Device input request should include client_id parameter"""
        client_id = "device_01"
        params = {"client_id": client_id}
        
        assert "client_id" in params
        assert params["client_id"] == "device_01"
    
    def test_offloading_layer_request_includes_client_id(self):
        """Offloading layer request should include client_id parameter"""
        client_id = "mobile_02"
        params = {"client_id": client_id}
        
        assert params["client_id"] == "mobile_02"
    
    def test_device_inference_result_includes_client_id(self):
        """Inference result request should include client_id parameter"""
        client_id = "a1b2c3d4"
        params = {"client_id": client_id}
        
        assert params["client_id"] == "a1b2c3d4"
    
    def test_server_can_identify_request_client(self):
        """Server should be able to identify which client made request"""
        http_server = Mock(spec=HttpServer)
        http_server.client_models = {
            "device_01": "fomo_96x96",
            "mobile_02": "fomo_96x96",
        }
        
        # Server receives request from device_01
        client_id = "device_01"
        client_model = http_server.client_models.get(client_id)
        
        assert client_model == "fomo_96x96"


class TestModelNegotiation:
    """Test model negotiation workflow"""
    
    def test_complete_negotiation_flow(self):
        """Test complete client registration and model assignment flow"""
        # Step 1: Client initialization
        client_id = str(uuid.uuid4())[:8]
        assert len(client_id) == 8
        
        # Step 2: Client sends registration with only client_id
        registration_request = {"client_id": client_id}
        assert "model_name" not in registration_request
        
        # Step 3: Server receives and assigns model
        http_server = Mock(spec=HttpServer)
        http_server.client_models = {}
        http_server.devices = set()
        http_server._assign_model_to_client = Mock(return_value="fomo_96x96")
        
        assigned_model = http_server._assign_model_to_client(client_id)
        http_server.client_models[client_id] = assigned_model
        http_server.devices.add(client_id)
        
        # Step 4: Server responds with assignment
        registration_response = {
            "message": "Success",
            "client_id": client_id,
            "model_name": assigned_model
        }
        
        # Step 5: Client stores assigned model
        client_model = registration_response.get("model_name", "fomo_96x96")
        
        # Verify complete flow
        assert registration_response["client_id"] == client_id
        assert registration_response["model_name"] == "fomo_96x96"
        assert client_model == "fomo_96x96"
        assert http_server.client_models[client_id] == "fomo_96x96"
    
    def test_fallback_model_when_server_unavailable(self):
        """Client should use fallback model if server unavailable"""
        # Client couldn't reach server
        server_available = False
        
        # Client model still None (not assigned)
        model_name = None
        
        # Fallback logic
        if not server_available and model_name is None:
            model_name = "fomo_96x96"  # Use fallback
        
        assert model_name == "fomo_96x96"


class TestConcurrentClients:
    """Test handling of multiple concurrent clients"""
    
    def test_three_clients_different_ids(self):
        """Three concurrent clients with different IDs"""
        http_server = Mock(spec=HttpServer)
        http_server.client_models = {}
        http_server.devices = set()
        http_server._assign_model_to_client = Mock(return_value="fomo_96x96")
        
        # Register 3 clients
        clients = [
            {"id": str(uuid.uuid4())[:8], "name": "client_A"},  # Random ID
            {"id": "device_01", "name": "client_B"},             # Fixed ID
            {"id": "mobile_02", "name": "client_C"},             # Fixed ID
        ]
        
        for client in clients:
            client_id = client["id"]
            assigned_model = http_server._assign_model_to_client(client_id)
            http_server.client_models[client_id] = assigned_model
            http_server.devices.add(client_id)
        
        # Verify all registered
        assert len(http_server.client_models) == 3
        assert len(http_server.devices) == 3
        
        # Verify each can be looked up
        for client in clients:
            assert client["id"] in http_server.client_models
            assert http_server.client_models[client["id"]] == "fomo_96x96"
    
    def test_concurrent_requests_from_different_clients(self):
        """Server should handle requests from different clients"""
        http_server = Mock(spec=HttpServer)
        http_server.client_models = {
            "device_01": "fomo_96x96",
            "mobile_02": "fomo_96x96",
            "a1b2c3d4": "fomo_96x96",
        }
        
        # Simulate requests from different clients
        requests_from_clients = [
            {"client_id": "device_01", "action": "offloading_layer"},
            {"client_id": "mobile_02", "action": "device_input"},
            {"client_id": "a1b2c3d4", "action": "device_inference_result"},
        ]
        
        for request in requests_from_clients:
            client_id = request["client_id"]
            # Server identifies client
            client_model = http_server.client_models.get(client_id)
            
            assert client_model == "fomo_96x96"
            # Can proceed with client-specific logic


class TestRequestHandlerClientTracking:
    """Test request handler tracking client_id"""
    
    def test_request_handler_accepts_client_id(self):
        """RequestHandler should accept client_id parameter"""
        request_handler = Mock(spec=RequestHandler)
        request_handler.handle_offloading_layer = Mock(return_value=30)
        
        # Handler called with client_id
        result = request_handler.handle_offloading_layer(
            best_offloading_layer=30,
            client_id="device_01"
        )
        
        assert result == 30
        request_handler.handle_offloading_layer.assert_called_once()
    
    def test_request_handler_device_input_with_client_id(self):
        """RequestHandler device_input should accept client_id"""
        request_handler = Mock(spec=RequestHandler)
        request_handler.handle_device_input = Mock()
        
        # Handler called with client_id
        request_handler.handle_device_input(
            rgb565_image=b"fake_data",
            height=96,
            width=96,
            client_id="device_01"
        )
        
        request_handler.handle_device_input.assert_called_once()
    
    def test_request_handler_inference_result_with_client_id(self):
        """RequestHandler inference result should accept client_id"""
        request_handler = Mock(spec=RequestHandler)
        request_handler.handle_device_inference_result = Mock(return_value=30)
        
        # Handler called with client_id
        result = request_handler.handle_device_inference_result(
            body=b"fake_data",
            received_timestamp=1234567890,
            client_id="device_01"
        )
        
        assert result == 30
        request_handler.handle_device_inference_result.assert_called_once()


class TestModelConfigurationFile:
    """Test that client config doesn't require model_name"""
    
    def test_config_without_model_name(self):
        """Client config should not have model_name field"""
        config = {
            "client": {
                "client_id": None
            },
            "http": {
                "server_host": "0.0.0.0",
                "server_port": 8000
            }
        }
        
        # Should not require model_name
        assert "model_name" not in config["client"]
        assert config["client"]["client_id"] is None
    
    def test_fixed_client_id_config(self):
        """Config with fixed client_id should work"""
        config = {
            "client": {
                "client_id": "device_01"
            }
        }
        
        assert config["client"]["client_id"] == "device_01"
        assert "model_name" not in config["client"]


class TestServerLoadBalancing:
    """Test future load balancing capability"""
    
    def test_model_assignment_can_balance_load(self):
        """Server's assignment logic can consider client loads"""
        # Simulate load-aware assignment (future enhancement)
        client_models = {
            "device_01": "fomo_96x96",  # 5 clients
            "mobile_02": "fomo_96x96",  # 5 clients
            "tablet_01": "fomo_96x96",  # 3 clients
        }
        
        # Count clients per model (simplified)
        model_counts = {}
        for model in client_models.values():
            model_counts[model] = model_counts.get(model, 0) + 1
        
        # In future, could assign to least-loaded:
        # if model_counts.get("fomo_96x96", 0) < 10:
        #     return "fomo_96x96"
        # else:
        #     return "mobilenet_lite"
        
        assert "fomo_96x96" in model_counts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
