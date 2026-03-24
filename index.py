import pathlib
import sqlite3
import time
from bs4 import BeautifulSoup
import re


class Indexer:
    def __init__(self):
        self.pages_informations = []
        self.page_informations = {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_text = str()
        self.frequencies = dict()

    def init(self):
        db = sqlite3.connect("index.db")
        db.execute("""
        CREATE TABLE IF NOT EXISTS inverted_index (
            word TEXT,
            page_id INTEGER,
            url TEXT,
            title TEXT,
            tf REAL
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS term_documents (
            word TEXT PRIMARY KEY,
            documents_number INTEGER
        )
        """)
        db.commit()
        db.close()

    def __get_pages_informations(self):
        # Get datas
        db = sqlite3.connect("parse.db")
        db_cursor = db.cursor()
        pages_informations = list()
        while not pages_informations:
            db_cursor.execute("SELECT id, url, page_filename, title FROM page_informations ORDER BY id LIMIT 10")
            pages_informations = db_cursor.fetchall()
            if not pages_informations:
                time.sleep(1)

        db.close()

        for page_infos in pages_informations:
            page_informations = dict()
            page_informations["id"], page_informations["url"], page_informations["page_filename"], \
                page_informations["title"] = page_infos
            self.pages_informations.append(page_informations)

    def __get_page_code(self):
        # Get page code
        page_path = pathlib.PurePath("Pages", self.page_informations["page_filename"][:2],
                                     self.page_informations["page_filename"])
        print(page_path)
        with open(page_path, "r", encoding="utf-8") as page_file:
            page_code = BeautifulSoup(page_file.read(), features="html.parser")

        # Just get body and title's text
        self.page_text = page_code.find("title").get_text() + page_code.find("body").get_text()

    def __count_words(self):
        # Tokenize page text
        self.page_text = re.sub(r"[’'/\-,!?.*()]", " ", self.page_text)  # Remove some symbols from text
        tokens = self.page_text.split()  # Tokenize

        # Get word's frequencies in page
        for token in tokens:
            token = token.lower()
            if not token in self.frequencies.keys():
                self.frequencies[token] = 1

            else:
                self.frequencies[token] += 1

    def __save_page_informations(self):
        db = sqlite3.connect("index.db")
        for token in self.frequencies.keys():
            # Save page's TF
            print(self.page_informations)
            db.execute("INSERT INTO inverted_index (word, page_id, url, title, tf) VALUES (?, ?, ?, ?, ?)", (
                token,
                self.page_informations["id"],
                self.page_informations["url"],
                self.page_informations["title"],
                self.frequencies[token] / len(self.frequencies.keys()),
            ))

            # Update the number of pages with this word
            db.execute("""INSERT INTO term_documents (word, documents_number) VALUES (?, 1)
            ON CONFLICT(word) DO UPDATE SET documents_number = documents_number + 1""", (
                token,
            ))

        # Update the total number of pages
        db.execute("""INSERT INTO term_documents (word, documents_number) VALUES ('', 1)
        ON CONFLICT(word) DO UPDATE SET documents_number = documents_number + 1""")

        db.commit()
        db.close()

    def run(self):
        self.init()
        for _ in range(3):
            if not self.pages_informations:
                self.__get_pages_informations()

            self.page_informations = self.pages_informations.pop(0)
            self.__get_page_code()
            self.__count_words()
            self.__save_page_informations()


indexer = Indexer()
indexer.run()
