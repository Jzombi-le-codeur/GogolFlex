from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import psycopg
from dotenv import load_dotenv
import os
import unicodedata


load_dotenv()
app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    n_results: int


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

if __name__ == "__main__":
    uvicorn.run("main:app", host=os.getenv("HOST"), port=int(os.getenv("PORT")), reload=True)
