import pathlib
import subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import psycopg
from dotenv import load_dotenv
import os
import unicodedata
import requests
import sys
import psutil
import docker


load_dotenv()
app = FastAPI()
client = docker.from_env()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

launching_services_api = {
    "crawler": False,
    "parser": False,
    "indexer": False
}

class SearchRequest(BaseModel):
    query: str
    n_results: int

class ServiceRequest(BaseModel):
    name: str


def __normalize(text):
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

@app.post("/search")
def search(request: SearchRequest):
    # Get query and numbers of results expected
    query = request.query.split()
    query = [__normalize(term.lower()) for term in query]
    n_results = request.n_results

    # Build SQL query
    sql_query = ["SELECT page_id FROM inverted_index WHERE word = %s" for _ in query]
    sql_query = " INTERSECT ".join(sql_query)

    # Get results
    db = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    with db.cursor() as db_cursor:
        if n_results != -1:
            db_cursor.execute(f"""
                SELECT inverted_index.url, inverted_index.title, 0.7*LOG(tf_idf + 1) + 0.3*LOG(page_rank + 1) AS score
                FROM inverted_index JOIN page_informations USING (url)
                WHERE word in ({', '.join([f"'{term}'" for term in query])})
                AND page_id IN (
                    {sql_query}
                )
                GROUP BY inverted_index.page_id, inverted_index.title, inverted_index.url, inverted_index.tf_idf, page_informations.page_rank
                ORDER BY SUM(0.7*LOG(tf_idf + 1)) + 0.3*LOG(MAX(page_rank) + 1) DESC
                LIMIT %s
                """, tuple(query + [n_results])
            )

        else:
            db_cursor.execute(f"""
                SELECT inverted_index.url, inverted_index.title, 0.7*LOG(tf_idf + 1) + 0.3*LOG(page_rank + 1) AS score
                FROM inverted_index JOIN page_informations USING (url)
                WHERE word in ({', '.join([f"'{term}'" for term in query])})
                AND page_id IN (
                    {sql_query}
                )
                GROUP BY inverted_index.page_id, inverted_index.title, inverted_index.url, inverted_index.tf_idf, page_informations.page_rank
                ORDER BY SUM(0.7*LOG(tf_idf + 1)) + 0.3*LOG(MAX(page_rank) + 1) DESC
                """, tuple(query)
            )

        results = db_cursor.fetchall()

    # Send results
    results_ = [{"title": title, "url": url} for url, title, _ in results]
    return {"results": results_}

@app.post("/get-status")
def get_status(service: ServiceRequest):
    service_name = service.name.lower()

    # Check if API is in docker
    if pathlib.Path("/.dockerenv").exists():
        print("Dans Docker !")
        try:
            response = requests.get(
                f"http://{os.getenv(f"{service_name.upper()}_API_HOST")}:{os.getenv(f"{service_name.upper()}_API_PORT")}/get-status"
            )
            if response.status_code < 500:
                status = response.json()["status"]
                if launching_services_api[service_name]:
                    launching_services_api[service_name] = False
                return {"response": f"{service_name} is {status}.", "status": status}

            else:
                if launching_services_api[service_name]:
                    return {"response": f"{service_name} is launching.", "status": "Launching"}
                else:
                    return {"response": f"{service_name} is stopped.", "status": "Stopped"}

        except requests.RequestException:
            if launching_services_api[service_name]:
                return {"response": f"{service_name} is launching.", "status": "Launching"}
            else:
                return {"response": f"{service_name} is stopped.", "status": "Stopped"}

    else:
        service_script_path = pathlib.Path(f"../core/{service_name}/main.py").absolute()
        # Check if service is online
        if sys.platform == "win32":
            api_launched = any(
                str(service_script_path) in " ".join(p.info["cmdline"] or [])
                for p in psutil.process_iter(["cmdline"])
            )

        else:
            result = subprocess.run(["pgrep", "-f", "python main.py"], capture_output=True)
            api_launched = result.returncode == 0

        if api_launched:
            # Pause service
            try:
                response = requests.get(
                    f"http://{os.getenv(f"{service_name.upper()}_API_HOST")}:{os.getenv(f"{service_name.upper()}_API_PORT")}/get-status"
                )
                status = response.json()["status"]
                return {"response": f"{service_name} is {status}", "status": status}

            except requests.RequestException:
                return {"response": f"Failed to pause {service_name}'s API", "status": "Running"}

        else:
            return {"response": f"{service_name}.s are not running", "status": "Stopped"}

@app.post("/run")
def run(service: ServiceRequest):
    service_name = service.name.lower()

    # Check if service is online
    api_launched = get_status(service=service)["status"] not in ("Stopped", "Launching")
    if api_launched:
        print("API is already running")
        return {"response": f"API is already running"}

    else:
        # Detect if api is in container
        if pathlib.Path("/.dockerenv").exists():
            print("DOCKERENV")
            # Dans un container docker
            # print("Dans Docker !")
            # return {"response": "Dans Docker !", "status": "Stopped"}
            try:
                filters = {
                    "label": f"com.docker.compose.service={service_name}"
                }
                containers = client.containers.list(all=True, filters=filters)
                if containers:
                    containers[0].start()

                else:
                    return {"response": f"Failed to start {service_name}'s API", "status": "Stopped"}
            except Exception:
                return {"response": f"Failed to start {service_name}'s API", "status": "Stopped"}

        else:
            # Hors d'un container docker
            service_script_path = pathlib.Path(f"../core/{service_name}/main.py").absolute()
            # service_script_path_ = str(service_script_path).replace("\\", "\\\\")

            # Launch API
            # Get Venv's python
            if sys.platform == "win32":
                venv_python = pathlib.Path(service_script_path.parent, ".venv", "Scripts", "python.exe").absolute()

            else:
                venv_python = pathlib.Path(service_script_path.parent, ".venv", "Scripts", "python").absolute()

            result = subprocess.Popen([str(venv_python), str(service_script_path)])

        launching_services_api[service_name] = True
        return {"response": f"Launching {service_name}'s API", "status": "Launching"}

        setInte


        # # Start service
        # try:
        #     response = requests.get(f"http://{os.getenv(f"{service_name.upper()}_API_HOST")}:{os.getenv(f"{service_name.upper()}_API_PORT")}/start")
        #     if response.json()["status"] != "Running":
        #         return {"response": f"Failed to start {service_name}'s API"}
        #
        # except requests.RequestException:
        #     return {"response": f"Failed to start {service_name}'s API"}
        #
        # print("caca")
        # return {"response": f"Started {service_name}'s API", "status": "Running"}

def _start_service(service_name: str):
    try:
        response = requests.get(
            f"http://{os.getenv(f"{service_name.upper()}_API_HOST")}:{os.getenv(f"{service_name.upper()}_API_PORT")}/start")
        if response.json()["status"] != "Running":
            return {"response": f"Failed to start {service_name}'s API", "status": "Paused"}

        else:
            return {"response": f"Started {service_name}", "status": "Running"}

    except requests.RequestException:
        return {"response": f"Failed to start {service_name}'s API", "status": "Paused"}

@app.post("/start")
def start(service: ServiceRequest, check_status: bool = True):
    service_name = service.name.lower()
    service_script_path = pathlib.Path(f"../core/{service_name}/main.py").absolute()

    # Check if service is online
    api_launched = get_status(service=service)["status"] != "Stopped"

    if api_launched:
        # Start service
        return _start_service(service_name=service_name)
    
    else:
        return {"response": f"{service_name}.s are not running", "status": "Stopped"}


@app.post("/pause")
def pause(service: ServiceRequest):
    service_name = service.name.lower()
    service_script_path = pathlib.Path(f"../core/{service_name}/main.py").absolute()

    # Check if service is online
    api_launched = get_status(service=service)["status"] != "Stopped"

    if api_launched:
        # Pause service
        try:
            response = requests.get(
                f"http://{os.getenv(f"{service_name.upper()}_API_HOST")}:{os.getenv(f"{service_name.upper()}_API_PORT")}/pause")
            if response.json()["status"] != "Paused":
                return {"response": f"Failed to pause {service_name}'s API", "status": "Running"}

            else:
                return {"response": f"Paused {service_name}", "status": "Paused"}

        except requests.RequestException:
            return {"response": f"Failed to pause {service_name}'s API", "status": "Running"}

    else:
        return {"response": f"{service_name}.s are not running", "status": "Stopped"}

@app.post("/stop")
def stop(service: ServiceRequest):
    service_name = service.name.lower()
    service_script_path = pathlib.Path(f"../core/{service_name}/main.py").absolute()

    # Check if service is online
    api_launched = get_status(service=service)["status"] != "Stopped"

    if api_launched:
        # Stop service
        try:
            response = requests.get(
                f"http://{os.getenv(f"{service_name.upper()}_API_HOST")}:{os.getenv(f"{service_name.upper()}_API_PORT")}/stop")
            if response.json()["status"] != "Stopped":
                return {"response": f"Error when stopping {service_name}'s API", "status": "Stopped"}

            else:
                return {"response": f"Stopped {service_name}", "status": "Stopped"}

        except requests.RequestException:
            return {"response": f"Failed to stop {service_name}'s API", "status": "Stopped"}

    else:
        return {"response": f"{service_name}.s are already stopped", "status": "Stopped"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=os.getenv("HOST"), port=int(os.getenv("PORT")))
