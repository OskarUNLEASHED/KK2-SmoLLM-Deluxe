from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
NextOutputT = TypeVar("NextOutputT")


class Runnable(Generic[InputT, OutputT], ABC):
    """A typed processing step that can be chained with other runnables."""

    @abstractmethod
    def invoke(self, input_data: InputT) -> OutputT:
        """Run the step and return its typed output."""

    def __call__(self, input_data: InputT) -> OutputT:
        return self.invoke(input_data)

    def __or__(
        self,
        next_step: Runnable[OutputT, NextOutputT],
    ) -> RunnableSequence[InputT, NextOutputT]:
        return RunnableSequence(self, next_step)


class RunnableSequence(Runnable[InputT, OutputT]):
    """Runs several Runnable steps in order."""

    def __init__(self, *steps: Runnable[object, object]) -> None:
        if len(steps) < 2:
            raise ValueError("RunnableSequence needs at least two steps.")

        self.steps: list[Runnable[object, object]] = []
        for step in steps:
            if isinstance(step, RunnableSequence):
                self.steps.extend(step.steps)
            else:
                self.steps.append(step)

    def invoke(self, input_data: InputT) -> OutputT:
        current: object = input_data
        for step in self.steps:
            current = step.invoke(current)

        return current  # type: ignore[return-value]

    def __or__(
        self,
        next_step: Runnable[OutputT, NextOutputT],
    ) -> RunnableSequence[InputT, NextOutputT]:
        return RunnableSequence(*self.steps, next_step)
