import datetime
import json
import pathlib
import secrets
import subprocess
import argon2.exceptions
from fastapi import FastAPI, Response, Cookie
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
from argon2 import PasswordHasher
import jwt


load_dotenv()
app = FastAPI()
if pathlib.Path("/.dockerenv").exists():
    client = docker.from_env()
db = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)
ph = PasswordHasher()
secret_key = os.getenv("SECRET_KEY")

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

class LoginRequest(BaseModel):
    username: str
    password: str

class AccessTokenRequest(BaseModel):
    access_token: str

class RoleRequest(BaseModel):
    access_token: str

class LogoutRequest(BaseModel):
    username: str

class ServiceRequest(BaseModel):
    name: str


def __normalize(text):
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def init():
    with open("save.json") as save:
        save = json.load(save)

    if save["firstUse"]:
        db_cursor = db.cursor()

        # Create tables
        db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """)
        db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id SERIAL PRIMARY KEY,
            username TEXT,
            token TEXT,
            expiration TIMESTAMP
        )
        """)

        # Save admin's IDs
        password = os.getenv("ADMIN_PASSWORD")
        password = ph.hash(password)
        db_cursor.execute("""
        INSERT INTO users (username, password, role) VALUES (%s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """, ("admin", password, "admin",))
        db.commit()


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

def __generate_token(token_type: str, username: str):
    # Generate token
    if token_type == "access":
        payload = {
            "username": username,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        }

        # Generate token
        token = jwt.encode(
            payload=payload,
            key=secret_key,
            algorithm="HS256"
        )

    else:
        token = secrets.token_hex(64)

    # Save refresh token
    if token_type == "refresh":
        db_cursor = db.cursor()
        db_cursor.execute(
            "INSERT INTO refresh_tokens (username, token, expiration) VALUES (%s, %s, %s)",
            (username, token, datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7))
        )
        db.commit()

    return token

@app.post("/login")
def login(ids: LoginRequest, response: Response):
    # Get IDs
    username = ids.username
    password = ids.password

    db_cursor = db.cursor()

    # Check if username exists in DB
    db_cursor.execute("""
    SELECT username, password FROM users WHERE username=%s
    """, (username,))
    real_ids = db_cursor.fetchone()
    if not real_ids:
        return {"response": "This user doesn't exist.", "status": "NotExists"}

    # Check if password is correct
    try:
        ph.verify(real_ids[1], password)

        # Delete all expired tokens
        db_cursor.execute("""
        DELETE FROM refresh_tokens
        WHERE username=%s;
        """, (username,))

        # Generate refresh token
        response.set_cookie(
            key="refresh_token",
            value=__generate_token(token_type="refresh", username=username),
            httponly=True,
            samesite="strict",
            max_age=7*24*3600
        )

        return {
            "response": "Connected !",
            "status": "Connected",
            "accessToken": __generate_token(token_type="access", username=username)
        }

    except argon2.exceptions.VerifyMismatchError:
        return {"response": "Password is false", "status": "Incorrect"}

def get_role(username: str):
    # Get user's role
    db_cursor = db.cursor()
    db_cursor.execute("""
        SELECT role FROM users WHERE username = %s
        """, (username,))
    role = db_cursor.fetchone()[0]

    return role


def handle_refresh_token(refresh_token: str):
    # Check if refresh token is valid
    db_cursor = db.cursor()

    # Get username
    db_cursor.execute("""
    SELECT username FROM refresh_tokens WHERE token = %s AND expiration > NOW()
    """, (refresh_token,))
    username_response = db_cursor.fetchone()
    print("username response :", username_response)
    if not username_response:
        return {"response": "This token is expired", "status": "Disconnected"}

    username = username_response[0]

    # Get user's role
    role = get_role(username=username)

    return {
        "response": "Token is valid",
        "role": role,
        "status": "Connected",
        "accessToken": __generate_token(token_type="access", username=username)
    }

@app.post("/check-token")
def check_token(token_request: AccessTokenRequest, refresh_token: str = Cookie(None)):
    access_token = token_request.access_token

    # Check if token has been sent
    if not access_token:
        if not refresh_token:
            return {"response": "No token has been receipted", "status": "Disconnected"}

        else:
            # Check if refresh token is valid
            return handle_refresh_token(refresh_token=refresh_token)

    # Check token
    try:
        payload = jwt.decode(access_token, key=secret_key, algorithms=["HS256"])
        return {"response": "Token is valid", "status": "Connected", "role": get_role(username=payload["username"])}

    except jwt.ExpiredSignatureError:
        return handle_refresh_token(refresh_token=refresh_token)

    except jwt.InvalidTokenError:
        return {"response": "This token is invalid", "status": "Disconnected"}

@app.post("/logout")
def logout(logout_request: LogoutRequest, response: Response):
    # Get username
    username = logout_request.username

    # Delete refresh token cookie
    response.delete_cookie(
        key="refresh_token"
    )

    # Delete refresh token in DB
    db_cursor = db.cursor()
    db_cursor.execute("""
    DELETE FROM refresh_tokens
    WHERE username=%s;
    """, (username,))

    return {"response": "Successfuly disconnected !", "status": "Disconnected"}

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
    try:
        init()
        uvicorn.run("main:app", host=os.getenv("HOST"), port=int(os.getenv("PORT")))

    finally:
        db.close()
