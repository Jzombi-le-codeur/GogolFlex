import psycopg
from dotenv import load_dotenv
import os
import unicodedata


class Searcher:
    def __init__(self):
        self.results = []  # {"title": title, "url": url}
        load_dotenv(encoding="utf-8")
        self.db = psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    def __normalize(self, text):
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def __search(self, query: str, n_results: int):
        # Split query into many terms
        query = query.split()
        query = [self.__normalize(t.lower()) for t in query]

        # Build SQL query
        sql_query = ["SELECT page_id FROM inverted_index WHERE word = %s" for _ in query]
        sql_query = " INTERSECT ".join(sql_query)

        # Get results
        placeholders = ', '.join(['%s'] * len(query))
        with self.db.cursor() as db_cursor:
            db_cursor.execute(f"""
            SELECT inverted_index.url, inverted_index.title, 0.7*LOG(tf_idf + 1) + 0.3*LOG(page_rank + 1) AS score
            FROM inverted_index JOIN page_informations USING (url)
            WHERE word IN ({placeholders})
            AND page_id IN (
                {sql_query}
            )
            GROUP BY inverted_index.page_id, inverted_index.title, inverted_index.url, inverted_index.tf_idf, page_informations.page_rank
            ORDER BY SUM(0.7*LOG(tf_idf + 1)) + 0.3*LOG(MAX(page_rank) + 1) DESC
            LIMIT %s
            """, tuple(query) + tuple(query) + (n_results,))
            results = db_cursor.fetchall()
            for url, title, _ in results:
                self.results.append({"title": title, "url": url})

    def __display_results(self):
        print(f"{len(self.results)} RESULTATS")
        for result in self.results:
            print(f"Page : {result['title']}\n> {result['url']}")
            print("--------------------")

    def search(self, n_results: int):
        query = input("> ")
        self.__search(query=query, n_results=n_results)
        self.__display_results()
        self.db.close()


searcher = Searcher()
searcher.search(20)
