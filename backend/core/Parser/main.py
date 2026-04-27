import os
import time
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from parser import Parser
import asyncio
import signal
import pathlib


load_dotenv(
    dotenv_path=pathlib.Path(__file__).parent / ".env",
    encoding="utf-8",
    override=True
)

app = FastAPI()
app.state.parser = Parser()
app.state.parser_running = False

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
    return {"response": "Welcome to Parser's API"}

@app.get("/get-status")
def get_status():
    if app.state.parser_running:
        return {"response": "Parser.s are running", "status": "Running"}

    else:
        return {"response": "No parser is running", "status": "Paused"}

@app.get("/start")
async def start():
    if not app.state.parser_running:
        app.state.parser.running = True
        app.state.parser_running = True
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, app.state.parser.run)
        return {"response": "Launched parser", "status": "Running"}
    else:
        return {"response": "Parser.s are already running", "status": "Running"}

@app.get("/pause")
def pause():
    if app.state.parser_running:
        app.state.parser.running = False
        app.state.parser_running = False
        return {"response": "Parser.s paused", "status": "Paused"}
    else:
        return {"response": "No parser is running", "status": "Paused"}

@app.get("/stop")
def stop(background_task: BackgroundTasks):
    pause()
    background_task.add_task(lambda: (time.sleep(0.5), os.kill(os.getpid(), signal.SIGTERM)))
    return {"response": "API Stopped", "status": "Stopped"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST"), port=int(os.getenv("PORT")))
