from dotenv import load_dotenv

import uvicorn
import os
load_dotenv()
if __name__ == "__main__":
    
    uvicorn.run(
            "src:create_app",  # Assuming your FastAPI app is in a file named main.py
            host="0.0.0.0",
            port=7000,
            # Concurrency settings
            workers=int(os.environ.get("WORKERS",1)),  # Ilość worker procesów
            loop="asyncio",  # Najlepszy dla async
            http="h11",  # Albo "httptools" dla lepszej wydajności

            # Connection limits
            limit_concurrency=1000,  # Max concurrent connections
            limit_max_requests=10000,  # Max requests per worker

            # Timeouts
            timeout_keep_alive=30,  # Keep-alive timeout
            timeout_graceful_shutdown=30,

            # Logging
            access_log=True,  # Wyłącz access log dla wydajności
            log_level="debug"
        )