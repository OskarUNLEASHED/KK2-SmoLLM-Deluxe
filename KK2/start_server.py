"""I am not afraid to admit I am giga lazy, I use this to start the FastAPI server faster.

Click the green run button next to this file in DataSpell.

Equivalent terminal command:
    uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
