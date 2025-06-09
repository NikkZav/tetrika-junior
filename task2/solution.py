import asyncio
import csv
import logging
import itertools
import time
from collections import defaultdict
from urllib.parse import urlencode

import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RUS_ALPHABET = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
ORDER_RUS_ALPHABET = {letter: index for index, letter in enumerate(RUS_ALPHABET)}


def get_prefixes(prefix_alphabet: str = RUS_ALPHABET, length: int = 1) -> list[str]:
    return [''.join(letters) for letters in itertools.product(prefix_alphabet, repeat=length)]


async def fetch_titles(prefix: str, category: str, session: aiohttp.ClientSession,
                       semaphore: asyncio.Semaphore, titles: dict[str, int]) -> None:
    """Собирает заголовки для префикса, добавляя в общий словарь."""
    url = "https://ru.wikipedia.org/w/api.php"
    params: dict[str, str | int] = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Категория:{category}",
        "cmtype": "page",
        "cmlimit": 500,
        "format": "json",
        "cmstartsortkeyprefix": prefix,
    }
    async with semaphore:
        full_url = f"{url}?{urlencode(params)}"
        logger.info(f"Запрос к API для префикса '{prefix}'")
        logger.debug(f"Полный URL: {full_url}")
        while True:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 429:
                        retry_after = float(response.headers.get("Retry-After", 2))
                        logger.warning(f"429 для '{prefix}', ждём {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    data = await response.json()
                    logger.debug(f"Ответ API для '{prefix}': {str(data)[:300]}...")
                    if "error" in data:
                        logger.error(f"API ошибка для '{prefix}': {data['error']}")
                        return
                    if "query" not in data or "categorymembers" not in data["query"]:
                        logger.error(f"Некорректный ответ для '{prefix}'")
                        return
                    new_titles = [page["title"] for page in data["query"]["categorymembers"]]
                    if not new_titles:
                        logger.debug(f"Нет заголовков для '{prefix}'")
                        return
                    logger.debug(f"Добавление {len(new_titles)} "
                                 f"заголовков для '{prefix}': {new_titles[:5]}...")
                    for title in new_titles:
                        titles[title] = titles.get(title, 0) + 1
                    await asyncio.sleep(0.5)  # Задержка между запросами
                    if 'continue' in data and new_titles[-1][:len(prefix)].upper() == prefix:
                        params['cmcontinue'] = data['continue']['cmcontinue']
                        logger.info(f"Снова запрос для префикса '{prefix}', "
                                    f"(след. страница т.к. ещё есть заголовки на {prefix}...)")
                    else:
                        return
            except aiohttp.ClientError as e:
                logger.error(f"Ошибка для '{prefix}': {e}")
                return


def get_category_members_api(category: str) -> dict[str, int]:
    """Собирает заголовки асинхронно."""
    titles: dict[str, int] = {}
    # Устанавлием ограничение для баланса между скоростью и нагрузкой на сервер wikipedia
    semaphore = asyncio.Semaphore(33 * 3)  # при value более 500 - ошибка 429
    # Если появляется WARNING - 429, то либо уменьшить значение семафора,
    # либо увеличить время задержки между запросами - await asyncio.sleep в fetch_titles

    async def gather_titles():
        async with aiohttp.ClientSession() as session:
            prefixes = get_prefixes(length=1)
            tasks = [
                fetch_titles(prefix, category, session, semaphore, titles)
                for prefix in prefixes
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(gather_titles())

    return titles


def count_animals_by_letter() -> dict[str, int]:
    logger.info("Начало обработки категорий через API асинхронно")
    start_time = time.time()
    letter_counts: dict[str, int] = defaultdict(int)

    titles = get_category_members_api("Животные по алфавиту")

    if titles:
        overlap_ratio = sum(titles.values()) / len(titles)
        logger.info(f"Собрано {len(titles)} уникальных заголовков, "
                    f"коэффициент пересечений: {overlap_ratio:.2f}")
    else:
        logger.warning("Заголовки не собраны")

    for title in titles:
        if title and title[0].upper() in RUS_ALPHABET:
            letter_counts[title[0].upper()] += 1
    logger.info(f"Подсчитано заголовков: {sum(letter_counts.values())}")
    logger.info(f"Время выполнения: {time.time() - start_time:.2f} секунд")
    return letter_counts


def write_to_csv(letter_counts: dict[str, int], filename: str = "beasts.csv") -> None:
    """Записывает результаты в CSV."""
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        logger.info
        for letter in sorted(letter_counts.keys(),
                             key=lambda c: ORDER_RUS_ALPHABET[c]):
            writer.writerow([letter, letter_counts[letter]])
    logger.info(f"Результаты записаны в {filename}")


def main():
    letter_counts = count_animals_by_letter()
    write_to_csv(letter_counts, filename="beasts.csv")


if __name__ == "__main__":
    main()
