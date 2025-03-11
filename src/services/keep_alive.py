import logging
import threading
import time
import requests
import os

logger = logging.getLogger(__name__)

class KeepAliveService:
    def __init__(self, interval_minutes=10):
        """Initialize the keep-alive service with a specified interval."""
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.thread = None
        
        # Get the service URL from environment or construct it
        self.url = os.getenv("SERVICE_URL")
        if not self.url:
            # Try to construct from Render environment variables
            render_service = os.getenv("RENDER_SERVICE_NAME")
            if render_service:
                self.url = f"https://{render_service}.onrender.com"
            else:
                # Fallback to localhost (for testing)
                port = os.getenv("PORT", 8000)
                self.url = f"http://localhost:{port}"
        
        # Append health endpoint
        if self.url:
            self.url = f"{self.url}/health"

    def _keep_alive_task(self):
        """Task that sends periodic requests to keep the service alive."""
        logger.info(f"Keep-alive service started, pinging {self.url} every {self.interval_seconds} seconds")
        
        while self.running:
            try:
                start_time = time.time()
                response = requests.get(self.url, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Keep-alive ping successful: {response.status_code}, latency: {(time.time() - start_time)*1000:.2f}ms")
                else:
                    logger.warning(f"Keep-alive ping returned non-200 status: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Keep-alive ping failed: {e}")
            
            # Sleep until next interval
            time.sleep(self.interval_seconds)

    def start(self):
        """Start the keep-alive service in a background thread."""
        if not self.url:
            logger.warning("Cannot start keep-alive service: No service URL configured")
            return False
            
        if self.running:
            logger.warning("Keep-alive service is already running")
            return True
            
        self.running = True
        self.thread = threading.Thread(target=self._keep_alive_task, daemon=True)
        self.thread.start()
        return True
        
    def stop(self):
        """Stop the keep-alive service."""
        if not self.running:
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None