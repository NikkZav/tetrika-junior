import csv
import logging
import requests
import time
from collections import defaultdict


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RUS_ALPHABET = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
ORDER_RUS_ALPHABET = {letter: index for index, letter in enumerate(RUS_ALPHABET)}


def get_category_members_api(category: str) -> set[str]:
    url = "https://ru.wikipedia.org/w/api.php"
    params: dict[str, str | int] = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Категория:{category}",
        "cmtype": "page",
        "cmlimit": 500,
        "format": "json"
    }
    members: set[str] = set()
    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            members.update([member['title'] for member in data['query']['categorymembers']])
            logger.debug(f"Получено {len(data['query']['categorymembers'])} заголовков через API")
            if 'continue' not in data:
                break
            params['cmcontinue'] = data['continue']['cmcontinue']
            time.sleep(0.05)
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            break
    logger.info(f"Всего получено {len(members)} заголовков через API")
    return members


def count_animals_by_letter() -> dict[str, int]:
    logger.info("Начало обработки категорий через API")
    start_time = time.time()
    letter_counts: dict[str, int] = defaultdict(int)

    titles = get_category_members_api("Животные_по_алфавиту")

    for title in titles:
        if title and title[0].upper() in RUS_ALPHABET:
            letter_counts[title[0].upper()] += 1
            logger.debug(f"Подсчитан: {title}")
        else:
            logger.debug(f"Пропущен: {title}")
    logger.info(f"Обработано {sum(letter_counts.values())} заголовков через API")
    logger.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
    return letter_counts


def write_to_csv(letter_counts: dict[str, int], filename: str = "beasts.csv"):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for letter in sorted(letter_counts.keys(),
                             key=lambda c: ORDER_RUS_ALPHABET[c]):
            writer.writerow([letter, letter_counts[letter]])
    logger.info(f"Результаты записаны в {filename}")


def main():
    letter_counts = count_animals_by_letter()
    write_to_csv(letter_counts, filename="beasts_sync.csv")


if __name__ == "__main__":
    main()
