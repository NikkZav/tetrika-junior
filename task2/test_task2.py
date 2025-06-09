import asyncio
import csv
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from .solution import count_animals_by_letter, fetch_titles, get_prefixes, write_to_csv


# Отключаем логирование для тестов
logging.getLogger().setLevel(logging.CRITICAL)


@pytest.fixture
def mock_api_response():
    """Фикстура для мокирования ответа API с пагинацией."""
    return {
        "query": {
            "categorymembers": [
                {"title": "Аардварк"},
                {"title": "Агути"},
                {"title": "Антилопа"},
            ]
        },
        "continue": {"cmcontinue": "next_page"},
    }


@pytest.fixture
def mock_api_response_empty():
    """Фикстура для мокирования пустого ответа API."""
    return {"query": {"categorymembers": []}}


@pytest.fixture
def tmp_csv_file(tmp_path: Path):
    """Фикстура для создания временного CSV-файла."""
    return tmp_path / "test_beasts.csv"


@pytest.mark.asyncio
async def test_get_prefixes():
    """Тестирует генерацию префиксов."""
    prefixes = get_prefixes(length=1)
    assert len(prefixes) == 33  # Количество букв в RUS_ALPHABET
    assert prefixes[:5] == ["А", "Б", "В", "Г", "Д"]
    prefixes = get_prefixes(length=2)
    assert len(prefixes) == 33 * 33  # Комбинации двух букв
    assert prefixes[0] == "АА"


@pytest.mark.asyncio
async def test_fetch_titles_success(mock_api_response):
    """Тестирует успешное получение заголовков с пагинацией."""
    mock_response = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=[
        mock_api_response,
        {"query": {"categorymembers": [{"title": "Аист"}]}},
    ])
    mock_response.raise_for_status = MagicMock(return_value=None)

    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response

    semaphore = asyncio.Semaphore(1)
    titles = {}
    await fetch_titles("А", "TestCategory", mock_session, semaphore, titles)
    assert titles == {"Аардварк": 1, "Агути": 1, "Антилопа": 1, "Аист": 1}
    assert len(titles) == 4


@pytest.mark.asyncio
async def test_fetch_titles_empty(mock_api_response_empty):
    """Тестирует обработку пустой категории."""
    mock_response = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_api_response_empty)
    mock_response.raise_for_status = MagicMock(return_value=None)

    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response

    semaphore = asyncio.Semaphore(1)
    titles = {}
    await fetch_titles("А", "EmptyCategory", mock_session, semaphore, titles)
    assert titles == {}
    assert len(titles) == 0


@pytest.mark.asyncio
async def test_fetch_titles_error():
    """Тестирует обработку ошибки API."""
    mock_response = MagicMock()
    mock_response.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("API error"))
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value = mock_response

    semaphore = asyncio.Semaphore(1)
    titles = {}
    await fetch_titles("А", "ErrorCategory", mock_session, semaphore, titles)
    assert titles == {}
    assert len(titles) == 0


@pytest.mark.asyncio
async def test_fetch_titles_429_empty(mock_api_response_empty):
    """Тестирует обработку ошибки 429 (Too Many Requests) и пустого ответа."""
    mock_response_429 = MagicMock()
    mock_response_429.__aenter__ = AsyncMock(return_value=mock_response_429)
    mock_response_429.__aexit__ = AsyncMock(return_value=None)
    mock_response_429.status = 429
    retry_after = 3
    mock_response_429.headers = {"Retry-After": str(retry_after)}
    mock_response_429.raise_for_status = MagicMock(return_value=None)

    mock_response_ok = MagicMock()
    mock_response_ok.__aenter__ = AsyncMock(return_value=mock_response_ok)
    mock_response_ok.__aexit__ = AsyncMock(return_value=None)
    mock_response_ok.status = 200
    mock_response_ok.json = AsyncMock(return_value=mock_api_response_empty)
    mock_response_ok.raise_for_status = MagicMock(return_value=None)

    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.side_effect = [mock_response_429, mock_response_ok]

    semaphore = asyncio.Semaphore(1)
    titles = {}
    with patch("asyncio.sleep", new=AsyncMock(return_value=None)) as mock_sleep:
        await fetch_titles("А", "TestCategory", mock_session, semaphore, titles)
        assert mock_sleep.called
        assert mock_sleep.call_count == 1
        assert mock_sleep.await_args == ((retry_after,),)
    assert titles == {}
    assert len(titles) == 0


@pytest.mark.asyncio
async def test_fetch_titles_429_non_empty():
    """Тест на обработку 429 с непустым ответом."""
    mock_response_429 = MagicMock()
    mock_response_429.__aenter__ = AsyncMock(return_value=mock_response_429)
    mock_response_429.__aexit__ = AsyncMock(return_value=None)
    mock_response_429.status = 429
    retry_after = 3
    mock_response_429.headers = {"Retry-After": str(retry_after)}
    mock_response_429.raise_for_status = MagicMock(return_value=None)

    mock_response_non_empty = MagicMock()
    mock_response_non_empty.__aenter__ = AsyncMock(return_value=mock_response_non_empty)
    mock_response_non_empty.__aexit__ = AsyncMock(return_value=None)
    mock_response_non_empty.status = 200
    mock_response_non_empty.json = AsyncMock(
        return_value={"query": {"categorymembers": [{"title": "Аист"}]}}
    )
    mock_response_non_empty.raise_for_status = MagicMock(return_value=None)

    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.get.side_effect = [mock_response_429, mock_response_non_empty]

    semaphore = asyncio.Semaphore(1)
    titles = {}
    with patch("asyncio.sleep", new=AsyncMock(return_value=None)) as mock_sleep:
        await fetch_titles("А", "TestCategory", mock_session, semaphore, titles)
        assert mock_sleep.called
        assert mock_sleep.call_count == 2
        assert mock_sleep.await_args_list == [((retry_after,),), ((0.5,),)]
    assert titles == {"Аист": 1}
    assert len(titles) == 1


@pytest.mark.parametrize(
    "titles, expected_counts",
    [
        (
            {"Аардварк": 1, "Бегемот": 1, "Волк": 1, "123 Не животное": 1},
            {"А": 1, "Б": 1, "В": 1},
        ),
        ({}, {}),
        ({"123 Не животное": 1, "English Title": 1}, {}),
    ],
    ids=["normal_case", "empty_dict", "non_cyrillic"],
)
@pytest.mark.asyncio
async def test_count_animals_by_letter(titles, expected_counts):
    """Тестирует подсчёт страниц по кириллическим буквам."""
    with patch("task2.solution.get_category_members_api", return_value=titles):
        result = count_animals_by_letter()
        assert result == expected_counts


def test_write_to_csv_normal(tmp_csv_file):
    """Тестирует запись непустого словаря в CSV."""
    letter_counts = {"А": 2, "Б": 1, "В": 3}
    write_to_csv(letter_counts, str(tmp_csv_file))
    with open(tmp_csv_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert rows == [["А", "2"], ["Б", "1"], ["В", "3"]]


def test_write_to_csv_empty(tmp_csv_file):
    """Тестирует запись пустого словаря в CSV."""
    letter_counts = {}
    write_to_csv(letter_counts, str(tmp_csv_file))
    with open(tmp_csv_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert rows == []
