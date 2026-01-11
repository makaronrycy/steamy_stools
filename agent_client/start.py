from dotenv import load_dotenv
from src import get_app
from sanic import Sanic
from functools import partial
from sanic.worker.loader import AppLoader
def main():
    loader = AppLoader(factory = partial(get_app))
    app = loader.load()
    app.config.REQUEST_TIMEOUT = 300  
    app.config.RESPONSE_TIMEOUT = 300  
    app.config.KEEP_ALIVE_TIMEOUT = 300 
    workers = 1  # Changed from 2 to 1 to avoid async context issues
    debug = True
    app.prepare('0.0.0.0', 3000, debug=debug, workers=workers)
    Sanic.serve(primary=app, app_loader=loader)
if __name__ == "__main__":
    load_dotenv()
    main()
    