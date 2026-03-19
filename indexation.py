import sqlite3
from bs4 import BeautifulSoup
import pathlib


class Indexation:
    def __init__(self):
        self.page_informations = {"url": str(), "page_filename": str(), "title": str()}
        self.page_code = BeautifulSoup()

    def __get_crawl_results(self):
        # Get visited_urls datas
        db = sqlite3.connect("crawl.db")
        db_cursor = db.cursor()
        db_cursor.execute("SELECT url, indexation, page_filename FROM visited_urls ORDER BY id LIMIT 1")
        page_informations = db_cursor.fetchone()

        # Get informations
        if bool(page_informations[1]):
            self.page_informations["url"] = page_informations[0]
            self.page_informations["page_filepath"] = page_informations[2]

        db.close()

    def __get_page_code(self):
        # Get page code
        page_filepath = pathlib.PurePath("Pages", self.page_informations["page_filepath"][:2], self.page_informations["page_filepath"])
        with open(page_filepath, encoding="utf-8") as page_file:
            self.page_code = BeautifulSoup(page_file.read(), features="html.parser")

    def __get_page_title(self):
        # Find page title

        # Try to get <title> tag
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
                title = self.page_code.find("meta", name="twitter:title")

            # Get meta title content
            if title:
                title = title["content"]

            else:
                # Try to get h1-6 tag
                for i in range(1, 7):
                    title = self.page_code.find(f"h{i}")
                    if title:
                        title = title.text

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

    def run(self):
        # Get basic page's information (url, index, pagepath)
        self.__get_crawl_results()
        self.__get_page_code()
        self.__get_page_title()
        print(self.page_informations.get("title"))
        # Get website code
        # Get page title & description
        # Add in database


indexation = Indexation()
indexation.run()
