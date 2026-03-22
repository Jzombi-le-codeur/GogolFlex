import pathlib
import sqlite3
from bs4 import BeautifulSoup
import re


class Indexer:
    def __init__(self):
        self.page_informations = {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_text = str()
        self.frequencies = dict()

    def init(self):
        db = sqlite3.connect("index.db")
        db.execute("""
        CREATE TABLE IF NOT EXISTS page_informations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            title TEXT,
            total_words INTEGER
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS inverted_index (
            word TEXT,
            page_id INTEGER,
            frequency INTEGER
        )
        """)
        db.commit()
        db.close()

    def __get_page_content(self):
        # Get datas
        db = sqlite3.connect("parse.db")
        db_cursor = db.cursor()
        db_cursor.execute("SELECT id, url, page_filename, title FROM page_informations ORDER BY id LIMIT 1")
        self.page_informations["id"], self.page_informations["url"], self.page_informations["page_filename"], self.page_informations["title"] = db_cursor.fetchone()
        db.close()

        # Get page code
        page_path = pathlib.PurePath("Pages", self.page_informations["page_filename"][:2], self.page_informations["page_filename"])
        with open(page_path, "r", encoding="utf-8") as page_file:
            page_code = BeautifulSoup(page_file.read(), features="html.parser")

        # Just get body and title's text
        self.page_text = page_code.find("title").get_text() + page_code.find("body").get_text()

    def __count_words(self):
        # Tokenize page text
        self.page_text = re.sub(r"['\-,!?.*]", " ", self.page_text)  # Remove some symbols from text
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
        db.execute("INSERT INTO page_informations (id, url, title, total_words) VALUES (?, ?, ?, ?)", (
            self.page_informations["id"],
            self.page_informations["url"],
            self.page_informations["title"],
            len(self.frequencies.keys()),
        ))
        db.commit()
        db.close()

    def __save_frequencies(self):
        db = sqlite3.connect("index.db")
        for token in self.frequencies.keys():
            db.execute("INSERT INTO inverted_index (word, page_id, frequency) VALUES (?, ?, ?)", (
                token,
                self.page_informations["id"],
                self.frequencies[token],
            ))

        db.commit()
        db.close()

        print(sum(self.frequencies.values()))

    def run(self):
        self.init()
        self.__get_page_content()
        self.__count_words()
        self.__save_page_informations()
        self.__save_frequencies()


indexer = Indexer()
indexer.run()
