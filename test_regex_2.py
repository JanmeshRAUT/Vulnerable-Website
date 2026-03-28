import re

url1 = "http://stock.secureshop.local/admin"
url2 = "http://stock.secureshop.local/"
url3 = "http://stock.secureshop.local"

pattern = r'https?://[^/]+(/.+)'

def test(url):
    match = re.search(pattern, url)
    print(f"URL: {url} -> Group 1: {match.group(1) if match else 'No Match'}")

test(url1)
test(url2)
test(url3)
