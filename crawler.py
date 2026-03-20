import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
from dateutil import parser as time_parser
import hashlib
import pathlib
import os
import sqlite3


class Crawler:
    def __init__(self):
        # Bot Informations
        self.name = "GogolFlexBot"
        self.headers = {
            "User-Agent": self.name
        }

        # URLs
        self.queue = ["https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal"]
        self.url = self.queue[0]
        self.response = requests.Response()
        self.page = BeautifulSoup()
        self.page_filepath = pathlib.PurePath()

        # Robots.txt
        self.robots_txt = RobotsTxt(crawler=self)

    def init(self):
        # Create database
        if not os.path.exists("crawl.db"):
            db = sqlite3.connect("crawl.db")
            db.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT
            )
            """)
            db.execute("""
            CREATE TABLE IF NOT EXISTS visited_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                indexation INTEGER,
                page_filename TEXT,
                parsed INTEGER
            )
            """)
            db.commit()
            db.close()

    def __load_queue(self):
        try:
            print("cacaquipue")
            # Connect to database
            db = sqlite3.connect("crawl.db")
            db_cursor = db.cursor()

            # Get queue
            db_cursor.execute("SELECT id, url FROM queue ORDER BY id LIMIT 10")
            queue = db_cursor.fetchmany(10)
            print(queue)
            self.queue = [u[1] for u in queue]
            ids = [u[0] for u in queue]

            # Delete these URLs from queue db
            db_cursor.execute(f"DELETE FROM queue WHERE id IN ({','.join('?' for _ in ids)})", ids)
            db.commit()

        finally:
            db.close()

    def __request(self):
        try:
            self.response = requests.get(self.url, headers=self.headers)

        except requests.exceptions.RequestException:
            self.response = None

    def __mark_url_as_visited(self):
        # Connect to database
        db = sqlite3.connect("crawl.db")

        # Add URL in visited_urls
        print("Page filepath :", self.page_filepath)
        db.execute("INSERT INTO visited_urls (url, indexation, page_filename, parsed) VALUES (?, ?, ?, ?)", (
            self.url,
            int(self.robots_txt.authorizations["index"]),
            self.page_filepath.name,
            0,
        ))
        db.commit()
        print("PROUTTTT NUCLEAIRE")

        # Close database
        db.close()

    def __get_page(self):
        # Parse page code
        self.page = BeautifulSoup(self.response.text, features="html.parser")

    def __check_if_page_has_been_visited(self, url):
        db = sqlite3.connect("crawl.db")
        db_cursor = db.cursor()
        db_cursor.execute("SELECT 1 FROM visited_urls WHERE url = (?)", (url,))
        if db_cursor.fetchone():
            return True

        else:
            return False

    def __check_if_page_is_in_queue(self, url):
        db = sqlite3.connect("crawl.db")
        db_cursor = db.cursor()
        db_cursor.execute("SELECT 1 FROM queue WHERE url = (?)", (url,))
        if db_cursor.fetchone():
            return True

        else:
            return False

    def __get_links(self):
        # Get all a tags
        links = self.page.find_all("a")

        # Connect to database
        db = sqlite3.connect("crawl.db")
        db_cursor = db.cursor()

        # Get & format all links
        for a in links:
            # Check if there's href in a
            if a.has_attr("href"):
                link = a["href"]  # Get link

                # Create url based on relative link
                if link.startswith("/") and not link.startswith("//"):
                    parsed_url = urlparse(self.url)
                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{link}"

                # Complete link with HTTP or HTTPS
                elif link.startswith("//"):
                    parsed_url = urlparse(self.url)
                    url = f"{parsed_url.scheme}{link}"

                # Get URL
                elif link.startswith("http"):
                    url = link

                else:
                    url = None

                # Add url if url in queue is not in queue or has never been visited
                if url:
                    parsed_url = urlparse(url)
                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}".rstrip('/')
                    if not self.__check_if_page_has_been_visited(url=url) and not self.__check_if_page_is_in_queue(url=url):
                        # Add url in database queue
                        db_cursor.execute(f"INSERT INTO queue (url) VALUES (?)", (url,))

        # Add URLs in queue & close connection
        db.commit()
        db.close()

    def __save_page(self):
        print("caca")
        # Create page's file's information
        page_filename = f"{hashlib.blake2b(self.url.encode("utf-8"), digest_size=16).hexdigest()}.html"  # Filename : hashed page's url
        print("FILENAME :", page_filename)
        self.page_filepath = pathlib.PurePath(pathlib.Path("Pages"), page_filename[:2], page_filename)

        # Create Directory if it doesn't exist
        if not os.path.exists(os.path.dirname(self.page_filepath)):
            os.makedirs(os.path.dirname(self.page_filepath))

        # Write file
        with open(self.page_filepath, "w", encoding="utf-8") as page_file:
            page_file.write(self.page.prettify())

    def run(self):
        # Initialization
        self.init()

        # running = True
        # while running:
        for _ in range(3):
            # Load queue if queue is empty
            if len(self.queue) == 0:
                self.__load_queue()

            # Get URL
            self.url = self.queue.pop(0)  # Get URl and delete it

            print(f"URl de la page : {self.url}")
            print(f"Nombre de sites à visiter : {len(self.queue)}")

            self.robots_txt.can_visit(url=self.url)
            if self.robots_txt.authorizations["visit"]:
                # Get response from page
                self.__request()
                if self.response:
                    # Get page's authorizations
                    self.robots_txt.get_authorizations()

                    # Get page's links & information
                    print("PROUTTTT")
                    self.__get_page()  # Get page code

                    # Save datas
                    self.__save_page()  # Save page
                    self.__mark_url_as_visited()  # Save datas

                    # Get page's links
                    if self.robots_txt.authorizations["follow"]:
                        self.__get_links()

            print("----------------------------")
            time.sleep(1)  # Wait not to DDOS host


class RobotsTxt:
    def __init__(self, crawler: Crawler):
        # Bot's informations
        self.crawler = crawler
        self.name = self.crawler.name
        self.headers = self.crawler.headers
        self.response = self.crawler.response

        # Page authorizations
        self.authorizations = {"visit": True, "index": True, "follow": True}

    def can_visit(self, url: str):
        # Get robots.txt url
        url_base = urlparse(url)
        robots_txt_url = f"{url_base.scheme}://{url_base.netloc}/robots.txt"

        # Get robots.txt content
        print(robots_txt_url)
        try:
            robots_txt_file = requests.get(robots_txt_url, headers=self.headers).text
            rfp = RobotFileParser()
            rfp.parse(robots_txt_file.splitlines())

            # Check if bot can visit the website
            self.authorizations["visit"] = rfp.can_fetch(useragent=self.name, url=url)

        except requests.exceptions.RequestException:
            self.authorizations["visit"] = False

    def __check_authorizations(self, authorizations):
        if "noindex" in authorizations:
            self.authorizations["index"] = False

        if "nofollow" in authorizations:
            self.authorizations["follow"] = False

        if "none" in authorizations:
            self.authorizations["index"] = False
            self.authorizations["follow"] = False

        if "unavailable_after" in authorizations:
            auth_parts = re.split(r',(?=[a-zA-Z-]+:?)', authorizations)
            for d in auth_parts:
                if d.startswith("unavailable_after"):
                    unavailable_after = d.split(":", 1)
                    date = unavailable_after[-1]
                    if not date:
                        break

                    dt = time_parser.parse(date)

                    # Check authorization
                    if datetime.now(timezone.utc) > dt:
                        self.authorizations["index"] = False
                        self.authorizations["follow"] = False

        if "noodp" in authorizations:
            pass

    def get_x_robots_tag_authorizations(self):
        # Get X-Robots-Tag
        response_headers = self.response.headers
        try:
            x_robots_tag = response_headers["X-Robots-Tag"]

            # Check authorizations
            self.__check_authorizations(authorizations=x_robots_tag)

        except KeyError:
            pass

    def get_meta_robots_authorizations(self):
        # Get meta-robots
        page = self.response.text
        page = BeautifulSoup(page, features="html.parser")
        meta_robots = page.find_all("meta", attrs={"name": "robots"})
        meta_robots = ",".join([m["content"] for m in meta_robots])

        # Check authorizations
        self.__check_authorizations(authorizations=meta_robots)

    def get_authorizations(self):
        self.authorizations = {"visit": True, "index": True, "follow": True}  # Reset authorizations
        self.response = self.crawler.response  # Get response from page
        self.get_x_robots_tag_authorizations()
        self.get_meta_robots_authorizations()


class Parser:
    def __init__(self):
        self.page_informations = {"id": int(), "url": str(), "page_filename": str(), "title": str()}
        self.page_code = BeautifulSoup()

    def init(self):
        db = sqlite3.connect("parse.db")
        db.execute("""
                    CREATE TABLE IF NOT EXISTS page_informations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT,
                        page_filename TEXT,
                        title TEXT
                    )
                    """)

    def __get_crawl_results(self):
        # Get visited_urls datas
        db = sqlite3.connect("crawl.db")
        db_cursor = db.cursor()
        db_cursor.execute("SELECT id, url, indexation, page_filename FROM visited_urls WHERE parsed=0 ORDER BY id LIMIT 1")
        page_informations = db_cursor.fetchone()

        # Get informations
        print(page_informations)
        if bool(page_informations[1]):
            self.page_informations["id"] = page_informations[0]
            self.page_informations["url"] = page_informations[1]
            self.page_informations["page_filename"] = page_informations[3]

        db.close()

    def __get_page_code(self):
        # Get page code
        page_filepath = pathlib.PurePath("Pages", self.page_informations["page_filename"][:2],
                                         self.page_informations["page_filename"])
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

    def __save_datas(self):
        # Mark page as parsed
        db = sqlite3.connect("crawl.db")
        db.execute("UPDATE visited_urls SET parsed=1 WHERE id=?", (self.page_informations["id"],))
        db.commit()
        db.close()

        # Save informations
        db = sqlite3.connect("parse.db")
        db.execute("INSERT INTO page_informations (url, page_filename, title) VALUES (?, ?, ?)", (
            self.page_informations["url"],
            self.page_informations["page_filename"],
            self.page_informations["title"],
        ))
        db.commit()
        db.close()

    def run(self):
        # Initialize database
        self.init()

        # Get basic page's information (url, index, pagepath)
        self.__get_crawl_results()

        # Get page code
        self.__get_page_code()

        # Get page title
        self.__get_page_title()

        # Save informations
        self.__save_datas()


# crawler = Crawler()
# crawler.run()
parser = Parser()
parser.run()
