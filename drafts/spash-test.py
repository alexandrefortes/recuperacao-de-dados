import requests
from bs4 import BeautifulSoup

url = 'https://sejaefi.com.br/central-de-ajuda/api/oferecer-pagamento-online-em-site'

r = requests.get('http://localhost:8050/render.html', params={'url': url, 'wait': 2})

soup = BeautifulSoup(r.text, 'html.parser')

print(soup.title.text)