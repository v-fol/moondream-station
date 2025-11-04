import asyncio
import json
import os
import subprocess
import time
import uvicorn
import logging

from threading import Thread, Event, Lock
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from .inference_service import InferenceService


class RestServer:
    def __init__(self, config, manifest_manager, session_state=None, analytics=None):
        self.config = config
        self.manifest_manager = manifest_manager
        self.session_state = session_state
        self.analytics = analytics
        self.inference_service = InferenceService(config, manifest_manager)
        self.app = FastAPI(title="Moondream Station Inference Server", version="1.0.0")
        self.server = None
        self.server_thread = None
        
        # Shutdown monitor configuration
        self.shutdown_enabled = self.config.get("shutdown_monitor_enabled", 
            os.getenv("SHUTDOWN_MONITOR_ENABLED", "true").lower() == "true")
        self.shutdown_check_interval = float(self.config.get("shutdown_check_interval",
            os.getenv("SHUTDOWN_CHECK_INTERVAL", "30.0")))
        self.shutdown_timeout = float(self.config.get("shutdown_timeout",
            os.getenv("SHUTDOWN_TIMEOUT", "30.0")))
        
        # Shutdown monitor state
        self.shutdown_thread: Optional[Thread] = None
        self.shutdown_event = Event()
        self.shutdown_lock = Lock()
        self.last_idle_time: Optional[float] = None
        self.consecutive_idle_checks = 0
        self.shutdown_attempted = False
        
        # Setup logger for shutdown monitor
        self.logger = logging.getLogger(__name__)
        
        self._setup_routes()
        
        # Start shutdown monitor if enabled
        if self.shutdown_enabled:
            self._start_shutdown_monitor()

    async def _verify_api_key(self, request: Request):
        """Verify API key from X-Auth header"""
        api_key = self.config.get("detection_api_key")
        
        # If no API key is configured, skip authentication
        if not api_key:
            return True
            
        # Get the API key from the X-Auth header
        auth_header = request.headers.get("X-API-Key")
        
        if not auth_header:
            raise HTTPException(
                status_code=401, 
                detail="Missing X-API-Key header"
            )
            
        if auth_header != api_key:
            raise HTTPException(
                status_code=401, 
                detail="Invalid API key"
            )
            
        return True

    def _sse_event_generator(self, raw_generator):
        """Convert generator tokens to Server-Sent Events format with token counting"""
        token_count = 0
        start_time = time.time()

        for token in raw_generator:
            token_count += 1
            yield f"data: {json.dumps({'chunk': token})}\n\n"

        # Send final stats
        duration = time.time() - start_time
        if duration > 0 and token_count > 0:
            tokens_per_sec = round(token_count / duration, 1)
            stats = {
                "tokens": token_count,
                "duration": round(duration, 2),
                "tokens_per_sec": tokens_per_sec,
            }
            yield f"data: {json.dumps({'stats': stats})}\n\n"

        yield f"data: {json.dumps({'completed': True})}\n\n"

    def _setup_routes(self):
        @self.app.get("/health")
        async def health(auth: bool = Depends(self._verify_api_key)):
            return {"status": "ok", "server": "moondream-station"}

        @self.app.get("/v1/models")
        async def list_models(auth: bool = Depends(self._verify_api_key)):
            models = self.manifest_manager.get_models()
            return {
                "models": [
                    {
                        "id": model_id,
                        "name": model_info.name,
                        "description": model_info.description,
                        "version": model_info.version,
                    }
                    for model_id, model_info in models.items()
                ]
            }

        @self.app.get("/v1/stats")
        async def get_stats(auth: bool = Depends(self._verify_api_key)):
            stats = self.inference_service.get_stats()
            # Add requests processed from session state
            if self.session_state:
                stats["requests_processed"] = self.session_state.state["requests_processed"]
            else:
                stats["requests_processed"] = 0
            return stats

        @self.app.api_route(
            "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        async def dynamic_route(request: Request, path: str, auth: bool = Depends(self._verify_api_key)):
            return await self._handle_dynamic_request(request, path)

    async def _handle_dynamic_request(self, request: Request, path: str):
        if not self.inference_service.is_running():
            raise HTTPException(status_code=503, detail="Inference service not running")

        function_name = self._extract_function_name(path)
        kwargs = await self._extract_request_data(request)

        timeout = kwargs.pop("timeout", None)
        if timeout:
            try:
                timeout = float(timeout)
            except (ValueError, TypeError):
                timeout = None

        # Check if streaming is requested
        stream = kwargs.get("stream", False)

        start_time = time.time()
        try:
            result = await self.inference_service.execute_function(
                function_name, timeout, **kwargs
            )

            # Record the request in session state
            if self.session_state:
                self.session_state.record_request(f"/{path}")

            success = not (isinstance(result, dict) and result.get("error"))
        except Exception as e:
            if self.analytics:
                self.analytics.track_error(
                    type(e).__name__,
                    str(e),
                    f"api_{function_name}"
                )
            raise

        # Handle streaming response
        if stream and isinstance(result, dict) and not result.get("error"):
            # Look for any generator in result (any capability can stream)
            generator_key = None
            generator = None

            for key, value in result.items():
                if hasattr(value, "__iter__") and hasattr(value, "__next__"):
                    generator_key = key
                    generator = value
                    break

            if generator:
                event_generator = self._sse_event_generator(generator)
                return StreamingResponse(
                    event_generator, media_type="text/event-stream"
                )

        # Add token stats and analytics for non-streaming responses
        if isinstance(result, dict) and not result.get("error"):
            token_count = 0
            # Count tokens from any string result
            for key, value in result.items():
                if isinstance(value, str):
                    token_count += len(value.split())

            duration = time.time() - start_time
            if duration > 0 and token_count > 0:
                result["_stats"] = {
                    "tokens": token_count,
                    "duration": round(duration, 2),
                    "tokens_per_sec": round(token_count / duration, 1),
                }

            if self.analytics:
                self.analytics.track_api_call(
                    function_name,
                    duration,
                    tokens=token_count,
                    success=success,
                    model=self.config.get("current_model")
                )

        return JSONResponse(result)

    def _extract_function_name(self, path: str) -> str:
        path_parts = [p for p in path.split("/") if p]
        if path_parts and path_parts[0] == "v1" and len(path_parts) > 1:
            return path_parts[1]
        elif path_parts:
            return path_parts[-1]
        return "index"

    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        kwargs = {}

        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                body = await request.json()
                kwargs.update(body)
            except json.JSONDecodeError:
                pass
        elif "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            kwargs.update(dict(form))
        elif "multipart/form-data" in content_type:
            form = await request.form()
            for key, value in form.items():
                kwargs[key] = value

        kwargs.update(dict(request.query_params))

        kwargs["_headers"] = dict(request.headers)
        kwargs["_method"] = request.method

        return kwargs

    def start(self, host: str = "127.0.0.1", port: int = 2020) -> bool:
        if self.server_thread and self.server_thread.is_alive():
            return False

        current_model = self.config.get("current_model")
        if not current_model:
            return False

        if not self.inference_service.start(current_model):
            return False

        try:
            config = uvicorn.Config(
                self.app,
                host=host,
                port=port,
                log_level="critical",  # Suppress more logs
                access_log=False,
            )
            self.server = uvicorn.Server(config)

            self.server_thread = Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            time.sleep(1)

            return self.is_running()
        except Exception:
            return False

    def _run_server(self):
        try:
            asyncio.run(self.server.serve())
        except Exception:
            # Suppress normal shutdown errors
            pass

    def stop(self) -> bool:
        """Stop the REST server properly"""
        # Stop shutdown monitor first
        self._stop_shutdown_monitor()
        
        if self.server:
            # Signal server to stop
            self.server.should_exit = True

            # Force shutdown the server
            if hasattr(self.server, "force_exit"):
                self.server.force_exit = True

        # Wait for server thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=3)

            # If thread is still alive, something went wrong
            if self.server_thread.is_alive():
                import logging

                logging.warning("Server thread did not shut down cleanly")

        # Stop inference service
        if hasattr(self, "inference_service") and self.inference_service:
            try:
                # Run the async stop in a sync context
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create task if loop is running
                        asyncio.create_task(self.inference_service.stop())
                    else:
                        # Run directly if loop is not running
                        loop.run_until_complete(self.inference_service.stop())
                except RuntimeError:
                    # No event loop, run in new loop
                    asyncio.run(self.inference_service.stop())
            except Exception:
                pass

        # Clean up references
        self.server = None
        self.server_thread = None

        return True

    def is_running(self) -> bool:
        return (
            self.server_thread
            and self.server_thread.is_alive()
            and self.server
            and not self.server.should_exit
        )
    
    def _start_shutdown_monitor(self):
        """Start background thread to monitor queue and shutdown if idle"""
        if not self.shutdown_enabled:
            self.logger.info("Shutdown monitor is disabled")
            return
        
        pod_id = os.environ.get("RUNPOD_POD_ID")
        if not pod_id:
            self.logger.warning(
                "Shutdown monitor enabled but RUNPOD_POD_ID not set. "
                "Monitor will log warnings but cannot shutdown pod."
            )
        
        self.logger.info(
            f"Starting shutdown monitor: check_interval={self.shutdown_check_interval}s, "
            f"timeout={self.shutdown_timeout}s, pod_id={pod_id or 'NOT_SET'}"
        )
        
        def monitor_loop():
            """Main monitoring loop - runs in background thread"""
            consecutive_errors = 0
            max_consecutive_errors = 5
            
            while not self.shutdown_event.is_set():
                try:
                    # Wait for check interval or until event is set
                    if self.shutdown_event.wait(self.shutdown_check_interval):
                        # Event was set, exit gracefully
                        break
                    
                    # Check if we should skip this check (e.g., after shutdown attempt)
                    with self.shutdown_lock:
                        if self.shutdown_attempted:
                            self.logger.info("Shutdown already attempted, stopping monitor")
                            break
                    
                    # Get current stats - handle errors gracefully
                    try:
                        stats = self.inference_service.get_stats()
                    except Exception as e:
                        self.logger.warning(f"Failed to get inference stats: {e}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            self.logger.error(
                                f"Too many consecutive errors ({consecutive_errors}), "
                                "stopping shutdown monitor"
                            )
                            break
                        continue
                    
                    # Reset error counter on success
                    consecutive_errors = 0
                    
                    # Extract queue and processing counts with safe defaults
                    queue_size = stats.get("queue_size", 0)
                    processing = stats.get("processing", 0)
                    
                    # Handle case where stats might not have expected keys
                    if not isinstance(queue_size, (int, float)) or not isinstance(processing, (int, float)):
                        self.logger.warning(
                            f"Invalid stats format: queue_size={queue_size}, processing={processing}"
                        )
                        continue
                    
                    queue_size = int(queue_size)
                    processing = int(processing)
                    
                    # Check if idle
                    if queue_size == 0 and processing == 0:
                        current_time = time.time()
                        
                        with self.shutdown_lock:
                            if self.last_idle_time is None:
                                self.last_idle_time = current_time
                                self.consecutive_idle_checks = 1
                                self.logger.debug(
                                    f"Service idle detected (queue={queue_size}, processing={processing}), "
                                    f"starting timeout timer"
                                )
                            else:
                                idle_duration = current_time - self.last_idle_time
                                self.consecutive_idle_checks += 1
                                
                                # Log progress periodically
                                if self.consecutive_idle_checks % 10 == 0:
                                    self.logger.info(
                                        f"Service idle for {idle_duration:.1f}s "
                                        f"({self.consecutive_idle_checks} checks)"
                                    )
                                
                                # Check if timeout exceeded
                                if idle_duration >= self.shutdown_timeout:
                                    self.logger.info(
                                        f"Shutdown timeout exceeded ({idle_duration:.1f}s >= {self.shutdown_timeout}s). "
                                        f"Queue and processing are both 0. Initiating pod shutdown."
                                    )
                                    self._shutdown_pod()
                                    break
                    else:
                        # Reset idle timer if there's work
                        with self.shutdown_lock:
                            if self.last_idle_time is not None:
                                was_idle_duration = time.time() - self.last_idle_time
                                self.logger.debug(
                                    f"Service no longer idle (queue={queue_size}, processing={processing}). "
                                    f"Was idle for {was_idle_duration:.1f}s"
                                )
                            self.last_idle_time = None
                            self.consecutive_idle_checks = 0
                    
                except Exception as e:
                    # Catch-all for any unexpected errors
                    self.logger.error(f"Unexpected error in shutdown monitor loop: {e}", exc_info=True)
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.error(
                            f"Too many consecutive errors ({consecutive_errors}), "
                            "stopping shutdown monitor"
                        )
                        break
                    # Wait a bit before retrying after error
                    time.sleep(min(self.shutdown_check_interval, 5.0))
            
            self.logger.info("Shutdown monitor thread exiting")
        
        # Start the monitoring thread
        self.shutdown_thread = Thread(target=monitor_loop, daemon=True, name="ShutdownMonitor")
        self.shutdown_thread.start()
        self.logger.info("Shutdown monitor thread started")
    
    def _stop_shutdown_monitor(self):
        """Stop the shutdown monitor thread gracefully"""
        if not self.shutdown_thread or not self.shutdown_thread.is_alive():
            return
        
        self.logger.info("Stopping shutdown monitor...")
        self.shutdown_event.set()
        
        # Wait for thread to finish (with timeout)
        if self.shutdown_thread.is_alive():
            self.shutdown_thread.join(timeout=5.0)
            if self.shutdown_thread.is_alive():
                self.logger.warning("Shutdown monitor thread did not exit cleanly")
            else:
                self.logger.info("Shutdown monitor stopped")
    
    def _shutdown_pod(self):
        """Execute runpodctl remove pod command to terminate the pod"""
        with self.shutdown_lock:
            if self.shutdown_attempted:
                self.logger.warning("Shutdown already attempted, skipping")
                return
            self.shutdown_attempted = True
        
        try:
            result = subprocess.run(
                ["runpodctl", "remove", "pod", '$RUNPOD_POD_ID'],
                capture_output=True,
                timeout=30,  # 30 second timeout for the command
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully initiated pod shutdown: {result.stdout}")
            else:
                self.logger.error(
                    f"Failed to shutdown pod (exit code {result.returncode}): "
                    f"{result.stderr or result.stdout}"
                )
                
        except subprocess.TimeoutExpired:
            self.logger.error("runpodctl command timed out after 30 seconds")
        except FileNotFoundError:
            self.logger.error(
                "runpodctl command not found. Make sure runpodctl is installed and in PATH."
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"runpodctl command failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while shutting down pod: {e}", exc_info=True)
