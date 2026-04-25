import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from index import Indexer
import asyncio


load_dotenv(encoding="utf-8")

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

@app.get("/start")
async def start():
    if not app.state.indexer_running:
        app.state.indexer.running = True
        app.state.indexer_running = True
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, app.state.indexer.run)
        return {"response": "Launched indexer"}
    else:
        return {"response": "indexer already running"}

@app.get("/stop")
def stop():
    if app.state.indexer_running:
        app.state.indexer.running = False
        app.state.indexer_running = False
        return {"response": "indexers stopped"}
    else:
        return {"response": "No indexer is running"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST"), port=int(os.getenv("PORT")))
