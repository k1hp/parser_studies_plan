from bs4 import BeautifulSoup
import requests

url = 'https://mauniver.ru/sveden/education/op/43292#prak'

page = requests.get(url)

# print(page.status_code)

filteredDisceplins = [] # список для хранения отфильтрованных дисциплин
allDisceplins = []

soup = BeautifulSoup(page.text, "html.parser")

# print(soup)

allDisceplins =[el.get_text(strip=True) for el in soup.find_all('h1')] + [el.get_text(strip=True) for el in soup.find_all('p')] + [el.get_text(strip=True) for el in soup.find_all('a', class_='esign')] 
# print(allDisceplins)
# + [el.get_text(strip=True) for el in soup.find_all('p')]

filteredDisceplins = [data for data in allDisceplins if data]

for data in filteredDisceplins:
    print(data)

