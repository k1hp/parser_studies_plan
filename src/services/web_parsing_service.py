from typing import List
import requests
from bs4 import BeautifulSoup


class WebParsingService:
    def __init__(self, url: str):
        self.url = url
        self.all_disciplines: List[str] = []
        self.filtered_disciplines: List[str] = []

    def parse(self) -> List[str]:
        response = requests.get(self.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        
        # отображаем как странице
        self.all_disciplines = [
            el.get_text(strip=True)
            for el in soup.select("h1, p, a.esign")
        ]

        self.filtered_disciplines = [item for item in self.all_disciplines if item]
        return self.filtered_disciplines
    

if __name__ == "__main__":
    service = WebParsingService("https://mauniver.ru/sveden/education/op/43292#prak")
    for entry in service.parse():
        print(entry)

