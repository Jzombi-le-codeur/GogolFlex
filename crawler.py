import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
from dateutil import parser as time_parser


class Crawler:
    def __init__(self):
        # Bot Informations
        self.name = "GogolFlexBot"
        self.headers = {
            "User-Agent": self.name
        }

        # URLs
        self.urls = ["https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal"]
        self.url = self.urls[0]
        self.response = requests.Response()
        self.page = BeautifulSoup()
        self.visited_urls = []

        # Robots.txt
        self.robots_txt = RobotsTxt(crawler=self)

    def __request(self):
        try:
            self.response = requests.get(self.url, headers=self.headers)

        except requests.exceptions.RequestException:
            self.response = None

    def __get_page(self):
        # Parse page code
        self.page = BeautifulSoup(self.response.text, features="html.parser")

    def __get_links(self):
        # Get all a tags
        links = self.page.find_all("a")

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

                # Add url if url is not in queue or has never been visited
                if url:
                    parsed_url = urlparse(url)
                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}".rstrip('/')
                    if not url in self.visited_urls and not url in self.urls:
                        self.urls.append(url)

    def run(self):
        while self.urls:
            # Get URL
            self.url = self.urls.pop(0)  # Get URl and delete it

            print(f"URl de la page : {self.url}")
            print(f"Nombre de sites à visiter : {len(self.urls)}")
            print(f"Nombre de site visités : {len(self.visited_urls)}")

            self.robots_txt.can_visit(url=self.url)
            if self.robots_txt.authorizations["visit"]:
                # Get response from page
                self.__request()
                if self.response:
                    # Get page's authorizations
                    self.robots_txt.get_authorizations()

                    # Get page's links & information
                    self.visited_urls.append(self.url)
                    self.__get_page()  # Get page code

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


bot = Crawler()
bot.run()
