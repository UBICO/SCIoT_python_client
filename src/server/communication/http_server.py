from fastapi import FastAPI, HTTPException, Request
from server.communication.request_handler import RequestHandler
from server.logger.log import logger
import ntplib
import threading
import time
import traceback
import sys

class HttpServer:
    def __init__(
        self,
        host: str,
        port: int,
        endpoints: dict,
        ntp_server: str,
        input_height: int,
        input_width: int,
        last_offloading_layer: int,
        request_handler: RequestHandler
    ):
        self.app = FastAPI()
        self.host = host
        self.port = port
        self.endpoints = endpoints

        self.devices = set()
        # Map client_id -> model_name for multi-client support
        self.client_models = {}

        # Set up model
        self.input_height = input_height
        self.input_width = input_width
        self.best_offloading_layer = last_offloading_layer

        # Set up request handler
        self.request_handler = request_handler

        # Set up NTP client
        self.ntp_client = ntplib.NTPClient()
        self.ntp_server = ntp_server
        self.offset = self._sync_with_ntp()
        self.start_timestamp = self._get_current_time()
        self._setup_routes()

    def _sync_with_ntp(self) -> float:
        ntp_timestamp = None
        while ntp_timestamp is None:
            try:
                response = self.ntp_client.request(self.ntp_server)
                # Get the offset between local clock time and ntp server time (seconds since 1900)
                offset = response.offset
                return offset
            except ntplib.NTPException as _:
                continue
        threading.Timer(600, self.sync_with_ntp).start()

    def _get_current_time(self) -> float:
        return time.time() + self.offset

    def _assign_model_to_client(self, client_id: str) -> str:
        """
        Assign a model to the connecting client.
        
        Current implementation: Assign default model
        Future enhancements: 
        - Load balancing across models
        - Client-specific model selection
        - Performance-based model assignment
        """
        # For now, assign the default model (can be made configurable)
        return "fomo_96x96"

    def _setup_routes(self):
        @self.app.post(self.endpoints['registration'])
        async def registration(data: dict):
            try:
                client_id = data.get("client_id", "unknown")
                
                # Server assigns a model to this client
                # For now, assign default model. Can be enhanced for load balancing, etc.
                assigned_model = self._assign_model_to_client(client_id)
                
                # Register client and store model mapping
                self.client_models[client_id] = assigned_model
                self.devices.add(client_id)
                
                logger.info(f"Client registered: {client_id} (assigned model: {assigned_model})")
                print(f"Client {client_id} registered, assigned model: {assigned_model}")
                
                return {
                    'message': 'Success',
                    'client_id': client_id,
                    'model_name': assigned_model
                }
            except Exception as e:
                print(f"ERROR in registration endpoint: {type(e).__name__}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post(self.endpoints['device_input'])
        async def device_input(request: Request, client_id: str = None):
            try:
                body = await request.body()  # Reads raw bytes
                self.request_handler.handle_device_input(body, self.input_height, self.input_width, client_id)
                return {'message': 'Success'}
            except Exception as e:
                print(f"ERROR in device_input endpoint: {type(e).__name__}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post(self.endpoints['device_inference_result'])
        async def device_inference_result(request: Request, client_id: str = None):
            try:
                received_timestamp = self._get_current_time()
                body = await request.body()  # Reads raw bytes
                self.best_offloading_layer = self.request_handler.handle_device_inference_result(body=body, received_timestamp=received_timestamp, client_id=client_id)
                return {'message': 'Success'}
            except Exception as e:
                error_msg = f"ERROR in device_inference_result endpoint: {type(e).__name__}: {e}"
                logger.error(error_msg)
                print(error_msg, file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get(self.endpoints['offloading_layer'])
        async def offloading_layer(client_id: str = None):
            try:
                cleaned_offloading_layer_index = self.request_handler.handle_offloading_layer(best_offloading_layer=self.best_offloading_layer, client_id=client_id)
                return {'offloading_layer_index': cleaned_offloading_layer_index}
            except Exception as e:
                print(f"ERROR in offloading_layer endpoint: {type(e).__name__}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def run(self):
        import uvicorn
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port
        )
