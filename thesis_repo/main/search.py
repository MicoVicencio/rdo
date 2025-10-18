import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sqlite3
import os
import subprocess

DB_FILE = "thesis_repository.db"
SEAL_PATH = "image.png"
THESIS_FILES_DIR = "thesis_files"

class ThesisSearchApp(tk.Frame):
    """
    Main application class for the Thesis Repository Search.
    Inherits from tk.Frame to create the main GUI window.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pack(fill="both", expand=True)

        # Window Setup
        self.parent.title("📚 Thesis Repository Search")
        self.parent.state("zoomed")  # start maximized
        self.parent.configure(bg="#f4f6f9")

        # --- Title Banner (Seal + App Name) ---
        banner_frame = tk.Frame(self.parent, bg="#4a90e2", height=90)
        banner_frame.pack(fill=tk.X, side=tk.TOP)

        try:
            img = Image.open(SEAL_PATH)
            img = img.resize((80, 70), Image.LANCZOS)
            self.seal_img = ImageTk.PhotoImage(img)
            tk.Label(banner_frame, image=self.seal_img, bg="#4a90e2").pack(side=tk.LEFT, padx=20)
        except Exception:
            pass

        tk.Label(banner_frame,
                 text="Research & Thesis Repository",
                 font=("Segoe UI", 32, "bold"),
                 fg="white", bg="#4a90e2").pack(side=tk.LEFT, pady=20)

        # --- Search + Filters ---
        top_frame = tk.Frame(self.parent, bg="#f4f6f9", pady=20)
        top_frame.pack(fill=tk.X)

        self.search_var = tk.StringVar()
                # --- Search Bar + Button + Filters ---
        # 🔍 Search Entry
        self.search_entry = tk.Entry(
            top_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 13),
            width=55,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightcolor="#4a90e2",
            highlightbackground="#cccccc"
        )
        self.search_entry.pack(side=tk.LEFT, padx=(25, 5), ipady=7)
        self.search_entry.bind("<Return>", self.perform_search)

        # 🔍 Search Button
        self.search_btn = tk.Button(
            top_frame, text="Search",
            font=("Segoe UI", 12, "bold"),
            command=self.perform_search,
            bg="#4a90e2", fg="white",
            activebackground="#357ab8",
            activeforeground="white",
            relief="flat",
            padx=18, pady=7,
            cursor="hand2"
        )
        self.search_btn.pack(side=tk.LEFT, padx=(0, 15))

        # --- Filters ---
        # Course Filter
        tk.Label(
            top_frame, text="Course:",
            font=("Segoe UI", 12), bg="#f4f6f9"
        ).pack(side=tk.LEFT, padx=(5, 5))
        
        self.course_var = tk.StringVar()
        self.course_filter = ttk.Combobox(
            top_frame,
            textvariable=self.course_var,
            width=20,
            state="readonly",
            font=("Segoe UI", 11)
        )
        self.course_filter.pack(side=tk.LEFT, padx=(0, 15))
        self.course_filter["values"] = self.get_filter_values("course")
        self.course_filter.set("All")

        # Year Filter
        tk.Label(
            top_frame, text="Year:",
            font=("Segoe UI", 12), bg="#f4f6f9"
        ).pack(side=tk.LEFT, padx=(5, 5))

        self.year_var = tk.StringVar()
        self.year_filter = ttk.Combobox(
            top_frame,
            textvariable=self.year_var,
            width=12,
            state="readonly",
            font=("Segoe UI", 11)
        )
        self.year_filter.pack(side=tk.LEFT, padx=(0, 15))
        self.year_filter["values"] = self.get_filter_values("year")
        self.year_filter.set("All")


        # --- Treeview (Results Table) ---
        table_frame = tk.Frame(self.parent, bg="#f4f6f9")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=(5, 25))

        columns = ("Title", "Course", "Year")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill="y")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        font=("Segoe UI", 12),
                        rowheight=35,
                        background="white",
                        fieldbackground="white")
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 13, "bold"),
                        background="#4a90e2",
                        foreground="white")
        style.map("Treeview", background=[("selected", "#cce7ff")])

        # Set up headings
        self.tree.heading("Title", text="Title")
        self.tree.heading("Course", text="Course")
        self.tree.heading("Year", text="Year")

        self.tree.column("Title", width=600, anchor="w")
        self.tree.column("Course", width=200, anchor="center")
        self.tree.column("Year", width=120, anchor="center")

        self.tree.tag_configure("oddrow", background="#f9f9f9")
        self.tree.tag_configure("evenrow", background="#eef7fb")

        self.tree.bind("<Double-1>", self.open_pdf)

        # Initial search
        self.perform_search()

    def connect_db(self):
        return sqlite3.connect(DB_FILE)

    def get_filter_values(self, column):
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
                    if os.name == "nt":
                        os.startfile(abs_path)
                    elif os.name == "posix":
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
 