from urllib.parse import urlparse


url = "http://caca.org/prout/test/caca"
url_path = urlparse(url).path.split("/")
url_path.pop(0) if not url_path[0] else url_path
print(url_path)

link = "../../test/../caca"
link = link.split("/")
print(link)

i = 0
n = len(link)
s = True
while i < n:
    if link[i] == "..":
        if s:
            link.pop(0)
            url_path.pop(i)

        else:
            link.pop(i-1)

    else:
        s = False

    print("------------------")
    print(url_path)
    print(link)

    i += 1

url = "/".join(url_path) + "/".join(link)
print(url)
