import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sqlite3
import os
import subprocess

DB_FILE = "thesis_repo/main/thesis_repository.db"
SEAL_PATH = r"C:/Users/Mico/Desktop/rdo/thesis_repo/main/image.png"
THESIS_FILES_DIR = "thesis_files"

class ThesisSearchApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pack(fill="both", expand=True)

        self.parent.title("Thesis Repository Search")
        self.parent.geometry("1200x800")

        # --- Top Frame (Seal + Search bar + Filters) ---
        top_frame = tk.Frame(self.parent, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Seal Image
        try:
            img = Image.open(SEAL_PATH)
            img = img.resize((70, 70), Image.LANCZOS)
            self.seal_img = ImageTk.PhotoImage(img)
            tk.Label(top_frame, image=self.seal_img).pack(side=tk.LEFT, padx=10)
        except Exception as e:
            messagebox.showerror("Error", f"Seal image not found:\n{e}")

        # Search Entry
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, font=("Arial", 12), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        self.search_entry.bind("<Return>", self.perform_search)

        # Search Button
        self.search_btn = tk.Button(top_frame, text="Search", font=("Arial", 11, "bold"),
                                     command=self.perform_search, bg="#007acc", fg="white")
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # Course Filter
        tk.Label(top_frame, text="Course:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(20,5))
        self.course_var = tk.StringVar()
        self.course_filter = ttk.Combobox(top_frame, textvariable=self.course_var, width=15, state="readonly")
        self.course_filter.pack(side=tk.LEFT)
        self.course_filter["values"] = self.get_filter_values("course")
        self.course_filter.set("All")

        # Year Filter
        tk.Label(top_frame, text="Year:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(20,5))
        self.year_var = tk.StringVar()
        self.year_filter = ttk.Combobox(top_frame, textvariable=self.year_var, width=10, state="readonly")
        self.year_filter.pack(side=tk.LEFT)
        self.year_filter["values"] = self.get_filter_values("year")
        self.year_filter.set("All")

        # --- Treeview for Results ---
        columns = ("Title", "Course", "Year")
        self.tree = ttk.Treeview(self.parent, columns=columns, show="headings", height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.configure("Treeview",
                        rowheight=35,
                        font=("Arial", 13))
        style.configure("Treeview.Heading",
                        font=("Arial", 14, "bold"))

        self.tree.tag_configure("oddrow", background="#f2f2f2")
        self.tree.tag_configure("evenrow", background="white")

        self.tree.heading("Title", text="Title")
        self.tree.heading("Course", text="Course")
        self.tree.heading("Year", text="Year")

        self.tree.column("Title", width=500)
        self.tree.column("Course", width=200)
        self.tree.column("Year", width=150)

        self.tree.bind("<Double-1>", self.open_pdf)

        self.perform_search()

    def connect_db(self):
        return sqlite3.connect(DB_FILE)

    def get_filter_values(self, column):
        """Fetch distinct values from DB for filters."""
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT {column} FROM theses")
            values = [row[0] for row in cur.fetchall()]
            conn.close()
            return ["All"] + values
        except Exception:
            return ["All"]

    def perform_search(self, event=None):
        """Search theses based on input and filters."""
        search_text = self.search_var.get().strip()
        course = self.course_var.get()
        year = self.year_var.get()

        query = "SELECT thesis_id, title, course, year, keywords, file_path, date_uploaded FROM theses WHERE 1=1"
        params = []

        if search_text:
            query += " AND (title LIKE ? OR keywords LIKE ?)"
            params.extend([f"%{search_text}%", f"%{search_text}%"])

        if course != "All":
            query += " AND course=?"
            params.append(course)

        if year != "All":
            query += " AND year=?"
            params.append(year)

        conn = self.connect_db()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        conn.close()

        for row in self.tree.get_children():
            self.tree.delete(row)

        for index, row in enumerate(results):
            thesis_id, title, course, year, keywords, file_path, date_uploaded = row
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.tree.insert("", tk.END, iid=thesis_id,
                             values=(title, course, year),
                             tags=(tag,))

    def open_pdf(self, event):
        """Open the selected PDF file"""
        selected_item_id = self.tree.focus()
        if not selected_item_id:
            return

        conn = self.connect_db()
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM theses WHERE thesis_id=?", (selected_item_id,))
        result = cur.fetchone()
        conn.close()

        if result:
            file_path_from_db = result[0]

            # Determine the base directory of the 'thesis_repo'
            repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(DB_FILE)))
            main_dir_path = os.path.join(repo_root_dir, 'main')
            absolute_thesis_base_dir = os.path.join(main_dir_path, THESIS_FILES_DIR)

            relative_path = file_path_from_db
            if file_path_from_db.startswith(THESIS_FILES_DIR + os.sep):
                relative_path = file_path_from_db[len(THESIS_FILES_DIR + os.sep):]
            elif file_path_from_db.startswith(THESIS_FILES_DIR + "/"):
                relative_path = file_path_from_db[len(THESIS_FILES_DIR + "/"):]

            abs_path = os.path.join(absolute_thesis_base_dir, relative_path)

            if os.path.exists(abs_path):
                try:
                    if os.name == "nt":  # Windows
                        os.startfile(abs_path)
                    elif os.name == "posix":  # Linux / Mac
                        subprocess.Popen(["xdg-open", abs_path])
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file:\n{e}")
            else:
                messagebox.showerror("File Not Found", f"The file does not exist:\n{abs_path}")
        else:
            messagebox.showerror("Error", "Could not retrieve file path from database.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ThesisSearchApp(root)
    root.mainloop()
