from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from crawler import Crawler
from dotenv import load_dotenv
import asyncio
import os


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

class Requests(BaseModel):
    query: str


@app.get("/")
def main():
    return {"response": "Welcome to the Crawler's API"}

@app.get("/start")
async def start():
    if not app.state.crawler_running:
        app.state.crawler.running = True
        app.state.crawler_running = True
        asyncio.create_task(app.state.crawler.run(n_crawlers=5))
        return {"response": "Launched crawler.s"}

    else:
        return {"response": "Crawler.s are already running"}

@app.get("/stop")
def stop():
    if app.state.crawler_running:
        app.state.crawler.running = False
        app.state.crawler_running = False
        return {"response": "Crawler.s stopped"}

    else:
        return {"response": "No crawler is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=os.getenv("HOST"), port=int(os.getenv("PORT")), reload=True)
