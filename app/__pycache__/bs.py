from bs4 import BeautifulSoup
import requests

def get_monthly_listeners(self, artist_id):
    """Obtiene los oyentes mensuales de un artista desde Spotify Web."""
    url = f'https://open.spotify.com/artist/{artist_id}'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    div_tag = soup.find('div', {'data-testid': 'monthly-listeners-label'})
    if div_tag:
        monthly_listeners = div_tag.text.strip().split(" ")[0].replace(",", "")
        return int(monthly_listeners)
    return 0