"""Необязательное углубление Python Core: типизированный декоратор времени."""
from functools import wraps
from time import perf_counter
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def timed(action: Callable[P, R]) -> Callable[P, R]:
    """Замеряет длительность вызова, сохраняя сигнатуру и метаданные.

    last_seconds — диагностическое поле на обёртке. Не меняет результат вызова.
    """
    @wraps(action)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        try:
            return action(*args, **kwargs)
        finally:
            wrapper.last_seconds = perf_counter() - start  # type: ignore[attr-defined]
    wrapper.last_seconds = 0.0  # type: ignore[attr-defined]
    return wrapper
