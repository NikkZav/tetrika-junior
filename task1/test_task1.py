import pytest

from .solution import strict


def add_numbers(a: int, b: float) -> float:
    return a + b


def check_string(s: str, flag: bool) -> str:
    return s if flag else s.upper()


@pytest.mark.parametrize(
    "func, args, kwargs, expected_result",
    [
        # Тесты для add_numbers
        (add_numbers, (1, 2.0), {}, 3.0),
        (add_numbers, (), {"a": 5, "b": 10.5}, 15.5),
        (add_numbers, (0, -1.0), {}, -1.0),
        # Тесты для check_string
        (check_string, ("abc", True), {}, "abc"),
        (check_string, (), {"s": "xyz", "flag": False}, "XYZ"),
        (check_string, ("test", False), {}, "TEST"),
    ],
    ids=[
        "add_numbers_positional",
        "add_numbers_kwargs",
        "add_numbers_negative",
        "check_string_positional_true",
        "check_string_kwargs_false",
        "check_string_positional_false",
    ]
)
def test_strict_correct_types(func, args, kwargs, expected_result):
    """Тестирует декоратор strict с корректными типами аргументов."""
    decorated_func = strict(func)
    result = decorated_func(*args, **kwargs)
    assert result == expected_result, f"Ожидалось {expected_result}, получено {result}"


@pytest.mark.parametrize(
    "func, args, kwargs, expected_error",
    [
        # Тесты для add_numbers
        (add_numbers, (1, 2), {}, "Аргумент b должен быть типа float, получен int"),
        (add_numbers, (1.0, 2.0), {}, "Аргумент a должен быть типа int, получен float"),
        (add_numbers, (1, "2.0"), {}, "Аргумент b должен быть типа float, получен str"),
        (add_numbers, (), {"a": 1, "b": True}, "Аргумент b должен быть типа float, получен bool"),
        # Тесты для check_string
        (check_string, (123, True), {}, "Аргумент s должен быть типа str, получен int"),
        (check_string, ("abc", 1), {}, "Аргумент flag должен быть типа bool, получен int"),
        (check_string, (), {"s": True, "flag": True},
         "Аргумент s должен быть типа str, получен bool"),
        (check_string, ("xyz", 1.0), {}, "Аргумент flag должен быть типа bool, получен float"),
    ],
    ids=[
        "add_numbers_int_b",
        "add_numbers_float_a",
        "add_numbers_string_b",
        "add_numbers_bool_b_kwargs",
        "check_string_int_s",
        "check_string_int_flag",
        "check_string_bool_s_kwargs",
        "check_string_float_flag",
    ]
)
def test_strict_incorrect_types(func, args, kwargs, expected_error):
    """Тестирует декоратор strict с некорректными типами аргументов."""
    decorated_func = strict(func)
    with pytest.raises(TypeError) as exc_info:
        decorated_func(*args, **kwargs)
    assert str(exc_info.value) == expected_error, f"Ожидалась ошибка: {expected_error}"
