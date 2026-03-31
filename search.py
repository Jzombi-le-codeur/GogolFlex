import sqlite3


class Searcher:
    def __init__(self):
        self.results = []  # {"title": title, "url": url}

    def __search(self, query: str, n_results: int):
        # Split query into many terms
        query = query.split()

        # Connect to database
        db = sqlite3.connect("index.db")
        db_cursor = db.cursor()

        # Build SQL query
        sql_query = ["SELECT page_id FROM inverted_index WHERE word = ?" for _ in query]
        sql_query = " INTERSECT ".join(sql_query)

        # Get results
        db_cursor.execute(f"""
        SELECT title, url, SUM(tf_idf) as score 
        FROM inverted_index 
        WHERE word in ({', '.join([f"'{term}'" for term in query])})
        AND page_id IN (
            {sql_query}
        )
        GROUP BY page_id
        ORDER BY score DESC
        LIMIT ?
        """, tuple(query + [n_results]))
        results = db_cursor.fetchall()
        for title, url, _ in results:
            self.results.append({"title": title, "url": url})

        db.close()

    def __display_results(self):
        print(f"{len(self.results)} RESULTATS")
        for result in self.results:
            print(f"Page : {result['title']}\n> {result['url']}")
            print("--------------------")

    def search(self, n_results: int):
        query = input("> ")
        self.__search(query=query, n_results=n_results)
        self.__display_results()


searcher = Searcher()
searcher.search(20)
