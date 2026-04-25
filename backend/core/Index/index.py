import pathlib
import psycopg
import time
from bs4 import BeautifulSoup
import re
import math
from dotenv import load_dotenv
import os
import unicodedata


class Indexer:
    def __init__(self):
        # Indexer's Informations
        load_dotenv(encoding="utf-8")
        self.db_timeout = 30
        self.pages_informations = []
        self.page_informations = {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_text = str()
        self.frequencies = dict()

        # DB
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

    def init(self):
        with self.db.cursor() as db_cursor:
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS inverted_index (
                id SERIAL PRIMARY KEY,
                word TEXT,
                page_id INTEGER,
                url TEXT,
                title TEXT,
                tf REAL,
                tf_idf REAL
            )
            """)
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS term_documents (
                word TEXT PRIMARY KEY,
                documents_number INTEGER
            )
            """)
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_inverted_index_word ON inverted_index(word)")
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_informations_indexed ON page_informations(indexed)")

            self.db.commit()

    def __get_pages_informations(self):
        # Get datas
        with self.db.cursor() as db_cursor:
            pages_informations = list()
            i = 0
            while not pages_informations and i < 400:
                db_cursor.execute("SELECT id, url, page_filename, title FROM page_informations WHERE indexed = 0 ORDER BY id LIMIT 10")
                pages_informations = db_cursor.fetchall()
                if not pages_informations:
                    i += 1
                    time.sleep(1)

        for page_infos in pages_informations:
            page_informations = dict()
            page_informations["id"], page_informations["url"], page_informations["page_filename"], \
                page_informations["title"] = page_infos
            self.pages_informations.append(page_informations)

    def __get_page_code(self):
        # Get page code
        page_path = pathlib.PurePath(self.pages_path, self.page_informations["page_filename"][:2],
                                     self.page_informations["page_filename"])
        with open(page_path, "r", encoding="utf-8") as page_file:
            page_code = BeautifulSoup(page_file.read(), features="html.parser")

        # Just get body and title's text
        title_tag = page_code.find("title")
        body_tag = page_code.find("body")
        self.page_text = title_tag.get_text() if title_tag else "" + body_tag.get_text() if body_tag else ""

    def __normalize(self, text):
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def __count_words(self):
        self.frequencies = {}
        # Tokenize page text
        self.page_text = re.sub(r"[’'/\-,!?.*()]", " ", self.page_text)  # Remove some symbols from text
        tokens = self.page_text.split()  # Tokenize

        # Get word's frequencies in page
        for token in tokens:
            token = token.lower()
            token = self.__normalize(text=token)
            if not token in self.frequencies.keys():
                self.frequencies[token] = 1

            else:
                self.frequencies[token] += 1

    def __save_page_informations(self):
        with self.db.cursor() as db_cursor:
            total_terms = sum(self.frequencies.values())
            for token in self.frequencies.keys():
                # Save page's TF
                db_cursor.execute("INSERT INTO inverted_index (word, page_id, url, title, tf) VALUES (%s, %s, %s, %s, %s)", (
                    token,
                    self.page_informations["id"],
                    self.page_informations["url"],
                    self.page_informations["title"],
                    self.frequencies[token] / total_terms,
                ))

                # Update the number of pages with this word
                db_cursor.execute("""INSERT INTO term_documents (word, documents_number) VALUES (%s, 1)
                ON CONFLICT (word) DO UPDATE SET documents_number = term_documents.documents_number + 1""", (
                    token,
                ))

            # Update the total number of pages
            db_cursor.execute("""INSERT INTO term_documents (word, documents_number) VALUES ('', 1)
            ON CONFLICT (word) DO UPDATE SET documents_number = term_documents.documents_number + 1""")

            self.db.commit()

        # Mark page as indexed
        with self.db.cursor() as db_cursor:
            db_cursor.execute("UPDATE page_informations SET indexed = 1 WHERE id = %s", (self.page_informations["id"],))
            self.db.commit()

    def __calculate_tf_idf(self):
        # Connect to database
        with self.db.cursor() as db_cursor:
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
                db_cursor.execute("SELECT word, tf FROM inverted_index WHERE id >= %s AND id < %s ORDER BY id", (
                    i,
                    i+n_pages_to_get,
                ))
                word_tfs = db_cursor.fetchall()

                # Get list of document's number with word in
                words = [w for w, _ in word_tfs]
                db_cursor.execute(f"SELECT word, documents_number FROM term_documents WHERE word IN ({','.join(['%s']*len(words))})", words)
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
                db_cursor.executemany("UPDATE inverted_index SET tf_idf = %s WHERE id = %s", tf_idfs)
                self.db.commit()
                print("Ajouté")

                i += n_pages_to_get
                print("-------------------------------------------")
                # input("")

    def __calculate_page_ranks(self):
        d = 0.85
        with self.db.cursor() as db_cursor:
            # Get total_numbers documents
            db_cursor.execute("SELECT documents_number FROM term_documents WHERE word = ''")
            total_documents_number = db_cursor.fetchone()[0]

            # Get number of links in each pages
            db_cursor.execute("SELECT source_url, COUNT(*) FROM page_links GROUP BY source_url")
            out_links = dict(db_cursor.fetchall())

            # Calculate first part of page_rank
            first_part = (1-d)/total_documents_number

            # Get links relations
            db_cursor.execute("SELECT source_url, target_url FROM page_links")
            links_relations_sql = db_cursor.fetchall()

            # Init page_ranks
            init_score = (1 / total_documents_number)
            db_cursor.execute("SELECT url FROM page_informations")
            urls = db_cursor.fetchall()
            page_ranks = {url[0]: init_score for url in urls}

            # Format links relations & page ranks
            links_relations = {}
            for relation in links_relations_sql:
                source_url = relation[0]
                target_url = relation[1]
                if target_url in links_relations.keys():
                    links_relations[target_url].append(source_url)

                else:
                    links_relations[target_url] = [source_url]

            # Calculate pagerank of each page
            iterations = 100
            for _ in range(iterations):
                for target_url, sources in links_relations.items():
                    contributions = []
                    for source in sources:
                        if source in page_ranks and source in out_links:
                            contributions.append((page_ranks[source]/out_links[source]))

                    page_ranks[target_url] = first_part + d*sum(contributions)

            # Format pageranks list and add them in db
            page_ranks = [(page_rank, url,) for url, page_rank in page_ranks.items()]
            db_cursor.executemany("UPDATE page_informations SET page_rank = %s WHERE url = %s", page_ranks)
            self.db.commit()

    def calculate_score(self):
        self.__calculate_tf_idf()
        self.__calculate_page_ranks()

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
        try:
            self.init()

            if i == 0:
                running = True
                j = 0
                while running:
                    j += 1
                    self.__run()
                    if j % i_bfr_tf_idf == 0:
                        self.calculate_score()

            else:
                j = 0
                for _ in range(i):
                    j += 1
                    self.__run()
                    if j % i_bfr_tf_idf == 0:
                        self.calculate_score()

        finally:
            self.db.close()


if __name__ == "__main__":
    indexer = Indexer()
    indexer.run()
