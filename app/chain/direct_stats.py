from __future__ import annotations

from numbers import Real
from typing import Any


METRIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "max",
        (
            "highest",
            "largest",
            "maximum",
            "max",
            "biggest",
            "hogsta",
            "högsta",
            "hogst",
            "högst",
            "storsta",
            "största",
            "storst",
            "störst",
        ),
    ),
    (
        "min",
        (
            "lowest",
            "smallest",
            "minimum",
            "min",
            "lagsta",
            "lägsta",
            "lagst",
            "lägst",
            "minsta",
            "minst",
        ),
    ),
    (
        "mean",
        (
            "average",
            "mean",
            "medel",
            "medelvarde",
            "medelvärde",
            "genomsnitt",
            "snitt",
        ),
    ),
    (
        "50%",
        ("median", "medianen", "medial", "middle", "midpoint"),
    ),
    (
        "count",
        ("count", "number of", "how many", "antal", "hur manga", "hur många"),
    ),
    ("top", ("most common", "top", "mode", "vanligaste", "mest vanlig")),
    ("freq", ("frequency", "freq", "frekvens")),
)

METRIC_LABELS = {
    "50%": "median",
}


def answer_direct_stats_question(
    question: str,
    stats: dict[str, dict[str, Any]],
) -> str | None:
    """Answer direct column+metric questions without relying on the LLM."""
    if _asks_for_row_or_category(question):
        return None

    metric = _find_requested_metric(question)
    if metric is None:
        return None

    column = _find_single_requested_column(question, stats)
    if column is None:
        return None

    value = stats[column].get(metric)
    if value == "" or value is None:
        return f"The uploaded stats do not contain {metric} for {column}."

    metric_label = METRIC_LABELS.get(metric, metric)
    return f"{column} {metric_label} is {_format_value(value)}."


def _find_requested_metric(question: str) -> str | None:
    question_text = f" {question.casefold()} "
    for metric, aliases in METRIC_ALIASES:
        if any(alias in question_text for alias in aliases):
            return metric

    return None


def _asks_for_row_or_category(question: str) -> bool:
    normalized_question = _normalize(question)
    return normalized_question.startswith(("which ", "who ", "where ", "vilken ", "vilket ", "vem ", "var "))


def _find_single_requested_column(
    question: str,
    stats: dict[str, dict[str, Any]],
) -> str | None:
    normalized_question = _normalize(question)
    columns_by_specificity = sorted(stats, key=lambda column: len(str(column)), reverse=True)
    matches: list[str] = []

    for column in columns_by_specificity:
        normalized_column = _normalize(column)
        if normalized_column and _column_matches_question(normalized_column, normalized_question):
            matches.append(column)

    if len(matches) != 1:
        return None

    return matches[0]


def _column_matches_question(normalized_column: str, normalized_question: str) -> bool:
    if normalized_column in normalized_question:
        return True

    column_tokens = normalized_column.split()
    question_tokens = set(normalized_question.split())

    return all(_token_or_simple_singular(token) in question_tokens for token in column_tokens)


def _token_or_simple_singular(token: str) -> str:
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]

    return token


def _normalize(value: object) -> str:
    return " ".join(str(value).casefold().replace("_", " ").split())


def _format_value(value: Any) -> str:
    if isinstance(value, Real) and not isinstance(value, bool):
        number = float(value)
        if number.is_integer():
            return str(int(number))

        return f"{number:.2f}"

    return str(value)
