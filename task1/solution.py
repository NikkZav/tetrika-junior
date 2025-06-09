from inspect import signature


def strict(func):
    sig = signature(func)

    def check_parameter_type(param_name, arg_value):
        expected_type = func.__annotations__.get(param_name)
        if expected_type and type(arg_value) is not expected_type:
            raise TypeError(
                f"Аргумент {param_name} должен быть типа {expected_type.__name__}, "
                f"получен {type(arg_value).__name__}"
            )

    def wrapper(*args, **kwargs):
        for (param_name, _), arg_value in zip(sig.parameters.items(), args):
            check_parameter_type(param_name, arg_value)

        for arg_name, arg_value in kwargs.items():
            check_parameter_type(arg_name, arg_value)

        return func(*args, **kwargs)

    return wrapper


@strict
def sum_two(a: int, b: int) -> int:
    return a + b


try:
    print(sum_two(1, 2))
    print(sum_two(1, 2.4))
except TypeError as e:
    print(e)
