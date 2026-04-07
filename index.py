import pathlib
import sqlite3
import time
from bs4 import BeautifulSoup
import re
import math


class Indexer:
    def __init__(self):
        self.db_timeout = 30
        self.pages_informations = []
        self.page_informations = {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_text = str()
        self.frequencies = dict()

    def init(self):
        db = sqlite3.connect("index.db", timeout=self.db_timeout)
        db.execute("""
        CREATE TABLE IF NOT EXISTS inverted_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            page_id INTEGER,
            url TEXT,
            title TEXT,
            tf REAL,
            tf_idf REAL
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
        db = sqlite3.connect("parse.db", timeout=self.db_timeout)
        db_cursor = db.cursor()
        pages_informations = list()
        i = 0
        while not pages_informations and i < 400:
            db_cursor.execute("SELECT id, url, page_filename, title FROM page_informations WHERE indexed = 0 ORDER BY id LIMIT 10")
            pages_informations = db_cursor.fetchall()
            if not pages_informations:
                i += 1
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
        with open(page_path, "r", encoding="utf-8") as page_file:
            page_code = BeautifulSoup(page_file.read(), features="html.parser")

        # Just get body and title's text
        self.page_text = page_code.find("title").get_text() + page_code.find("body").get_text()

    def __count_words(self):
        self.frequencies = {}
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
        db = sqlite3.connect("index.db", timeout=self.db_timeout)
        for token in self.frequencies.keys():
            # Save page's TF
            db.execute("INSERT INTO inverted_index (word, page_id, url, title, tf) VALUES (?, ?, ?, ?, ?)", (
                token,
                self.page_informations["id"],
                self.page_informations["url"],
                self.page_informations["title"],
                self.frequencies[token] / sum(self.frequencies.values()),
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

        # Mark page as indexed
        db = sqlite3.connect("parse.db", timeout=self.db_timeout)
        db.execute("UPDATE page_informations SET indexed = 1 WHERE id = ?", (self.page_informations["id"],))
        db.commit()
        db.close()

    def calculate_tf_idf(self):
        # Connect to database
        db = sqlite3.connect("index.db", timeout=self.db_timeout)
        db_cursor = db.cursor()

        # Check queue
        i = 1
        n_pages_to_get = 20
        db_cursor.execute("SELECT MAX(id) from inverted_index")
        max_i = db_cursor.fetchone()[0]
        db_cursor.execute("SELECT documents_number FROM term_documents WHERE word = ''")
        total_documents_number = db_cursor.fetchone()[0]

        # Calculate tf-idf score of each word
        while i <= max_i:
            print(f"I : {i}\nMaxI : {max_i}")
            # Get TF's words
            db_cursor.execute("SELECT word, tf FROM inverted_index WHERE id >= ? AND id < ? ORDER BY id", (
                i,
                i+n_pages_to_get,
            ))
            word_tfs = db_cursor.fetchall()

            # Get list of document's number with word in
            words = [w for w, _ in word_tfs]
            db_cursor.execute(f"SELECT word, documents_number FROM term_documents WHERE word IN ({','.join(['?']*len(words))})", words)
            documents_number_with_words = dict(db_cursor.fetchall())

            # Calculate tf idf
            tf_idfs = list()
            local_i = 0
            for word, tf in word_tfs:
                # Calculate IDF
                documents_number_with_word = documents_number_with_words[word]
                print(f"Total_documents_number : {total_documents_number}\nDocuments_number_with_words : {documents_number_with_word}")
                print("-----")
                idf = math.log(total_documents_number/documents_number_with_word)

                # Calculate tf_idf
                tf_idf = tf*idf
                print(f"Word : {word}\nTF : {tf}\nIDF : {idf}\nTF-IDF : {tf_idf}")
                print("----------")

                # Update
                tf_idfs.append((tf_idf, i+local_i))
                local_i += 1

            # Save TF-IDF
            db_cursor.executemany("UPDATE inverted_index SET tf_idf = ? WHERE id = ?", tf_idfs)
            db.commit()
            print("Ajouté")

            i += n_pages_to_get
            print("-------------------------------------------")
            # input("")

        # Close database
        db.close()

    def __run(self):
        if not self.pages_informations:
            self.__get_pages_informations()

        self.page_informations = self.pages_informations.pop(0)
        self.__get_page_code()
        self.__count_words()
        self.__save_page_informations()

        print("Site traité")
        print("---------------------------------------------------------------------------------------------")

    def run(self, i_bfr_tf_idf: int = 10, i: int = 0):
        self.init()

        if i == 0:
            running = True
            j = 0
            while running:
                j += 1
                self.__run()
                if j%i_bfr_tf_idf == 0:
                    self.calculate_tf_idf()

        else:
            j = 0
            for _ in range(i):
                j += 1
                self.__run()
                if j % i_bfr_tf_idf == 0:
                    self.calculate_tf_idf()


if __name__ == "__main__":
    indexer = Indexer()
    indexer.calculate_tf_idf()
