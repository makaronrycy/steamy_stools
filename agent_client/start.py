
import asyncio
from dotenv import load_dotenv
from src import get_app
from sanic import Sanic
from functools import partial
from sanic.worker.loader import AppLoader
from sanic.worker.manager import WorkerManager
import os
def main():
    loader = AppLoader(factory = partial(get_app))
    app = loader.load()
    workers = 2
    debug =True
    app.prepare('0.0.0.0', 3000, debug=debug, workers=workers)
    Sanic.serve(primary=app, app_loader=loader)
if __name__ == "__main__":
    load_dotenv()
    main()
    