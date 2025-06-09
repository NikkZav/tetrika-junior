import csv
import logging
import requests
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from .solution_sync import count_animals_by_letter, get_category_members_api, write_to_csv


# Отключаем логирование для тестов, чтобы не засорять вывод
logging.getLogger().setLevel(logging.CRITICAL)


@pytest.fixture
def mock_api_response() -> dict:
    """
    Фикстура для мокирования ответа API с пагинацией.
    """
    return {
        "query": {
            "categorymembers": [
                {"title": "Аардварк"},
                {"title": "Бегемот"},
                {"title": "123 Не животное"},
            ]
        },
        "continue": {"cmcontinue": "next_page"},
    }


@pytest.fixture
def mock_api_response_empty() -> dict:
    """
    Фикстура для мокирования пустого ответа API.
    """
    return {"query": {"categorymembers": []}}


@pytest.fixture
def tmp_csv_file(tmp_path: Path) -> Path:
    """
    Фикстура для создания временного CSV-файла.
    """
    return tmp_path / "test_beasts.csv"


def test_get_category_members_api_success(mock_api_response: dict) -> None:
    """
    Тестирует успешное получение заголовков с пагинацией.
    """
    mock_response = Mock()
    mock_response.json.side_effect = [
        mock_api_response,
        {"query": {"categorymembers": [{"title": "Волк"}]}},
    ]
    mock_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_response):
        titles = get_category_members_api("TestCategory")
        assert titles == {"Аардварк", "Бегемот", "123 Не животное", "Волк"}
        assert len(titles) == 4


def test_get_category_members_api_empty(mock_api_response_empty: dict) -> None:
    """
    Тестирует обработку пустой категории.
    """
    mock_response = Mock()
    mock_response.json.return_value = mock_api_response_empty
    mock_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_response):
        titles = get_category_members_api("EmptyCategory")
        assert titles == set()
        assert len(titles) == 0


def test_get_category_members_api_error() -> None:
    """
    Тестирует обработку ошибки API.
    """
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.RequestException("API error")

    with patch("requests.get", return_value=mock_response):
        titles = get_category_members_api("ErrorCategory")
        assert titles == set()
        assert len(titles) == 0


@pytest.mark.parametrize(
    "titles, expected_counts",
    [
        (
            ["Аардварк", "Бегемот", "Волк", "123 Не животное"],
            {"А": 1, "Б": 1, "В": 1},
        ),
        ([], {}),
        (["123 Не животное", "English Title"], {}),
    ],
    ids=["normal_case", "empty_list", "non_cyrillic"],
)
def test_count_animals_by_letter(titles: list[str], expected_counts: dict[str, int]) -> None:
    """
    Тестирует подсчёт страниц по кириллическим буквам.
    """
    with patch("task2.solution_sync.get_category_members_api", return_value=titles):
        result = count_animals_by_letter()
        assert result == expected_counts


def test_write_to_csv_normal(tmp_csv_file: Path) -> None:
    """
    Тестирует записка непустого словаря в CSV.
    """
    letter_counts = {"А": 2, "Б": 1, "В": 3}
    write_to_csv(letter_counts, str(tmp_csv_file))

    with open(tmp_csv_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert rows == [["А", "2"], ["Б", "1"], ["В", "3"]]


def test_write_to_csv_empty(tmp_csv_file: Path) -> None:
    """
    Тестирует записка пустого словаря в CSV.
    """
    letter_counts: dict[str, int] = {}
    write_to_csv(letter_counts, str(tmp_csv_file))

    with open(tmp_csv_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert rows == []
