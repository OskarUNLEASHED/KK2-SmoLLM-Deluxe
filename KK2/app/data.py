from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

import pandas as pd
from pandas import DataFrame

from app.config import get_settings
from app.schemas import UploadMetadata


@dataclass
class DatasetStore:
    dataframe: DataFrame | None = None


class DatasetError(Exception):
    """Raised when the uploaded dataset cannot be used."""


store = DatasetStore()


def load_csv(file: BinaryIO) -> UploadMetadata:
    _validate_file_size(file)

    try:
        dataframe = pd.read_csv(file)
    except pd.errors.EmptyDataError as exc:
        raise DatasetError("The uploaded CSV file is empty.") from exc
    except UnicodeDecodeError as exc:
        raise DatasetError("The uploaded CSV file could not be decoded as text.") from exc
    except pd.errors.ParserError as exc:
        raise DatasetError("The uploaded CSV file could not be parsed.") from exc

    if dataframe.empty:
        raise DatasetError("The uploaded CSV file contains no data rows.")

    store.dataframe = dataframe
    return metadata_for(dataframe)


def _validate_file_size(file: BinaryIO) -> None:
    current_position = file.tell()
    file.seek(0, 2)
    size = file.tell()
    file.seek(current_position)

    max_size = get_settings().max_upload_size_bytes
    if size > max_size:
        raise DatasetError(
            f"The uploaded CSV file is too large. Max size is {_format_bytes(max_size)}."
        )


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} bytes"

    size_as_float = float(size)
    for unit in ("KB", "MB", "GB"):
        size_as_float /= 1024
        if size_as_float < 1024:
            return f"{size_as_float:.1f} {unit}"

    return f"{size_as_float:.1f} TB"


def metadata_for(dataframe: DataFrame) -> UploadMetadata:
    return UploadMetadata(
        rows=len(dataframe),
        columns=list(dataframe.columns),
        dtypes={column: str(dtype) for column, dtype in dataframe.dtypes.items()},
    )


def has_dataset() -> bool:
    return store.dataframe is not None


def get_dataset() -> DataFrame | None:
    return store.dataframe


def get_stats() -> dict[str, dict[str, object]] | None:
    if store.dataframe is None:
        return None

    return store.dataframe.describe(include="all").fillna("").to_dict()


def clear_dataset() -> None:
    store.dataframe = None
