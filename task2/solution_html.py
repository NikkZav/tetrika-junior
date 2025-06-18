import csv
import logging
import requests
import time
from collections import defaultdict

from bs4 import BeautifulSoup, PageElement, Tag

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RUS_ALPHABET = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
ORDER_RUS_ALPHABET = {letter: index for index, letter in enumerate(RUS_ALPHABET)}


def get_wikipedia_page(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Ошибка при загрузке страницы {url}: {e}")
        return None


def parse_category_page(html: str) -> tuple[list[str], str | None]:
    soup = BeautifulSoup(html, 'html.parser')
    titles: list[str] = []
    next_page_url: str | None = None

    category_div: PageElement | None = soup.find('div', id='mw-pages')
    if not isinstance(category_div, Tag):
        logger.warning("Контейнер со списком страниц не найден или не является тегом")
        return titles, None

    for link in category_div.find_all('a'):
        if not isinstance(link, Tag):
            logger.debug("Пропущен элемент, не являющийся тегом")
            continue
        title = link.get('title')
        if isinstance(title, str):
            titles.append(title)
            logger.debug(f"Извлечен заголовок: {title}")
        else:
            logger.debug(f"Пропущен заголовок, так как title не строка: {title}")

    logger.debug(f"Найдено {len(titles)} заголовков на странице")
    next_page_link: PageElement | None = soup.find('a', string='Следующая страница')
    if isinstance(next_page_link, Tag) and 'href' in next_page_link.attrs:
        href = next_page_link['href']
        if isinstance(href, str):
            next_page_url = href
        else:
            logger.warning(f"Атрибут href не является строкой: {href}")

    return titles, next_page_url


def get_category_members_html() -> list[str]:
    base_url = "https://ru.wikipedia.org"
    current_url: str | None = f"{base_url}/wiki/Категория:Животные_по_алфавиту"
    all_titles: list[str] = []

    while current_url:
        logger.debug(f"Обработка страницы: {current_url}")
        html = get_wikipedia_page(current_url)
        if not html:
            break
        titles, next_page_url = parse_category_page(html)
        all_titles.extend(titles)
        current_url = f"{base_url}{next_page_url}" if next_page_url else None
        time.sleep(0.5)

    logger.info(f"Всего получено {len(all_titles)} заголовков через HTML")
    return all_titles


def count_animals_by_letter() -> dict[str, int]:
    logger.info("Начало обработки категорий через HTML")
    start_time = time.time()
    letter_counts: dict[str, int] = defaultdict(int)

    titles = get_category_members_html()

    for title in titles:
        if title and title[0].upper() in RUS_ALPHABET:
            letter_counts[title[0].upper()] += 1
            logger.debug(f"Подсчитан: {title}")
        else:
            logger.debug(f"Пропущен: {title}")

    logger.info(f"Обработано {sum(letter_counts.values())} заголовков через HTML")
    logger.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
    return letter_counts


def write_to_csv(letter_counts: dict[str, int], filename: str = "beasts_html.csv"):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for letter in sorted(letter_counts.keys(), key=lambda c: ORDER_RUS_ALPHABET[c]):
            writer.writerow([letter, letter_counts[letter]])
    logger.info(f"Результаты записаны в {filename}")


def main():
    letter_counts = count_animals_by_letter()
    write_to_csv(letter_counts, filename="beasts_html.csv")


if __name__ == "__main__":
    main()
