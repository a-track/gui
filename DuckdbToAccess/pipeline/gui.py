from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from pipeline.runner import run_pipeline


def _default_duckdb_path() -> str:
    p = Path("data.duckdb")
    return str(p.resolve()) if p.exists() else ""


def _default_access_path() -> str:
    p = Path("semantic.accdb")
    return str(p.resolve())


def launch_gui() -> None:
    root = tk.Tk()
    root.title("DuckDB → Access Export")
    root.resizable(False, False)

    padding = {"padx": 8, "pady": 4}

    # DuckDB source
    tk.Label(root, text="DuckDB source file:").grid(row=0, column=0, sticky="w", **padding)
    duckdb_var = tk.StringVar(value=_default_duckdb_path())
    duckdb_entry = tk.Entry(root, width=55, textvariable=duckdb_var)
    duckdb_entry.grid(row=0, column=1, **padding)

    def browse_duckdb() -> None:
        filename = filedialog.askopenfilename(
            title="Select DuckDB file",
            filetypes=[("DuckDB database", "*.duckdb"), ("All files", "*.*")],
        )
        if filename:
            duckdb_var.set(filename)

    tk.Button(root, text="Browse…", command=browse_duckdb).grid(row=0, column=2, **padding)

    # Access output
    tk.Label(root, text="Access output file:").grid(row=1, column=0, sticky="w", **padding)
    access_var = tk.StringVar(value=_default_access_path())
    access_entry = tk.Entry(root, width=55, textvariable=access_var)
    access_entry.grid(row=1, column=1, **padding)

    def browse_access() -> None:
        filename = filedialog.asksaveasfilename(
            title="Save Access database as",
            defaultextension=".accdb",
            filetypes=[("Access database", "*.accdb"), ("All files", "*.*")],
            initialfile="semantic.accdb",
        )
        if filename:
            access_var.set(filename)

    tk.Button(root, text="Browse…", command=browse_access).grid(row=1, column=2, **padding)

    overwrite_var = tk.BooleanVar(value=True)
    tk.Checkbutton(root, text="Overwrite if exists", variable=overwrite_var).grid(
        row=2, column=1, sticky="w", **padding
    )

    status_var = tk.StringVar(value="Ready.")
    status_label = tk.Label(root, textvariable=status_var, fg="gray")
    status_label.grid(row=3, column=0, columnspan=3, sticky="w", **padding)

    def run_clicked() -> None:
        duckdb_path = duckdb_var.get().strip()
        access_path = access_var.get().strip()

        if not duckdb_path:
            messagebox.showerror("Missing DuckDB", "Please choose a DuckDB source file.")
            return
        if not Path(duckdb_path).exists():
            messagebox.showerror("DuckDB not found", f"DuckDB file not found:\n{duckdb_path}")
            return
        if not access_path:
            messagebox.showerror("Missing Access target", "Please choose an Access output file.")
            return

        status_var.set("Running pipeline… this may take a moment.")
        root.update_idletasks()

        def worker() -> None:
            try:
                run_pipeline(
                    duckdb_path=Path(duckdb_path),
                    sql_dir=Path("SQL"),
                    access_out=Path(access_path),
                    access_overwrite=overwrite_var.get(),
                    csv_out_dir=None,
                )
            except Exception as e:  # pragma: no cover
                def on_error() -> None:
                    status_var.set("Error.")
                    messagebox.showerror("Pipeline failed", str(e))

                root.after(0, on_error)
            else:
                def on_success() -> None:
                    status_var.set("Done.")
                    messagebox.showinfo(
                        "Success",
                        f"Access database created:\n{Path(access_path).resolve()}",
                    )

                root.after(0, on_success)

        threading.Thread(target=worker, daemon=True).start()

    tk.Button(root, text="Run", width=12, command=run_clicked).grid(
        row=2, column=2, sticky="e", **padding
    )

    root.mainloop()


if __name__ == "__main__":
    launch_gui()

