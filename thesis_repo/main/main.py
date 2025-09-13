import tkinter as tk
from tkinter import ttk, messagebox
# Import the function from the separate file to open the thesis entry form.
from upload_thesis import open_thesis_entry_form
import sqlite3
# Assuming `search.py` contains the `ThesisSearchApp` class.
from search import ThesisSearchApp

class Repo:
    def __init__(self):
        """Initializes the main application window and GUI components."""
        self.root = tk.Tk()
        self.root.title("Research Development Office")
        # Start the window in a maximized state.
        self.root.state('zoomed')

        screen_width = self.root.winfo_screenwidth()
        half_width = screen_width // 2

        label_font = ("Arial", 25)
        tree_font = ("Arial", 14)
        button_font = ("Arial", 16, "bold")

        self.main_frame = tk.Frame(self.root, bg="white")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.title_label = tk.Label(
            self.main_frame, text="Thesis Repository",
            font=("Helvetica", 70, "bold"), bg="white"
        )
        self.title_label.pack(pady=20)

        self.split_frame = tk.Frame(self.main_frame, bg="white")
        self.split_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel for information display
        self.left_panel = tk.Frame(self.split_frame, bg="#d0e6f7", width=half_width)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)

        # Right panel for navigation buttons
        self.right_panel = tk.Frame(self.split_frame, bg="#fce4b8", width=half_width)
        self.right_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.right_panel.pack_propagate(False)

        top_left_frame = tk.Frame(self.left_panel, bg="#a9d0f5", height=250)
        top_left_frame.pack(fill=tk.X)
        top_left_frame.pack_propagate(False)

        college_frame = tk.Frame(top_left_frame, bg="#a9d0f5")
        college_frame.pack(anchor="w", padx=20, pady=(20, 5))
        college_count = self.get_thesis_count()

        tk.Label(college_frame, text="Total Thesis of College:",
                 font=label_font, bg="#a9d0f5").pack(side=tk.LEFT)

        tk.Label(college_frame, text=str(college_count),
                 font=label_font, bg="#a9d0f5", fg="blue").pack(side=tk.LEFT, padx=10)

        bottom_left_frame = tk.Frame(self.left_panel, bg="#d0e6f7")
        bottom_left_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        bottom_left_frame.pack_propagate(False)

        tk.Label(bottom_left_frame, text="Recently Added:",
                 font=("Arial", 16, "bold"), bg="#d0e6f7", fg="gray20").pack(anchor="w", padx=10)

        tree_container = tk.Frame(bottom_left_frame, bg="#d0e6f7")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))
        tree_container.pack_propagate(False)

        tree_scroll = tk.Scrollbar(tree_container)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("Treeview", font=tree_font, rowheight=100)
        style.configure("Treeview.Heading", font=("Arial", 16, "bold"))

        self.tree = ttk.Treeview(
            tree_container,
            yscrollcommand=tree_scroll.set,
            columns=("title", "course", "date_uploaded"),
            show="headings",
            height=20
        )
        self.tree.heading("title", text="Title")
        self.tree.heading("course", text="Course")
        self.tree.heading("date_uploaded", text="Date Uploaded")

        self.tree.column("title", width=400)
        self.tree.column("course", width=200)
        self.tree.column("date_uploaded", width=180)

        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)

        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 14), rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 16, "bold"))

        self.tree.tag_configure("oddrow", background="#f9f9f9")
        self.tree.tag_configure("evenrow", background="#e0f7fa")

        # Load data from the database on startup.
        self.load_data_from_database()

        button_frame = tk.Frame(self.right_panel, bg="#fce4b8")        #Edit color of buttons
        button_frame.place(relx=0.5, rely=0.5, anchor="center")

        btn1 = tk.Button(button_frame, text="Create a Record", font=button_font, width=30, height=2, bg="#ffcc80",
                         command=lambda: self.security(1))
        btn2 = tk.Button(button_frame, text="Search Research/Thesis", font=button_font, width=30, height=2, bg="#ffd180",
                         command=self.search_thesis)
        btn3 = tk.Button(button_frame, text="Update Research/Thesis", font=button_font, width=30, height=2, bg="#ffab91",
                         command=lambda: self.security(3))
        btn4 = tk.Button(button_frame, text="Delete Research/Thesis", font=button_font, width=30, height=2, bg="#ef9a9a",
                         command=lambda: self.security(4))

        btn1.pack(pady=10)
        btn2.pack(pady=10)
        btn3.pack(pady=10)
        btn4.pack(pady=10)

        self.root.mainloop()

    def security(self, step):
        """
        Creates a modal login window to secure administrative actions.
        """
        login_window = tk.Toplevel(self.root)
        login_window.title("User Login")
        login_window.geometry("300x300")
        login_window.resizable(False, False)
        # Prevents interaction with the main window until login is complete.
        login_window.transient(self.root)
        login_window.grab_set()

        login_frame = tk.Frame(login_window, padx=20, pady=20)
        login_frame.pack(expand=True, fill="both")

        tk.Label(login_frame, text="User Login", font=("Arial", 16, "bold")).pack(pady=(0, 20))

        tk.Label(login_frame, text="Username:", font=("Arial", 12)).pack(anchor='w')
        self.username_entry = tk.Entry(login_frame, font=("Arial", 12))
        self.username_entry.pack(fill='x', pady=5)

        tk.Label(login_frame, text="Password:", font=("Arial", 12)).pack(anchor='w')
        self.password_entry = tk.Entry(login_frame, show="*", font=("Arial", 12))
        self.password_entry.pack(fill='x', pady=5)

        tk.Button(login_frame, text="Login", font=("Arial", 12, "bold"),
                  command=lambda: self.check_credentials(login_window, step)).pack(fill='x', pady=10)

    def check_credentials(self, login_window, step):
        """
        Checks for valid credentials and proceeds with the correct action.
        """
        username = self.username_entry.get()
        password = self.password_entry.get()

        if username == "admin" and password == "123": #edit credentials
            login_window.destroy()
            if step == 1:
                self.upload_thesis()
            elif step == 3:
                self.update_thesis()
            elif step == 4:
                self.delete_thesis()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def get_thesis_count(self):
        """Fetches the total number of thesis records from the database."""
        try:
            conn = sqlite3.connect("thesis_repo/main/thesis_repository.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM theses")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print("Error counting theses:", e)
            return 0

    def load_data_from_database(self):
        """Loads and displays the most recently added theses in the Treeview widget."""
        try:
            from datetime import datetime
            conn = sqlite3.connect("thesis_repo/main/thesis_repository.db")
            cursor = conn.cursor()
            cursor.execute("SELECT title, course, date_uploaded FROM theses ORDER BY date_uploaded DESC")
            rows = cursor.fetchall()

            for index, row in enumerate(rows):
                tag = "evenrow" if index % 2 == 0 else "oddrow"
                # Truncate long titles for better display
                title = (row[0][:35] + "...") if len(row[0]) > 38 else row[0]
                course = row[1]

                try:
                    dt_obj = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                    date_uploaded = dt_obj.strftime("%B %d, %Y - %I:%M %p")
                except:
                    date_uploaded = row[2]

                self.tree.insert("", "end", values=(title, course, date_uploaded), tags=(tag,))
            conn.close()
        except Exception as e:
            print("Error loading data from database:", e)

    def upload_thesis(self):
        """
        Opens the thesis entry form and refreshes the main window's data
        after the form is closed.
        """
        open_thesis_entry_form()
        # This function call refreshes the view to show the new entry.
        self.refresh_recent_entries()
        messagebox.showinfo("Success", "Thesis entry form opened.")

    def search_thesis(self):
        """Opens the search application window."""
        top = tk.Toplevel(self.root)
        ThesisSearchApp(top)

    def update_thesis(self):
        """Placeholder for the update functionality."""
        messagebox.showinfo("Action Required", "Update functionality is not yet implemented.")

    def delete_thesis(self):
        """Placeholder for the delete functionality."""
        messagebox.showinfo("Action Required", "Delete functionality is not yet implemented.")

    def refresh_recent_entries(self):
        """Clears the Treeview and reloads data from the database."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.load_data_from_database()

if __name__ == "__main__":
    Repo()
