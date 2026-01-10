from dotenv import load_dotenv
import uvicorn
import os

def main():
    load_dotenv()
    
    uvicorn.run(
        "src:create_app",
        host="0.0.0.0",
        port=3000,
        workers=1,
        loop="asyncio",
        http="h11",
        limit_concurrency=100,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30,
        access_log=True,
        log_level="debug"
    )

if __name__ == "__main__":
    main()