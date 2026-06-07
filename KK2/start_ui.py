"""Open a small desktop window for Oraklet.

Terminal command:
    uv run python start_ui.py
"""

from __future__ import annotations

import json
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from typing import Any

from app.chain.direct_stats import answer_direct_stats_question
from app.chain.pipeline import MODEL_NAME, oraklet
from app.data import DatasetError, get_stats, load_csv
from app.schemas import PromptBuilderInput


class OrakletWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected_file = tk.StringVar(value="No CSV selected.")
        self.status = tk.StringVar(value="Ready.")

        self._build_window()

    def _build_window(self) -> None:
        self.root.title("KK2 Oraklet")
        self.root.geometry("760x560")
        self.root.minsize(620, 460)

        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text="KK2 Oraklet", font=("Segoe UI", 18, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            frame,
            text="Upload a CSV, check stats, and ask questions without Swagger.",
        )
        subtitle.pack(anchor=tk.W, pady=(0, 14))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)

        ttk.Button(buttons, text="Health", command=self.check_health).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Choose CSV", command=self.choose_file).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        ttk.Button(buttons, text="Upload", command=self.upload_file).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        ttk.Button(buttons, text="Stats", command=self.show_stats).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        ttk.Label(frame, textvariable=self.selected_file).pack(anchor=tk.W, pady=(10, 10))

        ttk.Label(frame, text="Question").pack(anchor=tk.W)
        self.question_box = tk.Text(frame, height=4, wrap=tk.WORD)
        self.question_box.insert("1.0", "Vad ar hogsta sales value?")
        self.question_box.pack(fill=tk.X)

        ttk.Button(frame, text="Ask Oraklet", command=self.ask_question).pack(
            anchor=tk.W,
            pady=(10, 12),
        )

        ttk.Label(frame, text="Response").pack(anchor=tk.W)
        self.response_box = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=14)
        self.response_box.pack(fill=tk.BOTH, expand=True)
        self.response_box.insert(tk.END, "Nothing yet.")

        ttk.Label(frame, textvariable=self.status).pack(anchor=tk.W, pady=(8, 0))

    def check_health(self) -> None:
        self._show_result({"status": "ok"})
        self.status.set("API logic is available.")

    def choose_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Choose CSV",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if file_path:
            self.selected_file.set(file_path)

    def upload_file(self) -> None:
        file_path = Path(self.selected_file.get())
        if not file_path.exists():
            self._show_error("Choose a CSV first.")
            return

        def work() -> dict[str, Any]:
            with file_path.open("rb") as file:
                metadata = load_csv(file)
            return metadata.model_dump()

        self._run("Uploading CSV...", work, "Dataset uploaded.")

    def show_stats(self) -> None:
        def work() -> dict[str, dict[str, Any]]:
            stats = get_stats()
            if stats is None:
                raise RuntimeError("No dataset has been uploaded.")
            return stats

        self._run("Loading stats...", work, "Stats loaded.")

    def ask_question(self) -> None:
        question = self.question_box.get("1.0", tk.END).strip()
        if not question:
            self._show_error("Write a question first.")
            return

        def work() -> dict[str, str]:
            stats = get_stats()
            if stats is None:
                raise RuntimeError("Upload a dataset before asking questions.")

            direct_answer = answer_direct_stats_question(question, stats)
            if direct_answer is not None:
                answer = direct_answer
            else:
                result = oraklet.invoke(PromptBuilderInput(question=question, stats=stats))
                answer = result.answer

            return {
                "question": question,
                "answer": answer,
                "model": MODEL_NAME,
            }

        self._run("Asking Oraklet...", work, "Answer ready.")

    def _run(
        self,
        pending_status: str,
        work: Callable[[], Any],
        done_status: str,
    ) -> None:
        self.status.set(pending_status)

        def worker() -> None:
            try:
                result = work()
            except (DatasetError, RuntimeError, ValueError) as exc:
                self.root.after(0, lambda: self._show_error(str(exc)))
            else:
                self.root.after(0, lambda: self._finish(result, done_status))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, result: Any, status: str) -> None:
        self._show_result(result)
        self.status.set(status)

    def _show_result(self, result: Any) -> None:
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, indent=2)

        self.response_box.delete("1.0", tk.END)
        self.response_box.insert(tk.END, text)

    def _show_error(self, message: str) -> None:
        self.status.set(f"Error: {message}")
        self._show_result({"error": message})


def main() -> None:
    root = tk.Tk()
    OrakletWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
