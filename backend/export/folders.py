"""Optional native folder picker (tkinter). Falls back to the text field in the UI."""

from __future__ import annotations

from .errors import FolderPickerUnavailable


def pick_folder(initial_dir: str | None = None) -> str | None:
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError as exc:  # pragma: no cover - Windows Python ships tkinter
        raise FolderPickerUnavailable("tkinter is not available") from exc

    try:
        root = tkinter.Tk()
    except Exception as exc:  # noqa: BLE001 - headless/service session
        raise FolderPickerUnavailable("A native folder dialog could not be opened") from exc
    try:
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:  # noqa: BLE001
            pass
        selected = filedialog.askdirectory(parent=root, initialdir=initial_dir or "", mustexist=False)
        return selected or None
    finally:
        try:
            root.destroy()
        except Exception:  # noqa: BLE001
            pass
