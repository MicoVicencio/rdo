import tkinter as tk
from tkinter import ttk
import sqlite3

def fetch_theses():
    conn = sqlite3.connect("thesis_repository.db")
    c = conn.cursor()
    c.execute('''
        SELECT thesis_id, title, authors, course, year, keywords, file_path, date_uploaded 
        FROM theses
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def populate_table():
    for row in fetch_theses():
        tree.insert("", "end", values=row)

# GUI Setup
root = tk.Tk()
root.title("Thesis Repository Viewer")
root.geometry("1400x500")

columns = ("ID", "Title", "Authors", "Course", "Year", "Keywords", "File Path", "Date Uploaded")

tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    if col == "File Path":
        tree.column(col, width=300)
    elif col == "Title" or col == "Keywords":
        tree.column(col, width=250)
    else:
        tree.column(col, width=120)

# Scrollbars
vsb = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
hsb = ttk.Scrollbar(root, orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
vsb.pack(side=tk.RIGHT, fill=tk.Y)
hsb.pack(side=tk.BOTTOM, fill=tk.X)

populate_table()

root.mainloop()
