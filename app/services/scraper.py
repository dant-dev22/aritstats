import requests
from bs4 import BeautifulSoup


def get_monthly_listeners(artist_id: str) -> int:
    url = f"https://open.spotify.com/artist/{artist_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    div_tag = soup.find("div", {"data-testid": "monthly-listeners-label"})
    if div_tag:
        raw = div_tag.text.strip().split(" ")[0].replace(",", "")
        return int(raw)
    return 0
