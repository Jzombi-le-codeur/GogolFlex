import time
import urllib.parse
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from aiohttp import set_zlib_backend
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
from dateutil import parser as time_parser
import hashlib
import pathlib
import os
import psycopg
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv
from datetime import datetime, timezone
import asyncio
import aiohttp
import aiofiles
import tldextract
import time


class Crawler:
    def __init__(self):
        # Bot Informations
        self.name = "GogolFlexBot"
        self.headers = {
            "User-Agent": f"{self.name}/1.0 ( jirasak.habrias@gmail.com)",
            "Cookie": "CONSENT=YES+; SOCS=CAI",
            "Accept-Encoding": "gzip"
        }

        # URLs
        self.queue = asyncio.Queue()
        [self.queue.put_nowait(u) for u in ["https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal", "https://nicot3m.pages-perso.free.fr/", "https://fr.wikihow.com/Accueil"]]
        self.queue_lock = asyncio.Lock()

        # Robots.txt
        self.robots_txt = RobotsTxt(crawler=self)

        # DB connection
        load_dotenv(encoding="utf-8")
        self.n_crawlers = int()
        self.pool = None

    async def __check_if_db_is_empty(self):
        async with self.pool.connection() as conn:
            async with conn.cursor() as db_cursor:
                await db_cursor.execute("SELECT id FROM queue LIMIT 1")
                # Check if db is empty
                if not await db_cursor.fetchone():
                    return True

                else:
                    return False

    async def init(self):
        # Connect to database
        self.pool = AsyncConnectionPool(
            conninfo=f"""
            host={os.getenv("DB_HOST")}
            port={os.getenv("DB_PORT")}
            dbname={os.getenv("DB_NAME")}
            user={os.getenv("DB_USER")}
            password={os.getenv("DB_PASSWORD")} 
            """,
            min_size=1,
            max_size=self.n_crawlers + 3,
            open=False
        )
        await self.pool.open()

        # Create database
        async with self.pool.connection() as conn:
            async with conn.cursor() as db_cursor:
                await db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id SERIAL PRIMARY KEY,
                    url TEXT,
                    domain TEXT
                )
                """)
                await db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS visited_urls (
                    id SERIAL PRIMARY KEY,
                    url TEXT,
                    indexation INTEGER,
                    page_filename TEXT,
                    parsed INTEGER
                )
                """)
                await db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS visited_domains (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE,
                    crawl_delay REAL,
                    last_visit TIMESTAMPTZ
                )
                """)
                await db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS page_links (
                    id SERIAL PRIMARY KEY,
                    source_url TEXT,
                    target_url TEXT
                )
                """)
                await db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_url ON queue(url)")
                await db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_visited_urls_url ON visited_urls(url)")
                await db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_visited_domains_url ON visited_domains(url)")
                await db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_links_source_url ON page_links(source_url)")
                await db_cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_links_target_url ON page_links(target_url)")
                await conn.commit()

                # Load queue if there are urls in db's queue
                if not await self.__check_if_db_is_empty():
                    async with self.queue_lock:
                        self.queue = asyncio.Queue()
                    await self.__load_queue()

    async def __load_queue(self):
        print("cacaquipue")
        async with self.pool.connection() as conn:
            async with conn.cursor() as db_cursor:
                # Get queue
                queue = list()
                while not queue:
                    await db_cursor.execute(f"""
                    SELECT q.id, q.url, q.domain
                    FROM queue q
                    WHERE NOT EXISTS (
                        SELECT 1 FROM visited_domains vd
                        WHERE vd.url = q.domain
                        AND vd.last_visit + (vd.crawl_delay * INTERVAL '1 second' * %s) > NOW()
                    )
                    ORDER BY q.id
                    LIMIT 10
                    FOR UPDATE SKIP LOCKED
                    """, (self.robots_txt.default_crawl_delay,))

                    queue = await db_cursor.fetchall()
                    if not queue:
                        await asyncio.sleep(2)

                    else:
                        timestamp = datetime.now(timezone.utc)
                        urls_to_keep = []
                        visited_domains = []
                        for id, url, domain in queue:
                            if not domain in visited_domains:
                                urls_to_keep.append(url)
                                visited_domains.append(domain)
                                await db_cursor.execute("""
                                DELETE FROM queue WHERE id = %s
                                """, (id,))

                        for domain in visited_domains:
                            await db_cursor.execute("""
                            INSERT INTO visited_domains (url, crawl_delay, last_visit)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (url) DO UPDATE
                            SET last_visit = EXCLUDED.last_visit
                            """, (domain, self.robots_txt.default_crawl_delay, timestamp))

                queue = urls_to_keep
                print(queue)
                async with self.queue_lock:
                    [self.queue.put_nowait(url) for url in queue]

                await conn.commit()

    async def __request(self, session: aiohttp.ClientSession, url: str):
        try:
            async with session.head(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=20), allow_redirects=True) as response:
                content_type = response.headers.get("Content-type", "")
                if "text/html" in content_type or "text/plain" in content_type:  # Check if the document is a web page
                    async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        # Doule check on document type
                        content_type = resp.headers.get("Content-Type", "")
                        if "text/html" not in content_type and "text/plain" not in content_type:
                            return None, None

                        header = dict(resp.headers)
                        response = await resp.text()

                else:
                    response = None
                    header = None

        except (aiohttp.ClientError, TimeoutError, asyncio.CancelledError):
            response = None
            header = None

        return response, header

    async def __mark_url_as_visited(self, url: str, can_visit: bool, page_filepath: pathlib.Path | None, authorizations: dict):
        # Add URL in visited_urls
        print("Page filepath :", page_filepath)
        async with self.pool.connection() as conn:
            async with conn.cursor() as db_cursor:
                if can_visit:
                    await db_cursor.execute("INSERT INTO visited_urls (url, indexation, page_filename, parsed) VALUES (%s, %s, %s, %s)", (
                        url,
                        int(authorizations["index"]),
                        page_filepath.name,
                        0,
                    ))

                else:
                    await db_cursor.execute(
                        "INSERT INTO visited_urls (url, indexation, page_filename, parsed) VALUES (%s, %s, %s, %s)", (
                            url,
                            0,
                            None,
                            0,
                        ))

                await conn.commit()
                print("PROUTTTT NUCLEAIRE")

    async def __mark_domain_as_visited(self, url: str, crawl_delay: int):
        async with self.pool.connection() as conn:
            async with conn.cursor() as db_cursor:
                # Set this site in visited domains
                timestamp = datetime.now(timezone.utc)
                extracted = tldextract.extract(url)
                domain = str(extracted.domain)
                await db_cursor.execute(
                    """
                    INSERT INTO visited_domains (url, crawl_delay, last_visit)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (url) DO UPDATE
                    SET last_visit = EXCLUDED.last_visit, crawl_delay = EXCLUDED.crawl_delay
                    """,
                    (
                        domain,
                        crawl_delay,
                        timestamp,
                    )
                )
                await conn.commit()

    def __get_page(self, response):
        # Parse page code
        return BeautifulSoup(response, features="html.parser")

    async def __add_urls_in_queue(self, urls, db_cursor):
        # Stop function if there are 0 url
        if not urls:
            return

        raw_urls = [u[0] for u in urls]
        placeholders = ','.join(['%s'] * len(urls))

        # Get visited urls
        await db_cursor.execute(f"SELECT url FROM visited_urls WHERE url IN ({placeholders})", raw_urls)
        visited_urls = {row[0] for row in await db_cursor.fetchall()}

        # Get urls already in queue
        await db_cursor.execute(f"SELECT url FROM queue WHERE url IN ({placeholders})", raw_urls)
        urls_in_queue = {row[0] for row in await db_cursor.fetchall()}

        # Insert urls in database
        # urls = set(urls) - visited_urls - urls_in_queue
        urls = {(url, domain,) for url, domain in urls if not url in  visited_urls and not url in urls_in_queue}
        await db_cursor.executemany("INSERT INTO queue (url, domain) VALUES (%s, %s)", [(url, domain,) for url, domain in urls])

    async def __add_links_relations(self, links_relations: list, db_cursor):
        # Check if there are links
        if not links_relations:
            return

        # Add relations in db
        await db_cursor.executemany("INSERT INTO page_links (source_url, target_url) VALUES (%s, %s)", links_relations)

    async def __get_links(self, page_url: str, page: BeautifulSoup):
        # Get all a tags
        links = page.find_all("a")

        urls = []
        links_relations = []
        # Get & format all links
        for a in links:
            # Check if there's href in a
            if a.has_attr("href"):
                link = a["href"]  # Get link

                # Create url based on relative link
                if link.startswith("/") and not link.startswith("//"):
                    parsed_url = urlparse(page_url)
                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{link}"

                # Complete link with HTTP or HTTPS
                elif link.startswith("//"):
                    parsed_url = urlparse(page_url)
                    url = f"{parsed_url.scheme}:{link}"

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
                            continue

                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{url_path}".rstrip('/')
                    extracted = tldextract.extract(url)
                    domain = str(extracted.domain)
                    urls.append((url, domain,))
                    links_relations.append((page_url, url))

        async with self.pool.connection() as conn:
            async with conn.cursor() as db_cursor:
                # Add urls in database queue
                await self.__add_urls_in_queue(urls=urls, db_cursor=db_cursor)

                # Add link's relations
                await self.__add_links_relations(links_relations=links_relations, db_cursor=db_cursor)

                # Add URLs in queue & close connection
                await conn.commit()

    async def __save_page(self, url: str, page: BeautifulSoup):
        print("caca")
        # Create page's file's information
        page_filename = f"{hashlib.blake2b(url.encode("utf-8"), digest_size=16).hexdigest()}.html"  # Filename : hashed page's url
        print("FILENAME :", page_filename)
        page_filepath = pathlib.PurePath(pathlib.Path("Pages"), page_filename[:2], page_filename)

        # Create Directory if it doesn't exist
        if not os.path.exists(os.path.dirname(page_filepath)):
            os.makedirs(os.path.dirname(page_filepath))

        # Write file
        async with aiofiles.open(page_filepath, "w", encoding="utf-8") as page_file:
            await page_file.write(page.prettify())

        return pathlib.Path(page_filepath)

    async def __run(self, session):
        # Load queue if queue is empty
        if self.queue.empty():
            await self.__load_queue()

        # Get URL
        url = await self.queue.get()  # Get URl and delete it

        # Check if URL is in delay
        # extracted = tldextract.extract(url)
        # domain = f"{extracted.domain}.{extracted.suffix}"
        # async with self.pool.connection() as conn:
        #     async with conn.cursor() as db_cursor:
        #         await db_cursor.execute("""
        #         SELECT 1 FROM visited_domains
        #         WHERE url = %s
        #         AND last_visit + (crawl_delay * INTERVAL '1 second') > NOW()
        #         """, (domain,))
        #         too_soon = await db_cursor.fetchone()
        #
        # if too_soon:
        #     await self.queue.put(url)  # Remet en queue
        #     await asyncio.sleep(0.1)
        #     return

        print(f"URl de la page : {url}")
        print(f"Nombre de sites à visiter : {self.queue.qsize()}")

        authorizations = {"visit": True, "index": True, "follow": True}  # Reset authorizations
        authorizations, crawl_delay = await self.robots_txt.can_visit(url=url, session=session, authorizations=authorizations)
        await self.__mark_domain_as_visited(url=url, crawl_delay=crawl_delay)

        if authorizations["visit"]:
            # Get response from page
            response, header = await self.__request(session=session, url=url)
            if response:
                # Get page's authorizations
                self.robots_txt.get_authorizations(response=response, header=header, authorizations=authorizations)

                # Get page's links & information
                print("PROUTTTT")
                page = self.__get_page(response=response)  # Get page code

                # Save datas
                page_filepath = await self.__save_page(url=url, page=page)  # Save page

                # Get page's links
                if authorizations["follow"]:
                    await self.__get_links(page_url=url, page=page)

                await self.__mark_url_as_visited(can_visit=True, url=url, page_filepath=page_filepath, authorizations=authorizations)  # Save datas

            else:
                await self.__mark_url_as_visited(can_visit=False, url=url, page_filepath=None, authorizations=authorizations)

        else:
            await self.__mark_url_as_visited(can_visit=False, url=url, page_filepath=None, authorizations=authorizations)

        print("----------------------------")
        # await asyncio.sleep(self.robots_txt.crawl_delay)  # Wait not to DDOS host
        await asyncio.sleep(0.1)

    async def run_crawler(self, i: int = 0):

        async with aiohttp.ClientSession() as session:
            if i == 0:
                running = True
                while running:
                    a = time.time()
                    await self.__run(session=session)
                    print("TEMPS :", time.time() - a)
                    print("________________________________________")

            else:
                for _ in range(i):
                    await self.__run(session=session)

    async def run(self, n_crawlers: int, i: int = 0):
        try:
            self.n_crawlers = n_crawlers

            # Initialization
            await self.init()

            tasks = [self.run_crawler(i=i) for _ in range(n_crawlers)]
            await asyncio.gather(*tasks)

        finally:
            await self.pool.close()

class RobotsTxt:
    def __init__(self, crawler: Crawler):
        # Bot's informations
        self.crawler = crawler
        self.name = self.crawler.name
        self.headers = self.crawler.headers

        # Create RobotsTXT folder
        os.makedirs("RobotsTXT") if not os.path.exists("RobotsTXT") else None

        self.default_crawl_delay = 1

    async def __get_robots_txt_file(self, url_base: urllib.parse.ParseResult, session):
        s = time.time()
        robots_txt_filepath = pathlib.PurePath("RobotsTXT", f"{url_base.netloc}.txt")
        if os.path.exists(robots_txt_filepath):
            async with aiofiles.open(robots_txt_filepath, "r", encoding="utf-8") as robots_txt_file:
                robots_txt_file_content = await robots_txt_file.read()

        else:
            robots_txt_url = f"{url_base.scheme}://{url_base.netloc}/robots.txt"
            async with session.get(robots_txt_url, headers=self.headers) as response:
                try:
                    robots_txt_file_content = await response.text()

                except UnicodeDecodeError:
                    return ""

            async with aiofiles.open(robots_txt_filepath, "w", encoding="utf-8") as robots_txt_file:
                await robots_txt_file.write(robots_txt_file_content)

        print("TIME :", time.time()-s)
        return robots_txt_file_content

    async def can_visit(self, url: str, session, authorizations: dict):
        # Get robots.txt url
        url_base = urlparse(url)

        # Get robots.txt content
        try:
            # robots_txt_file =
            robots_txt_file = await self.__get_robots_txt_file(url_base=url_base, session=session)
            rfp = RobotFileParser()
            rfp.parse(robots_txt_file.splitlines())

            # Check if bot can visit the website
            authorizations["visit"] = rfp.can_fetch(useragent=self.name, url=url)

            # Get Crawl-delay
            crawl_delay = rfp.crawl_delay(self.name)
            crawl_delay = crawl_delay if crawl_delay else self.default_crawl_delay


        except (aiohttp.ClientError, TimeoutError, asyncio.CancelledError):
            authorizations["visit"] = False
            crawl_delay = 0

        return authorizations, crawl_delay

    def __check_authorizations(self, authorizations, directives):
        if "noindex" in directives:
            authorizations["index"] = False

        if "nofollow" in directives:
            authorizations["follow"] = False

        if "none" in directives:
            authorizations["index"] = False
            authorizations["follow"] = False

        if "unavailable_after" in directives:
            auth_parts = re.split(r',(?=[a-zA-Z-]+:?)', directives)
            for d in auth_parts:
                if d.startswith("unavailable_after"):
                    unavailable_after = d.split(":", 1)
                    date = unavailable_after[-1]
                    if not date:
                        break

                    dt = time_parser.parse(date)

                    # Check authorization
                    if datetime.now(timezone.utc) > dt:
                        authorizations["index"] = False
                        authorizations["follow"] = False

        if "noodp" in directives:
            pass

        return authorizations

    def get_x_robots_tag_authorizations(self, header, authorizations):
        if not header:
            return

        # Get X-Robots-Tag
        response_headers = header
        try:
            x_robots_tag = response_headers["X-Robots-Tag"]

            # Check authorizations
            self.__check_authorizations(directives=x_robots_tag, authorizations=authorizations)

        except KeyError:
            pass

    def get_meta_robots_authorizations(self, response, authorizations):
        # Get meta-robots
        page = response
        page = BeautifulSoup(page, features="html.parser")
        meta_robots = page.find_all("meta", attrs={"name": "robots"})
        meta_robots = ",".join([m["content"] for m in meta_robots])

        # Check authorizations
        self.__check_authorizations(directives=meta_robots, authorizations=authorizations)

    def get_authorizations(self, response, header, authorizations):
        self.get_x_robots_tag_authorizations(header=header, authorizations=authorizations)
        self.get_meta_robots_authorizations(response=response, authorizations=authorizations)


if __name__ == "__main__":
    crawler = Crawler()
    asyncio.run(crawler.run(n_crawlers=5), loop_factory=asyncio.SelectorEventLoop)
