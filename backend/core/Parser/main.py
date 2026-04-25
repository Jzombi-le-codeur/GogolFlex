import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from parser import Parser
import asyncio


load_dotenv(encoding="utf-8")

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

@app.get("/start")
async def start():
    if not app.state.parser_running:
        app.state.parser.running = True
        app.state.parser_running = True
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, app.state.parser.run)
        return {"response": "Launched parser"}
    else:
        return {"response": "Parser already running"}

@app.get("/stop")
def stop():
    if app.state.parser_running:
        app.state.parser.running = False
        app.state.parser_running = False
        return {"response": "parsers stopped"}
    else:
        return {"response": "No parser is running"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST"), port=int(os.getenv("PORT")))
