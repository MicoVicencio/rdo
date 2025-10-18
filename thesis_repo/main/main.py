import tkinter as tk
from tkinter import ttk, messagebox
from upload_thesis import open_thesis_entry_form
from search import ThesisSearchApp
import sqlite3
from update_thesis import UpdateThesisApp
from delete import open_delete_management_ui


class Repo:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Research Development Office")
        self.root.state("zoomed")
        self.root.configure(bg="#f4f6f9")  # Softer background

        screen_width = self.root.winfo_screenwidth()
        half_width = screen_width // 2

        # 🎨 Fonts
        self.label_font = ("Segoe UI", 18, "bold")
        self.tree_font = ("Segoe UI", 12)
        self.button_font = ("Segoe UI", 14, "bold")

        # 🔹 Title Banner
        self.title_label = tk.Label(
            self.root,
            text="📚 Thesis Repository",
            font=("Segoe UI", 45, "bold"),
            bg="#4a90e2",
            fg="white",
            pady=25
        )
        self.title_label.pack(fill="x")

        # 🔹 Split Frame
        self.split_frame = tk.Frame(self.root, bg="#f4f6f9")
        self.split_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)  # more breathing space

        # Left Panel
        self.left_panel = tk.Frame(self.split_frame, bg="white", bd=2, relief="groove")
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20), pady=10)

        # Right Panel
        self.right_panel = tk.Frame(self.split_frame, bg="white", bd=2, relief="groove", width=300)
        self.right_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=10)

                # 🔹 Thesis Count (in its own box)
        count_frame = tk.Frame(self.left_panel, bg="#fdfdfd", bd=1, relief="solid")
        count_frame.pack(fill=tk.X, padx=20, pady=(20, 15))

        self.college_count = self.get_thesis_count()
        tk.Label(count_frame, text="Total Thesis of College:",
                 font=self.label_font, bg="#fdfdfd").pack(anchor="w", padx=20, pady=(10, 5))

        # 👉 keep a reference to this label so we can update later
        self.college_count_label = tk.Label(
            count_frame,
            text=str(self.college_count),
            font=("Segoe UI", 34, "bold"),
            fg="#4a90e2",
            bg="#fdfdfd"
        )
        self.college_count_label.pack(anchor="w", padx=20, pady=(0, 10))


        # 🔹 Recently Added Label
        tk.Label(self.left_panel, text="Recently Added",
                 font=("Segoe UI", 18, "bold"), bg="white", fg="#444").pack(anchor="w", padx=20, pady=(10, 5))

        # Treeview Container
        tree_container = tk.Frame(self.left_panel, bg="white")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        tree_scroll = tk.Scrollbar(tree_container)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        font=self.tree_font,
                        rowheight=35,
                        background="white",
                        fieldbackground="white")
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 13, "bold"),
                        background="#4a90e2",
                        foreground="white")
        style.map("Treeview", background=[("selected", "#aed6f1")])

        self.tree = ttk.Treeview(
            tree_container,
            yscrollcommand=tree_scroll.set,
            columns=("title", "course", "date_uploaded"),
            show="headings",
            height=15
        )
        self.tree.heading("title", text="Title")
        self.tree.heading("course", text="Course")
        self.tree.heading("date_uploaded", text="Date Uploaded")

        # Wider columns for balance
        self.tree.column("title", width=450, anchor="w")
        self.tree.column("course", width=220, anchor="center")
        self.tree.column("date_uploaded", width=220, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)

        self.tree.tag_configure("oddrow", background="#f9f9f9")
        self.tree.tag_configure("evenrow", background="#eef7fb")

        # Load DB data
        self.load_data_from_database()

                # 🔹 Right Panel Buttons
        button_frame = tk.Frame(self.right_panel, bg="white")
        button_frame.pack(expand=True, pady=40, padx=30)

        def styled_btn(parent, text, color, cmd):
            return tk.Button(
                parent,
                text=text,
                font=self.button_font,
                width=26, height=2,       # ✅ wide enough for long text
                bg=color,
                fg="black",
                bd=0,
                relief="flat",
                activebackground="#e1e1e1",
                highlightthickness=0,
                command=cmd
            )

        # Buttons with more vertical space
        styled_btn(button_frame, "➕ Create a Record", "#ffcc80", lambda: self.security(1)).pack(pady=15, ipadx=5, ipady=5)
        styled_btn(button_frame, "🔍 Search Thesis", "#ffd180", self.search_thesis).pack(pady=15, ipadx=5, ipady=5)
        styled_btn(button_frame, "✏️ Update Thesis", "#ffab91", lambda: self.security(3)).pack(pady=15, ipadx=5, ipady=5)
        styled_btn(button_frame, "🗑️ Delete & Export Thesis", "#ef9a9a", lambda: self.security(4)).pack(pady=15, ipady=5)


        self.root.mainloop()

    # ---------------- Other methods (no design changes needed) ---------------- #

    def security(self, step):
        login_window = tk.Toplevel(self.root)
        login_window.title("User Login")
        login_window.geometry("300x300")
        login_window.resizable(False, False)
        login_window.transient(self.root)
        login_window.grab_set()

        frame = tk.Frame(login_window, padx=20, pady=20)
        frame.pack(expand=True, fill="both")

        tk.Label(frame, text="🔒 User Login", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))
        tk.Label(frame, text="Username:", font=("Segoe UI", 12)).pack(anchor="w")
        self.username_entry = tk.Entry(frame, font=("Segoe UI", 12))
        self.username_entry.pack(fill="x", pady=5)

        tk.Label(frame, text="Password:", font=("Segoe UI", 12)).pack(anchor="w")
        self.password_entry = tk.Entry(frame, show="*", font=("Segoe UI", 12))
        self.password_entry.pack(fill="x", pady=5)

        tk.Button(frame, text="Login", font=("Segoe UI", 12, "bold"),
                  bg="#4a90e2", fg="white", command=lambda: self.check_credentials(login_window, step)).pack(fill="x", pady=15)

    def check_credentials(self, login_window, step):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username == "admin" and password == "123":
            login_window.destroy()
            if step == 1:
                self.upload_thesis()
            elif step == 3:
                UpdateThesisApp(self.root)
            elif step == 4:
                self.delete_thesis()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    def get_thesis_count(self):
        try:
            conn = sqlite3.connect("thesis_repository.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM theses")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def load_data_from_database(self):
        try:
            from datetime import datetime
            conn = sqlite3.connect("thesis_repository.db")
            cursor = conn.cursor()
            cursor.execute("SELECT title, course, date_uploaded FROM theses ORDER BY date_uploaded DESC")
            rows = cursor.fetchall()
            for index, row in enumerate(rows):
                tag = "evenrow" if index % 2 == 0 else "oddrow"
                title = (row[0][:40] + "...") if len(row[0]) > 43 else row[0]
                course = row[1]
                try:
                    dt_obj = datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
                    date_uploaded = dt_obj.strftime("%b %d, %Y - %I:%M %p")
                except:
                    date_uploaded = row[2]
                self.tree.insert("", "end", values=(title, course, date_uploaded), tags=(tag,))
            conn.close()
        except Exception as e:
            print("DB Load Error:", e)

    def upload_thesis(self):
        from upload_thesis import open_thesis_entry_form
        open_thesis_entry_form(on_success=self.refresh_recent_entries)

    def search_thesis(self):
        top = tk.Toplevel(self.root)
        ThesisSearchApp(top)


    def delete_thesis(self):
        open_delete_management_ui(on_refresh = self.refresh_recent_entries)

    def refresh_recent_entries(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.load_data_from_database()

        # Update thesis count and label
        self.college_count = self.get_thesis_count()
        self.college_count_label.config(text=str(self.college_count))



if __name__ == "__main__":
    Repo()
