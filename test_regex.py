import re

pattern = r'https?://192\.168\.0\.(\d+):8080(/.*)'

def test(url):
    match = re.search(pattern, url)
    if match:
        print(f"URL: {url} -> Match! Octet: {match.group(1)}, Path: {match.group(2)}")
    else:
        print(f"URL: {url} -> No Match")

test("http://192.168.0.1:8080/admin")
test("http://192.168.0.1:8080/")
test("http://192.168.0.1:8080")
test("http://192.168.0.92:8080/admin")
test("http://192.168.0.92:8080")
