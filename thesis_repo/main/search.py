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
    """
    Main application class for the Thesis Repository Search.
    Inherits from tk.Frame to create the main GUI window.
    """
    def __init__(self, parent):
        """
        Initializes the main application window and its components.

        Args:
            parent (tk.Tk): The root Tkinter window.
        """
        super().__init__(parent)
        self.parent = parent
        self.pack(fill="both", expand=True)

        self.parent.title("Thesis Repository Search")
        self.parent.geometry("1200x800")

        # --- Top Frame (Seal + Search bar + Filters) ---
        # This frame holds the seal image, search bar, and filter dropdowns.
        top_frame = tk.Frame(self.parent, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # Seal Image
        # Tries to load and display the university seal image.
        try:
            img = Image.open(SEAL_PATH)
            img = img.resize((70, 70), Image.LANCZOS)
            self.seal_img = ImageTk.PhotoImage(img)
            tk.Label(top_frame, image=self.seal_img).pack(side=tk.LEFT, padx=10)
        except Exception as e:
            messagebox.showerror("Error", f"Seal image not found:\n{e}")

        # Search Entry
        # The text input field for the search query.
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var, font=("Arial", 12), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        self.search_entry.bind("<Return>", self.perform_search)

        # Search Button
        # The button that triggers the search operation.
        self.search_btn = tk.Button(top_frame, text="Search", font=("Arial", 11, "bold"),
                                     command=self.perform_search, bg="#007acc", fg="white")
        self.search_btn.pack(side=tk.LEFT, padx=5)

        # Course Filter
        # Combobox for filtering results by course.
        tk.Label(top_frame, text="Course:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(20,5))
        self.course_var = tk.StringVar()
        self.course_filter = ttk.Combobox(top_frame, textvariable=self.course_var, width=15, state="readonly")
        self.course_filter.pack(side=tk.LEFT)
        self.course_filter["values"] = self.get_filter_values("course")
        self.course_filter.set("All")

        # Year Filter
        # Combobox for filtering results by year.
        tk.Label(top_frame, text="Year:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(20,5))
        self.year_var = tk.StringVar()
        self.year_filter = ttk.Combobox(top_frame, textvariable=self.year_var, width=10, state="readonly")
        self.year_filter.pack(side=tk.LEFT)
        self.year_filter["values"] = self.get_filter_values("year")
        self.year_filter.set("All")

        # --- Treeview for Results ---
        # A Treeview widget to display the search results in a table format.
        columns = ("Title", "Course", "Year")
        self.tree = ttk.Treeview(self.parent, columns=columns, show="headings", height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Styling for the Treeview widget.
        style = ttk.Style()
        style.configure("Treeview",
                        rowheight=35,
                        font=("Arial", 13))
        style.configure("Treeview.Heading",
                        font=("Arial", 14, "bold"))

        # Configure alternating row colors for better readability.
        self.tree.tag_configure("oddrow", background="#f2f2f2")
        self.tree.tag_configure("evenrow", background="white")

        # Set the headings and column widths for the Treeview.
        self.tree.heading("Title", text="Title")
        self.tree.heading("Course", text="Course")
        self.tree.heading("Year", text="Year")

        self.tree.column("Title", width=500)
        self.tree.column("Course", width=200)
        self.tree.column("Year", width=150)

        # Binds the double-click event to the open_pdf function.
        self.tree.bind("<Double-1>", self.open_pdf)

        # Performs an initial search to populate the table on startup.
        self.perform_search()

    def connect_db(self):
        """
        Establishes a connection to the SQLite database file.

        Returns:
            sqlite3.Connection: The database connection object.
        """
        return sqlite3.connect(DB_FILE)

    def get_filter_values(self, column):
        """
        Fetches distinct values for a given column from the database,
        used to populate the filter dropdowns.

        Args:
            column (str): The name of the database column (e.g., 'course', 'year').

        Returns:
            list: A list of unique values, including "All" as the first item.
        """
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT {column} FROM theses")
            values = [row[0] for row in cur.fetchall()]
            conn.close()
            return ["All"] + values
        except Exception:
            # Returns a default list if the database connection or query fails.
            return ["All"]

    def perform_search(self, event=None):
        """
        Executes a search query against the database based on the search bar
        text and the selected filters. Updates the Treeview with the results.

        Args:
            event (tk.Event, optional): The event that triggered the function.
                                         Defaults to None.
        """
        search_text = self.search_var.get().strip()
        course = self.course_var.get()
        year = self.year_var.get()

        # Construct the base SQL query and parameter list.
        query = "SELECT thesis_id, title, course, year, keywords, file_path, date_uploaded FROM theses WHERE 1=1"
        params = []

        # Add search conditions for title and keywords if a search text is provided.
        if search_text:
            query += " AND (title LIKE ? OR keywords LIKE ?)"
            params.extend([f"%{search_text}%", f"%{search_text}%"])

        # Add filter conditions for course and year if a specific value is selected.
        if course != "All":
            query += " AND course=?"
            params.append(course)

        if year != "All":
            query += " AND year=?"
            params.append(year)

        # Connect to the database and execute the query.
        conn = self.connect_db()
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        conn.close()

        # Clear existing items in the Treeview.
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Insert new results into the Treeview with alternating row colors.
        for index, row in enumerate(results):
            thesis_id, title, course, year, keywords, file_path, date_uploaded = row
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.tree.insert("", tk.END, iid=thesis_id,
                             values=(title, course, year),
                             tags=(tag,))

    def open_pdf(self, event):
        """
        Handles the double-click event on a Treeview item.
        It retrieves the associated file path from the database and
        attempts to open the PDF file using the system's default viewer.

        Args:
            event (tk.Event): The event that triggered the function.
        """
        selected_item_id = self.tree.focus()
        if not selected_item_id:
            return

        # Fetch the file path from the database using the selected item's ID.
        conn = self.connect_db()
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM theses WHERE thesis_id=?", (selected_item_id,))
        result = cur.fetchone()
        conn.close()

        if result:
            file_path_from_db = result[0]

            # Construct the absolute path to the PDF file.
            # This logic handles both relative and absolute paths stored in the DB.
            repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(DB_FILE)))
            main_dir_path = os.path.join(repo_root_dir, 'main')
            absolute_thesis_base_dir = os.path.join(main_dir_path, THESIS_FILES_DIR)

            relative_path = file_path_from_db
            if file_path_from_db.startswith(THESIS_FILES_DIR + os.sep):
                relative_path = file_path_from_db[len(THESIS_FILES_DIR + os.sep):]
            elif file_path_from_db.startswith(THESIS_FILES_DIR + "/"):
                relative_path = file_path_from_db[len(THESIS_FILES_DIR + "/"):]

            abs_path = os.path.join(absolute_thesis_base_dir, relative_path)

            # Check if the file exists and then try to open it.
            if os.path.exists(abs_path):
                try:
                    if os.name == "nt":  # For Windows
                        os.startfile(abs_path)
                    elif os.name == "posix":  # For Linux and Mac
                        subprocess.Popen(["xdg-open", abs_path])
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file:\n{e}")
            else:
                messagebox.showerror("File Not Found", f"The file does not exist:\n{abs_path}")
        else:
            messagebox.showerror("Error", "Could not retrieve file path from database.")


if __name__ == "__main__":
    # Creates the main Tkinter window and runs the application loop.
    root = tk.Tk()
    app = ThesisSearchApp(root)
    root.mainloop()
