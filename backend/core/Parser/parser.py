import time
from bs4 import BeautifulSoup
import pathlib
import psycopg
import os
from dotenv import load_dotenv


class Parser:
    def __init__(self):
        # Parser's informations
        load_dotenv(encoding="utf-8")
        self.db_timeout = 30
        self.pages_informations = []  # {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_informations = {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_code = BeautifulSoup()
        self.running = False

        # DBs
        self.db = psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

        # Paths
        self.datas_path = pathlib.PurePath(os.getenv("DATAS_PATH"))
        self.pages_path = pathlib.Path(self.datas_path, pathlib.Path("Pages"))
        self.robots_txt_path = pathlib.Path(self.datas_path, pathlib.Path("RobotsTXT"))

    def init(self):
        with self.db.cursor() as db_cursor:
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_informations (
                id SERIAL PRIMARY KEY,
                url TEXT,
                page_filename TEXT,
                title TEXT,
                indexed INTEGER,
                page_rank REAL
            )
            """)
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_informations_url ON page_informations(url)")

    def __get_crawl_results(self):
        # Get visited_urls datas
        with self.db.cursor() as db_cursor:
            pages_informations = list()
            while not self.pages_informations:
                db_cursor.execute("SELECT id, url, indexation, page_filename FROM visited_urls WHERE parsed=0 ORDER BY id LIMIT 10")
                pages_informations = db_cursor.fetchall()

                for page_infos in pages_informations:
                    # Get informations
                    if bool(page_infos[2]):
                        page_informations = {}
                        page_informations["id"] = page_infos[0]
                        page_informations["url"] = page_infos[1]
                        page_informations["page_filename"] = page_infos[3]
                        self.pages_informations.append(page_informations)

                    else:
                        db_cursor.execute("UPDATE visited_urls SET parsed=1 WHERE id=%s", (page_infos[0],))

                if not pages_informations:
                    time.sleep(1)

    def __get_page_code(self):
        # Get page code
        page_filepath = pathlib.PurePath(self.pages_path, self.page_informations["page_filename"][:2],
                                         self.page_informations["page_filename"])
        with open(page_filepath, encoding="utf-8") as page_file:
            self.page_code = BeautifulSoup(page_file.read(), features="html.parser")

    def __get_page_title(self):
        # Find page title

        # Try to get <title> tag
        if not self.page_code.find("title"):
            title = ""

        else:
            title = self.page_code.find("title").text.strip()

        if title:
            # Save title
            self.page_informations["title"] = title

        else:
            # Try to get <meta property="og:title">
            if not title:
                title = self.page_code.find("meta", attrs={"property": "og:title"})

            # Try to get <meta name="twitter:title">
            if not title:
                title = self.page_code.find("meta", attrs={"name": "twitter:title"})

            # Get meta title content
            if title:
                title = title["content"]

            else:
                # Try to get h1-6 tag
                for i in range(1, 7):
                    title = self.page_code.find(f"h{i}")
                    if title:
                        title = title.text
                        break

            # Get title by URL
            if not title:
                title = self.page_informations["url"].split("/")[-1]
                if "." in title:
                    title = title.split(".")
                    if len(title) == 2:
                        title = title[0]

                    else:
                        title = ".".join(title[0:-1])

        # Save URL in page_informations
        self.page_informations["title"] = title.strip()

    def __is_page_in_db(self):
        with self.db.cursor() as db_cursor:
            db_cursor.execute("SELECT url FROM page_informations WHERE url = %s", (self.page_informations["url"],))
            res = db_cursor.fetchone()
            print(res)
        return True if res else False

    def __save_datas(self):
        # Mark page as parsed
        with self.db.cursor() as db_cursor:
            db_cursor.execute("UPDATE visited_urls SET parsed=1 WHERE id=%s", (self.page_informations["id"],))
            self.db.commit()

        # Save informations
        if not self.__is_page_in_db():
            with self.db.cursor() as db_cursor:
                db_cursor.execute("INSERT INTO page_informations (url, page_filename, title, indexed) VALUES (%s, %s, %s, %s)", (
                    self.page_informations["url"],
                    self.page_informations["page_filename"],
                    self.page_informations["title"],
                    0,
                ))
                self.db.commit()

        else:
            print("DEJA DEDANS")

    def __run(self):
        # Get basic pages' information (url, index, pagepath)
        if not self.pages_informations and self.running:
            self.__get_crawl_results()

        if not self.running:
            return

        # Get page's informations
        self.page_informations = self.pages_informations.pop(0)

        print(self.page_informations)

        # Get page code
        self.__get_page_code()

        # Get page title
        self.__get_page_title()

        # Save informations
        self.__save_datas()

    def run(self, i: int = 0):
        try:
            # Initialize database
            self.init()

            if i == 0:
                while self.running:
                    self.__run()

            else:
                for _ in range(i):
                    if self.running:
                        self.__run()

                    else:
                        break

        finally:
            self.db.close()


if __name__ == "__main__":
    parser = Parser()
    parser.run()