from inspect import signature
from functools import wraps
from typing import Callable


def strict(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_kwargs = {
            **{param_name: arg_value for (param_name, _), arg_value
               in zip(signature(func).parameters.items(), args)},
            **kwargs
        }

        for arg_name, arg_value in args_kwargs.items():
            expected_type = func.__annotations__.get(arg_name)
            if expected_type and type(arg_value) is not expected_type:
                raise TypeError(
                    f"Аргумент {arg_name} должен быть типа {expected_type.__name__}, "
                    f"получен {type(arg_value).__name__}"
                )

        return func(*args, **kwargs)

    return wrapper


@strict
def sum_two(a: int, b: int) -> int:
    """Сумма двух целых чисел"""
    return a + b


try:
    print(sum_two(1, 2))
    print(sum_two(1, 2.4))
except TypeError as e:
    print(e)
