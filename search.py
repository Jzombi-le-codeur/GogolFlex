import sqlite3


class Searcher:
    def __init__(self):
        self.results = []  # {"title": title, "url": url}

    def __search(self, query: str, n_results: int):
        # (only work for 1 word in query)

        # Connect to database
        db = sqlite3.connect("index.db")
        db_cursor = db.cursor()

        # Search term
        db_cursor.execute("SELECT title, url FROM inverted_index WHERE word = ? ORDER BY tf_idf DESC LIMIT ?", (
            query,
            n_results,
        ))
        results = db_cursor.fetchall()
        for title, url in results:
            self.results.append({"title": title, "url": url})

    def __display_results(self):
        print(f"{len(self.results)} RESULTATS")
        for result in self.results:
            print(f"Page : {result['title']}\n> {result['url']}")
            print("--------------------")

    def search(self, query: str, n_results: int):
        self.__search(query=query, n_results=n_results)
        self.__display_results()


searcher = Searcher()
searcher.search("don", 20)
