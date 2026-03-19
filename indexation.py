import sqlite3


class Indexation:
    def __init__(self):
        self.page_informations = {"url": str, "page_filepath": str}

    def __get_crawl_results(self):
        # Get visited_urls datas
        db = sqlite3.connect("crawl.db")
        db_cursor = db.cursor()
        db_cursor.execute("SELECT url, indexation, pagepath FROM visited_urls ORDER BY id LIMIT 1")
        page_informations = db_cursor.fetchone()

        # Get informations
        if bool(page_informations[1]):
            self.page_informations["url"] = page_informations[0]
            self.page_informations["page_filepath"] = page_informations[2]

        db.close()

    def run(self):
        # Get basic page's information (url, index, pagepath)
        self.__get_crawl_results()
        print(self.page_informations)
        # Get website code
        # Get page title & description
        # Add in database


indexation = Indexation()
indexation.run()
