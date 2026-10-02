import tkinter as tk
from tkinter import ttk


def create_scrollable_frame(parent: tk.Misc, padding: str = "20") -> ttk.Frame:
    """
    Fill `parent` with a vertically scrolling area, and return the frame to put content in.

    The content frame stretches to the area's width, so its columns can expand.
    """
    canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0)
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    content = ttk.Frame(canvas, padding=padding)
    content_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)
    content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(content_id, width=e.width))
    return content
