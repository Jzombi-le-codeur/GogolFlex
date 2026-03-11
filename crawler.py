from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
from dateutil import parser as time_parser


class RobotsTxt:
    def __init__(self, name: str, headers: dict):
        self.name = name
        self.headers = headers

        self.authorizations = {"visit": True, "index": True, "follow": True}

    def can_visit(self, url: str):
        # Get robots.txt url
        url_base = urlparse(url)
        robots_txt_url = f"{url_base.scheme}://{url_base.netloc}/robots.txt"

        # Get robots.txt content
        robots_txt_file = requests.get(robots_txt_url, headers=self.headers).text
        rfp = RobotFileParser()
        rfp.parse(robots_txt_file.splitlines())

        # Check if bot can visit the website
        self.authorizations["visit"] = rfp.can_fetch(useragent=self.name, url=url)
        
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

    def get_x_robots_tag_authorizations(self, url: str):
        # Get X-Robots-Tag
        response_headers = requests.get(url=url, headers=self.headers).headers
        try:
            x_robots_tag = response_headers["X-Robots-Tag"]

            # Check authorizations
            self.__check_authorizations(authorizations=x_robots_tag)

        except KeyError:
            pass

    def get_meta_robots_authorizations(self, url: str):
        # Get meta-robots
        page = requests.get(url=url, headers=self.headers).text
        page = BeautifulSoup(page, features="html.parser")
        meta_robots = page.find_all("meta", attrs={"name": "robots"})
        meta_robots = ",".join([m["content"] for m in meta_robots])
        print(meta_robots)

        # Check authorizations
        self.__check_authorizations(authorizations=meta_robots)

    def get_authorizations(self, url):
        self.can_visit(url=url)
        self.get_x_robots_tag_authorizations(url=url)
        self.get_meta_robots_authorizations(url=url)




robots_txt = RobotsTxt(name="GogolFlexBot", headers={"User-Agent": "GogolFlexBot"})
robots_txt.get_authorizations(url="https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal")
print(robots_txt.authorizations)