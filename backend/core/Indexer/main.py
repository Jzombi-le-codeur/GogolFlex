import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from index import Indexer
import asyncio
import time
import signal
import pathlib


load_dotenv(
    dotenv_path=pathlib.Path(__file__).parent / ".env",
    encoding="utf-8",
    override=True
)

app = FastAPI()
app.state.indexer = Indexer()
app.state.indexer_running = False

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def main():
    return {"response": "Welcome to indexer's API"}

@app.get("/get-status")
def get_status():
    if app.state.indexer_running:
        return {"response": "Indexer.s are running", "status": "Running"}

    else:
        return {"response": "No indexer is running", "status": "Paused"}

@app.get("/start")
async def start():
    if not app.state.indexer_running:
        app.state.indexer.running = True
        app.state.indexer_running = True
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, app.state.indexer.run)
        return {"response": "Launched indexer", "status": "Running"}
    else:
        return {"response": "Indexer already running", "status": "Running"}

@app.get("/pause")
def pause():
    if app.state.indexer_running:
        app.state.indexer.running = False
        app.state.indexer_running = False
        return {"response": "Indexers paused", "status": "Paused"}
    else:
        return {"response": "No indexer is running", "status": "Paused"}

@app.get("/stop")
def stop(background_task: BackgroundTasks):
    pause()
    background_task.add_task(lambda: (time.sleep(0.5), os.kill(os.getpid(), signal.SIGTERM)))
    return {"response": "API Stopped", "status": "Stopped"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST"), port=int(os.getenv("PORT")))
