"""Open a small desktop window for Cat Data Analyst Deluxe.

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


PROJECT_NAME = "Cat Data Analyst Deluxe"
IMAGE_DIR = Path(__file__).parent / "images"
LOGO_PATH = IMAGE_DIR / "Logo.png"
HEALTH_OK_PATH = IMAGE_DIR / "HealthOK.png"
HEALTH_NOT_OK_PATH = IMAGE_DIR / "HealthNOTOk.png"
CAT_THINKING_PATH = IMAGE_DIR / "CatThinking.png"
CAT_RESPONSE_PATH = IMAGE_DIR / "CatResponse.png"
SAMPLE_CSV_PATH = Path(__file__).parent / "CSV" / "SuperMarket Data.csv"


class CatDataAnalystWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.logo_image: tk.PhotoImage | None = None
        self.status_images: dict[str, tk.PhotoImage] = {}
        self.selected_file_path: Path | None = None
        self.selected_file = tk.StringVar(value="No file selected")
        self.dataset_status = tk.StringVar(value="Dataset: not uploaded")
        self.status_panel_text = tk.StringVar(value="Status: idle")
        self.status = tk.StringVar(value="Ready.")
        self.is_busy = False
        self.loading_frames = ("◐", "◓", "◑", "◒")
        self.loading_frame_index = 0
        self.loading_after_id: str | None = None

        self._build_window()

    def _build_window(self) -> None:
        self.root.title(PROJECT_NAME)
        self.root.geometry("820x620")
        self.root.minsize(680, 520)
        self._set_window_icon()

        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(frame)
        header.pack(fill=tk.X)

        title_block = ttk.Frame(header)
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title = ttk.Label(title_block, text=PROJECT_NAME, font=("Segoe UI", 18, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            title_block,
            text="This cat works for free. He does not have a degree as a data analyst.",
        )
        subtitle.pack(anchor=tk.W)

        top_area = ttk.Frame(frame)
        top_area.pack(fill=tk.X, pady=(16, 10))

        csv_box = ttk.LabelFrame(top_area, text="CSV", padding=10)
        csv_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        file_row = ttk.Frame(csv_box)
        file_row.pack(fill=tk.X)

        ttk.Button(file_row, text="Choose CSV", command=self.choose_file).pack(side=tk.LEFT)
        ttk.Button(file_row, text="Sample CSV", command=self.choose_sample_csv).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        ttk.Label(csv_box, text="Selected file:").pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(csv_box, textvariable=self.selected_file, font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W
        )
        ttk.Label(csv_box, textvariable=self.dataset_status).pack(anchor=tk.W, pady=(6, 0))
        ttk.Button(csv_box, text="Display data", command=self.show_stats).pack(
            anchor=tk.W,
            pady=(10, 0),
        )

        status_box = ttk.LabelFrame(top_area, text="Status", padding=10)
        status_box.pack(side=tk.RIGHT, fill=tk.BOTH)

        ttk.Label(
            status_box,
            textvariable=self.status_panel_text,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.CENTER)
        self.status_image_label = ttk.Label(status_box)
        self.status_image_label.pack(anchor=tk.CENTER, pady=(8, 8))
        ttk.Button(status_box, text="Health", command=self.check_health).pack(anchor=tk.CENTER)
        self._load_status_images()

        ask_box = ttk.LabelFrame(frame, text="Ask", padding=10)
        ask_box.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(ask_box, text="Question").pack(anchor=tk.W)
        self.question_box = tk.Text(ask_box, height=4, wrap=tk.WORD)
        self.question_box.insert("1.0", "Choose and upload a CSV first.")
        self.question_box.pack(fill=tk.X)

        ttk.Button(ask_box, text="Ask analyst", command=self.ask_question).pack(
            anchor=tk.W,
            pady=(8, 0),
        )

        response_box = ttk.LabelFrame(frame, text="Output", padding=10)
        response_box.pack(fill=tk.BOTH, expand=True)

        self.response_box = scrolledtext.ScrolledText(response_box, wrap=tk.WORD, height=14)
        self.response_box.pack(fill=tk.BOTH, expand=True)
        self.response_box.insert(tk.END, "Nothing yet.")

        ttk.Label(frame, textvariable=self.status).pack(anchor=tk.W, pady=(8, 0))

    def check_health(self) -> None:
        self._show_result({"status": "ok"})
        self._set_status_panel("Health OK", "health_ok")
        self.status.set("App logic is available.")

    def choose_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Choose CSV",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if file_path:
            self._select_csv(Path(file_path))

    def choose_sample_csv(self) -> None:
        if not SAMPLE_CSV_PATH.exists():
            self._show_error(f"Sample CSV was not found: {SAMPLE_CSV_PATH}")
            return

        self._select_csv(SAMPLE_CSV_PATH)

    def _select_csv(self, file_path: Path) -> None:
        self.selected_file_path = file_path
        self.selected_file.set(f"{file_path.name} ({file_path.parent})")
        self.dataset_status.set("Dataset: selected, uploading...")
        self.upload_file()

    def upload_file(self) -> None:
        if self.selected_file_path is None or not self.selected_file_path.exists():
            self._show_error("Choose a CSV first.")
            return

        def work() -> dict[str, Any]:
            with self.selected_file_path.open("rb") as file:
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

        self._run("Asking analyst...", work, "Answer ready.")

    def _set_window_icon(self) -> None:
        if not LOGO_PATH.exists():
            return

        try:
            self.logo_image = tk.PhotoImage(file=LOGO_PATH)
            self.root.iconphoto(True, self.logo_image)
        except tk.TclError:
            self.logo_image = None

    def _load_status_images(self) -> None:
        image_paths = {
            "health_ok": HEALTH_OK_PATH,
            "health_not_ok": HEALTH_NOT_OK_PATH,
            "thinking": CAT_THINKING_PATH,
            "response": CAT_RESPONSE_PATH,
        }
        for name, path in image_paths.items():
            image = self._load_image(path, max_width=150, max_height=110)
            if image is not None:
                self.status_images[name] = image

    def _load_image(
        self,
        path: Path,
        max_width: int,
        max_height: int,
    ) -> tk.PhotoImage | None:
        if not path.exists():
            return None

        try:
            image = tk.PhotoImage(file=path)
        except tk.TclError:
            return None

        scale = max(
            1,
            (image.width() + max_width - 1) // max_width,
            (image.height() + max_height - 1) // max_height,
        )
        if scale > 1:
            image = image.subsample(scale, scale)

        return image

    def _set_status_panel(self, text: str, image_name: str | None = None) -> None:
        self.status_panel_text.set(text)
        image = self.status_images.get(image_name or "")
        self.status_image_label.configure(image=image)

    def _run(
        self,
        pending_status: str,
        work: Callable[[], Any],
        done_status: str,
    ) -> None:
        if self.is_busy:
            self.status.set("Wait for the current task to finish.")
            return

        self.is_busy = True
        self.status.set(pending_status)
        if pending_status == "Asking analyst...":
            self._start_loading_status()

        def worker() -> None:
            try:
                result = work()
            except (DatasetError, RuntimeError, ValueError) as exc:
                message = str(exc)
                self.root.after(0, lambda: self._show_error(message))
            else:
                self.root.after(0, lambda: self._finish(result, done_status))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, result: Any, status: str) -> None:
        self.is_busy = False
        self._stop_loading_status()
        self._show_result(result)
        if status == "Answer ready.":
            self._set_status_panel("Cat answered", "response")
        if status == "Stats loaded.":
            self._set_status_panel("Here is your data.", "response")
        if status == "Dataset uploaded." and isinstance(result, dict):
            rows = result.get("rows", "?")
            columns = len(result.get("columns", []))
            self.dataset_status.set(f"Dataset: uploaded ({rows} rows, {columns} columns)")
            self._set_question_suggestion()
        self.status.set(status)

    def _show_result(self, result: Any) -> None:
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, indent=2)

        self.response_box.delete("1.0", tk.END)
        self.response_box.insert(tk.END, text)

    def _show_error(self, message: str) -> None:
        self.is_busy = False
        self._stop_loading_status()
        if message.startswith("Choose a CSV") or "CSV" in message:
            self.dataset_status.set("Dataset: not ready")
        if "SmolLM" in message or "model" in message.casefold():
            self._set_status_panel("Health NOT OK", "health_not_ok")
        self.status.set(f"Error: {message}")
        self._show_result({"error": message})

    def _set_question_suggestion(self) -> None:
        stats = get_stats()
        if stats is None:
            return

        numeric_column = next(
            (
                column
                for column, metrics in stats.items()
                if metrics.get("mean") not in ("", None)
            ),
            None,
        )

        if numeric_column is not None:
            question = f"What is the average {numeric_column} value?"
        else:
            text_column = next(
                (
                    column
                    for column, metrics in stats.items()
                    if metrics.get("top") not in ("", None)
                ),
                None,
            )
            if text_column is None:
                return
            question = f"What is the most common {text_column} value?"

        self.question_box.delete("1.0", tk.END)
        self.question_box.insert("1.0", question)

    def _start_loading_status(self) -> None:
        self.loading_frame_index = 0
        self._set_status_panel("Cat is thinking", "thinking")
        self._animate_loading_status()

    def _animate_loading_status(self) -> None:
        if not self.is_busy:
            return

        frame = self.loading_frames[self.loading_frame_index]
        self.loading_frame_index = (self.loading_frame_index + 1) % len(self.loading_frames)
        self.status_panel_text.set(f"Cat is thinking {frame}")
        self.loading_after_id = self.root.after(180, self._animate_loading_status)

    def _stop_loading_status(self) -> None:
        if self.loading_after_id is None:
            return

        self.root.after_cancel(self.loading_after_id)
        self.loading_after_id = None


def main() -> None:
    root = tk.Tk()
    CatDataAnalystWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
