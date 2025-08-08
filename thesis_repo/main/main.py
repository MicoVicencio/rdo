import tkinter as tk
from tkinter import ttk
from upload_thesis import open_thesis_entry_form  
import sqlite3



class Repo:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Research Development Office")
        self.root.state('zoomed')  # Maximize window
    
    


        # Get screen width and divide into half
        screen_width = self.root.winfo_screenwidth()
        half_width = screen_width // 2

        # Font styles
        label_font = ("Arial", 25)
        tree_font = ("Arial", 14)
        button_font = ("Arial", 16, "bold")

        # Main container
        self.main_frame = tk.Frame(self.root, bg="white")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header title
        self.title_label = tk.Label(
            self.main_frame, text="Thesis Repository",
            font=("Helvetica", 70, "bold"), bg="white"
        )
        self.title_label.pack(pady=20)

        # Split main area
        self.split_frame = tk.Frame(self.main_frame, bg="white")
        self.split_frame.pack(fill=tk.BOTH, expand=True)

        # LEFT PANEL
        self.left_panel = tk.Frame(self.split_frame, bg="#d0e6f7", width=half_width)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)

        # RIGHT PANEL
        self.right_panel = tk.Frame(self.split_frame, bg="#fce4b8", width=half_width)
        self.right_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.right_panel.pack_propagate(False)

        # --- TOP LEFT (info labels) ---
        top_left_frame = tk.Frame(self.left_panel, bg="#a9d0f5", height=250)
        top_left_frame.pack(fill=tk.X)
        top_left_frame.pack_propagate(False)

        college_frame = tk.Frame(top_left_frame, bg="#a9d0f5")
        college_frame.pack(anchor="w", padx=20, pady=(20, 5))
        college_count = self.get_thesis_count()  # 👈 Get actual count

        tk.Label(college_frame, text="Total Thesis of College:",
                 font=label_font, bg="#a9d0f5").pack(side=tk.LEFT)

        tk.Label(college_frame, text=str(college_count),
                 font=label_font, bg="#a9d0f5", fg="blue").pack(side=tk.LEFT, padx=10)


        senior_frame = tk.Frame(top_left_frame, bg="#a9d0f5")
        senior_frame.pack(anchor="w", padx=20, pady=(5, 10))
        


        # --- BOTTOM LEFT (Recently Added + Treeview) ---
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

        # Create Treeview
        self.tree = ttk.Treeview(
            tree_container,
            yscrollcommand=tree_scroll.set,
            columns=("title", "course", "date_uploaded"),
            show="headings",
            height=20  # ✅ Increase visible rows
        )
        self.tree.heading("title", text="Title")
        self.tree.heading("course", text="Course")
        self.tree.heading("date_uploaded", text="Date Uploaded")

        self.tree.column("title", width=400)
        self.tree.column("course", width=200)
        self.tree.column("date_uploaded", width=180)

        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)

        # ✅ Zebra Style
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 14), rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 16, "bold"))

        # Define tag colors (no borderwidth/relief)
        self.tree.tag_configure("oddrow", background="#f9f9f9")
        self.tree.tag_configure("evenrow", background="#e0f7fa")


        self.load_data_from_database()


        # --- RIGHT PANEL BUTTONS (centered) ---
        button_frame = tk.Frame(self.right_panel, bg="#fce4b8")
        button_frame.place(relx=0.5, rely=0.5, anchor="center")  # Centered

        btn1 = tk.Button(button_frame, text="Create a Record", font=button_font, width=30, height=2, bg="#ffcc80",command=self.upload_thesis)
        btn2 = tk.Button(button_frame, text="Search Research/Thesis", font=button_font, width=30, height=2, bg="#ffd180")
        btn3 = tk.Button(button_frame, text="Update Research/Thesis", font=button_font, width=30, height=2, bg="#ffab91")
        btn4 = tk.Button(button_frame, text="Delete Research/Thesis", font=button_font, width=30, height=2, bg="#ef9a9a")

        btn1.pack(pady=10)
        btn2.pack(pady=10)
        btn3.pack(pady=10)
        btn4.pack(pady=10)

        self.root.mainloop()
    def get_thesis_count(self):
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
        try:
            from datetime import datetime

            conn = sqlite3.connect("thesis_repo/main/thesis_repository.db")
            cursor = conn.cursor()
            cursor.execute("SELECT title, course, date_uploaded FROM theses ORDER BY date_uploaded DESC")
            rows = cursor.fetchall()

            for index, row in enumerate(rows):
                tag = "evenrow" if index % 2 == 0 else "oddrow"

                # Format title
                title = (row[0][:35] + "...") if len(row[0]) > 38 else row[0]
                course = row[1]

                # Format date_uploaded
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
        open_thesis_entry_form()  # open upload form
        self.refresh_recent_entries()  # reload treeview after form closes
        
    def refresh_recent_entries(self):
          # Clear old data
        for item in self.tree.get_children():
           self.tree.delete(item)
        # Reload from database
        self.load_data_from_database()



if __name__ == "__main__":
    Repo()
