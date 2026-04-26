import selectors
import asyncio
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from crawler import Crawler
from dotenv import load_dotenv

load_dotenv(encoding="utf-8")

app = FastAPI()
app.state.crawler = Crawler()
app.state.crawler_running = False

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Queue(BaseModel):
    queue: list[str]

@app.get("/")
def main():
    return {"response": "Welcome to the Crawler's API"}

@app.post("/set-queue")
def set_queue(payload: Queue):
    if not app.state.crawler_running:
        for url in payload.queue:
            app.state.crawler.queue.put_nowait(url)
        return {"response": "Queue set"}
    else:
        return {"response": "Can't change queue when crawlers are running"}

@app.get("/start")
async def start():
    print("test")
    if not app.state.crawler_running:
        app.state.crawler.running = True
        app.state.crawler_running = True
        asyncio.create_task(app.state.crawler.run(n_crawlers=5))
        return {"response": "Launched crawlers"}
    else:
        return {"response": "Crawlers are already running"}

@app.get("/stop")
def stop():
    if app.state.crawler_running:
        app.state.crawler.running = False
        app.state.crawler_running = False
        return {"response": "Crawlers stopped"}
    else:
        return {"response": "No crawler is running"}


if __name__ == "__main__":
    if sys.platform == "win32":
        import selectors

        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(loop)

    config = uvicorn.Config(
        app,
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT")),
    )
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        loop.run_until_complete(server.serve())
    else:
        server.run()
