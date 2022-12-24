"""
Useful exceptions
"""


class SelectorError(ValueError):

    def __init__(self, selector: str) -> None:
        self._selector = selector

    def __str__(self) -> str:
        return "Given selector doesn't work. Selector: %s" % self._selector


class TaskNotFound(Exception):

    def __init__(self, task_name: str) -> None:
        self._task_name = task_name

    def __str__(self) -> str:
        return "Task %s not found" % self._task_name
