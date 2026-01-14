from tkinter import messagebox
import traceback

def throw(e, summary):
    traceback.print_exc()
    messagebox.showerror("Error", f"{summary}: {str(e)}")