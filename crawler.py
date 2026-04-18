import time
import urllib.parse
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
import psycopg
from dotenv import load_dotenv
from datetime import datetime, timezone


class Crawler:
    def __init__(self):
        # Bot Informations
        self.name = "GogolFlexBot"
        self.headers = {
            "User-Agent": self.name
        }

        # URLs
        self.queue = ["https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal", "https://nicot3m.pages-perso.free.fr/", "https://fr.wikihow.com/Accueil"]
        self.url = self.queue[0]
        self.response = requests.Response()
        self.page = BeautifulSoup("", "html.parser")
        self.page_filepath = pathlib.PurePath()

        # Robots.txt
        self.robots_txt = RobotsTxt(crawler=self)

        # DB connection
        load_dotenv(encoding="utf-8")
        self.db = psycopg.connect(
            dbname="GogolFlexDB",
            user="postgres",
            password=os.getenv("PASSWORD"),
            host="localhost",
            port=5432
        )

    def __check_if_db_is_empty(self):
        with self.db.cursor() as db_cursor:
            db_cursor.execute("SELECT id FROM queue LIMIT 1")
            # Check if db is empty
            if not db_cursor.fetchone():
                return True

            else:
                return False

    def init(self):
        # Create database
        with self.db.cursor() as db_cursor:
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id SERIAL PRIMARY KEY,
                url TEXT,
                domain TEXT
            )
            """)
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS visited_urls (
                id SERIAL PRIMARY KEY,
                url TEXT,
                indexation INTEGER,
                page_filename TEXT,
                parsed INTEGER
            )
            """)
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS visited_domains (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE,
                crawl_delay REAL,
                last_visit TIMESTAMPTZ
            )
            """)
            db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_links (
                id SERIAL PRIMARY KEY,
                source_url TEXT,
                target_url TEXT
            )
            """)
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_url ON queue(url)")
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_visited_urls_url ON visited_urls(url)")
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_visited_domains_url ON visited_domains(url)")
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_links_source_url ON page_links(source_url)")
            db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_links_target_url ON page_links(target_url)")
            self.db.commit()

            # Load queue if there are urls in db's queue
            if not self.__check_if_db_is_empty():
                self.queue.clear()
                self.__load_queue()

    def __load_queue(self):
        print("cacaquipue")
        with self.db.cursor() as db_cursor:
            # Get queue
            queue = list()
            while not queue:
                # Get pages of not visited domains & delete them from queue
                db_cursor.execute("""
                DELETE FROM queue
                WHERE id IN (
                    SELECT DISTINCT ON (q.domain) q.id
                    FROM queue q
                    WHERE NOT EXISTS (
                        SELECT 1 FROM visited_domains vd
                        WHERE vd.url = q.domain
                        AND vd.last_visit + (vd.crawl_delay * INTERVAL '1 second') > NOW()
                    )
                    ORDER BY q.domain, q.id
                    LIMIT 10
                )
                RETURNING id, url, domain
                """)
                queue = db_cursor.fetchall()
                if not queue:
                    time.sleep(0.5)

            print(queue)
            self.queue = [u[1] for u in queue]

            self.db.commit()

    def __request(self):
        try:
            response = requests.head(self.url, headers=self.headers, timeout=20)
            content_type = response.headers.get("Content-type", "")
            if "text/html" in content_type:
                self.response = requests.get(self.url, headers=self.headers, timeout=20)

            else:
                self.response = None

        except requests.exceptions.RequestException:
            self.response = None

    def __mark_url_as_visited(self, can_visit: bool):
        # Add URL in visited_urls
        print("Page filepath :", self.page_filepath)
        with self.db.cursor() as db_cursor:
            if can_visit:
                db_cursor.execute("INSERT INTO visited_urls (url, indexation, page_filename, parsed) VALUES (%s, %s, %s, %s)", (
                    self.url,
                    int(self.robots_txt.authorizations["index"]),
                    self.page_filepath.name,
                    0,
                ))

            else:
                db_cursor.execute(
                    "INSERT INTO visited_urls (url, indexation, page_filename, parsed) VALUES (%s, %s, %s, %s)", (
                        self.url,
                        0,
                        None,
                        0,
                    ))

            self.db.commit()
            print("PROUTTTT NUCLEAIRE")

    def __mark_domain_as_visited(self):
        with self.db.cursor() as db_cursor:
            # Set this site in visited domains
            timestamp = datetime.now(timezone.utc)
            db_cursor.execute(
                """
                INSERT INTO visited_domains (url, crawl_delay, last_visit)
                VALUES (%s, %s, %s)
                ON CONFLICT (url) DO UPDATE
                SET last_visit = EXCLUDED.last_visit, crawl_delay = EXCLUDED.crawl_delay
                """,
                (
                    urlparse(self.url).netloc,
                    self.robots_txt.crawl_delay,
                    timestamp,
                )
            )
            self.db.commit()

    def __get_page(self):
        # Parse page code
        self.page = BeautifulSoup(self.response.text, features="html.parser")

    def __add_urls_in_queue(self, urls, db_cursor):
        # Stop function if there are 0 url
        if not urls:
            return

        raw_urls = [u[0] for u in urls]
        placeholders = ','.join(['%s'] * len(urls))

        # Get visited urls
        db_cursor.execute(f"SELECT url FROM visited_urls WHERE url IN ({placeholders})", raw_urls)
        visited_urls = {row[0] for row in db_cursor.fetchall()}

        # Get urls already in queue
        db_cursor.execute(f"SELECT url FROM queue WHERE url IN ({placeholders})", raw_urls)
        urls_in_queue = {row[0] for row in db_cursor.fetchall()}

        # Insert urls in database
        # urls = set(urls) - visited_urls - urls_in_queue
        urls = {(url, domain,) for url, domain in urls if not url in  visited_urls and not url in urls_in_queue}
        db_cursor.executemany("INSERT INTO queue (url, domain) VALUES (%s, %s)", [(url, domain,) for url, domain in urls])

    def __add_links_relations(self, links_relations: list, db_cursor):
        # Check if there are links
        if not links_relations:
            return

        # Add relations in db
        db_cursor.executemany("INSERT INTO page_links (source_url, target_url) VALUES (%s, %s)", links_relations)

    def __get_links(self):
        # Get all a tags
        links = self.page.find_all("a")

        urls = []
        links_relations = []
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
                    url_path = parsed_url.path

                    # Check if url has an allowed extension
                    allowed_ext = {".htm", ".html", ".php", ".asp", ".aspx", ".xhtml"}
                    if "." in url_path:
                        if pathlib.PurePath(url_path).suffix.lower() not in allowed_ext:
                            return

                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{url_path}".rstrip('/')
                    domain = parsed_url.netloc
                    urls.append((url, domain,))
                    links_relations.append((self.url, url))


        with self.db.cursor() as db_cursor:
            # Add urls in database queue
            self.__add_urls_in_queue(urls=urls, db_cursor=db_cursor)

            # Add link's relations
            self.__add_links_relations(links_relations=links_relations, db_cursor=db_cursor)

            # Add URLs in queue & close connection
            self.db.commit()

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

    def __run(self):
        # Load queue if queue is empty
        if len(self.queue) == 0:
            self.__load_queue()

        # Get URL
        self.url = self.queue.pop(0)  # Get URl and delete it

        print(f"URl de la page : {self.url}")
        print(f"Nombre de sites à visiter : {len(self.queue)}")

        self.robots_txt.can_visit(url=self.url)
        self.__mark_domain_as_visited()

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

                # Get page's links
                if self.robots_txt.authorizations["follow"]:
                    self.__get_links()

                self.__mark_url_as_visited(can_visit=True)  # Save datas

            else:
                self.__mark_url_as_visited(can_visit=False)

        else:
            self.__mark_url_as_visited(can_visit=False)

        print("----------------------------")
        # time.sleep(self.robots_txt.crawl_delay)  # Wait not to DDOS host
        time.sleep(0.1)

    def run(self, i: int = 0):
        try:
            # Initialization
            self.init()

            if i == 0:
                running = True
                while running:
                    a = time.time()
                    self.__run()
                    print("TEMPS :", time.time() - a)
                    print("________________________________________")

            else:
                for _ in range(i):
                    self.__run()

        finally:
            self.db.close()


class RobotsTxt:
    def __init__(self, crawler: Crawler):
        # Bot's informations
        self.crawler = crawler
        self.name = self.crawler.name
        self.headers = self.crawler.headers
        self.response = self.crawler.response

        # Page authorizations
        self.authorizations = {"visit": True, "index": True, "follow": True}
        self.crawl_delay = 1

        # Create RobotsTXT folder
        os.makedirs("RobotsTXT") if not os.path.exists("RobotsTXT") else None

    def __get_robots_txt_file(self, url_base: urllib.parse.ParseResult):
        s = time.time()
        robots_txt_filepath = pathlib.PurePath("RobotsTXT", f"{url_base.netloc}.txt")
        if os.path.exists(robots_txt_filepath):
            with open(robots_txt_filepath, "r", encoding="utf-8") as robots_txt_file:
                robots_txt_file_content = robots_txt_file.read()

        else:
            robots_txt_url = f"{url_base.scheme}://{url_base.netloc}/robots.txt"
            robots_txt_file_content = requests.get(robots_txt_url, headers=self.headers).text
            with open(robots_txt_filepath, "w", encoding="utf-8") as robots_txt_file:
                robots_txt_file.write(robots_txt_file_content)

        print("TIME :", time.time()-s)
        return robots_txt_file_content

    def can_visit(self, url: str):
        # Get robots.txt url
        url_base = urlparse(url)

        # Get robots.txt content
        try:
            # robots_txt_file =
            robots_txt_file = self.__get_robots_txt_file(url_base=url_base)
            rfp = RobotFileParser()
            rfp.parse(robots_txt_file.splitlines())

            # Check if bot can visit the website
            self.authorizations["visit"] = rfp.can_fetch(useragent=self.name, url=url)

            # Get Crawl-delay
            crawl_delay = rfp.crawl_delay(self.name)
            self.crawl_delay = crawl_delay if crawl_delay else 1

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


if __name__ == "__main__":
    crawler = Crawler()
    crawler.run(i=20)
