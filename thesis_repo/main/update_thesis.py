import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import shutil
import re
from PIL import Image, ImageTk
import fitz # PyMuPDF
from keybert import KeyBERT
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import tempfile

# Global setup
# Define DB_PATH relative to the script's directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thesis_repository.db")

# Initialize KeyBERT, handling potential errors if dependencies are missing
try:
    kw_model = KeyBERT()
except Exception as e:
    # KeyBERT requires certain NLP models/libraries, this handles failure gracefully
    print(f"KeyBERT failed to initialize: {e}. Keyword extraction will be disabled.")
    kw_model = None

# ---------------- Database Init ---------------- #
def init_db():
    """Initializes the SQLite database and ensures the directory structure exists."""
    # Ensure the parent directory for the DB and file storage exists
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    
    conn = None
    try:
        # Connect to DB with a timeout and enable Write-Ahead Logging (WAL) for better concurrency
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS theses (
                thesis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT NOT NULL,
                course TEXT NOT NULL,
                year INTEGER NOT NULL,
                keywords TEXT,
                file_path TEXT NOT NULL,
                date_uploaded DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
        messagebox.showerror("DB Error", f"Database initialization failed: {e}")
    finally:
        if conn:
            conn.close()

# ---------------- Keyword Extraction ---------------- #
def extract_keywords(text, num_keywords=5):
    """Extracts keywords from text using KeyBERT."""
    if not kw_model:
        return "Keyword model unavailable."
    try:
        keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2),
                                             stop_words='english', top_n=num_keywords)
        return ", ".join([kw[0] for kw in keywords])
    except Exception as e:
        print(f"Keyword extraction failed: {e}")
        return "Extraction failed."

# ---------------- PDF Preview ---------------- #
def preview_pdf_first_page(pdf_path, pdf_label):
    """Loads the first page of a PDF, converts it to an image, and displays it."""
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        
        # Increased matrix scale for higher resolution preview
        matrix = fitz.Matrix(2, 2) 
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        # Convert pixmap to PIL Image
        img_buffer = io.BytesIO(pix.tobytes("ppm"))
        image = Image.open(img_buffer)
        image.thumbnail((380, 480))
        
        # Create PhotoImage and store a reference to prevent garbage collection
        photo = ImageTk.PhotoImage(image, master=pdf_label)
        
        pdf_label.config(image=photo, text="")
        pdf_label.image = photo
        
        doc.close() # Crucial: Close the document
    except Exception as e:
        pdf_label.config(text=f"Preview Error:\n{str(e)[:50]}", image="")

# ---------------- Upload / Update PDF ---------------- #
def upload_file_wrapper(course_entry, title_entry, file_path_var, pdf_label,
                        authors_entry=None, year_entry=None, keyword_label=None):
    """Opens file dialog, sets path, extracts metadata, and updates preview."""
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        try:
            # Check if the file path is the same as the target path (already copied)
            # If the user selects a file that is the one currently saved in the repository, 
            # we need to ensure we don't try to access it while it's locked.
            
            # --- Key Step: Clear any old preview lock before opening new file ---
            pdf_label.config(image="", text="Loading PDF...")
            pdf_label.image = None 
            
            doc = fitz.open(file_path)
            # Read first few pages for metadata/abstract
            first_page_text = doc[0].get_text()
            
            abstract_text = ""
            for i in range(min(2, len(doc))):
                abstract_text += doc[i].get_text()
            
            doc.close() # Crucial: Close the document after reading
            
            # --- Metadata Extraction ---
            
            # Authors extraction (Simple pattern: Last, First)
            name_pattern = r'([A-Z][\wñÑáéíóúüÁÉÍÓÚÜ\-]*, [A-Z][a-zA-ZñÑáéíóúüÁÉÍÓÚÜ\-]+)'
            name_lines = re.findall(name_pattern, first_page_text)
            # Filter out common non-author location/university names
            filtered_names = [name for name in name_lines if not any(word in name for word in ["Cainta", "Rizal", "University", "College"])]
            authors = ", ".join(filtered_names)
            
            # Year extraction (Month YYYY pattern)
            year_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', first_page_text)
            year = year_match.group(1) if year_match else ""
            
            # --- Fill GUI entries ---
            title_entry.delete(0, tk.END)
            title_entry.insert(0, os.path.splitext(os.path.basename(file_path))[0])
            
            if authors_entry:
                authors_entry.delete(0, tk.END)
                authors_entry.insert(0, authors)
                
            if year_entry:
                year_entry.delete(0, tk.END)
                year_entry.insert(0, year)
                
            if keyword_label:
                keyword_label.config(text=extract_keywords(abstract_text))

            file_path_var.set(file_path)
            preview_pdf_first_page(file_path, pdf_label)
            
        except Exception as e:
            messagebox.showerror("File Error", f"Error processing file: {str(e)}")

# ---------------- Save / Update Thesis ---------------- #
def save_thesis(title_entry, authors_entry, course_entry, year_entry, file_path_var,
                keyword_label, root, pdf_label, thesis_id=None):
    """Validates data, copies file, applies watermark, and updates database."""
    title = title_entry.get().strip()
    authors = authors_entry.get().strip()
    course = course_entry.get().strip()
    year = year_entry.get().strip()
    file_path = file_path_var.get().strip()
    keywords = keyword_label.cget("text")

    if not all([title, authors, course, year, file_path]) or course == "Select Course":
        messagebox.showerror("Error", "Please fill in all required fields and upload a PDF.")
        return

    # --- FIX FOR WINERROR 32: Release the file lock before file operations ---
    # Clearing the image reference ensures the Tkinter/Pillow resources are released,
    # dropping any file handle that might cause the "file being used" error.
    pdf_label.config(image="", text="Processing file...")
    pdf_label.image = None 

    conn = None
    try:
        # 1. File management & Copy
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thesis_files")
        os.makedirs(base_dir, exist_ok=True)
        course_folder = os.path.join(base_dir, course.lower())
        os.makedirs(course_folder, exist_ok=True)
        
        # Create a safe, unique filename
        original_filename = os.path.basename(file_path)
        safe_filename = re.sub(r'[\\/*?:"<>|\r\n]', "_", original_filename)
        # Use thesis ID if updating, otherwise use filename
        if thesis_id:
            safe_filename = f"{thesis_id}_{safe_filename}"
        
        target_path = os.path.join(course_folder, safe_filename)
        
        # Copy the original file to the repository if it's new or imported from outside
        if not os.path.exists(target_path) or file_path != target_path:
            shutil.copy2(file_path, target_path)

        # 2. Watermark function
        def add_watermark(input_pdf, output_pdf):
            """Adds a 'CCC RESEARCH PROPERTY' watermark to every page of the PDF."""
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            page_width, page_height = letter
            
            # Draw Watermark Text
            can.setFont("Helvetica-Bold", 30)
            can.setFillColorRGB(0.6, 0.6, 0.6)
            can.saveState()
            
            # Rotate and set transparency
            can.translate(page_width/2 - 150, page_height/2)
            can.rotate(45)
            can.setFillAlpha(0.3)
            can.drawString(0, 0, "CCC RESEARCH PROPERTY")
            can.restoreState()
            can.save()
            packet.seek(0)
            
            try:
                watermark = PdfReader(packet)
                watermark_page = watermark.pages[0]
                
                # Use a temporary file for writing to prevent data loss on failure
                temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
                os.close(temp_fd)

                with open(input_pdf, "rb") as input_file:
                    reader = PdfReader(input_file)
                    writer = PdfWriter()
                    for page in reader.pages:
                        # Create a copy of the watermark page for merging (important in PyPDF2)
                        page.merge_page(watermark_page)
                        writer.add_page(page)
                
                    with open(temp_path, "wb") as output_file:
                        writer.write(output_file)

                # Atomically replace the original file with the watermarked temporary file
                shutil.move(temp_path, output_pdf)
                
            except Exception as w_err:
                messagebox.showwarning("Watermark Warning", f"Could not apply watermark. The file was saved without it. Details: {w_err}")

        # Apply watermark to the target file
        add_watermark(target_path, target_path)

        # 3. Save to DB
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()
        
        if thesis_id:
            # Update existing record
            c.execute('''UPDATE theses SET title=?, authors=?, course=?, year=?, keywords=?, file_path=? WHERE thesis_id=?''',
                      (title, authors, course, int(year), keywords, target_path, thesis_id))
            message = "Thesis updated successfully!"
        else:
            # Insert new record
            c.execute('''INSERT INTO theses (title, authors, course, year, keywords, file_path) VALUES (?, ?, ?, ?, ?, ?)''',
                      (title, authors, course, int(year), keywords, target_path))
            message = "Thesis saved successfully!"
            
        conn.commit()
        messagebox.showinfo("Success", message)
        
        # Reload the main treeview if it's available (assuming this is a Toplevel window)
        if hasattr(root.master, 'load_tree_data'):
             root.master.load_tree_data()
        
        root.destroy()
        
    except ValueError:
        messagebox.showerror("Error", "Year must be a valid number.")
    except sqlite3.OperationalError as db_err:
        messagebox.showerror("Database Error", f"Database is locked or busy. Please try again.\n\nDetails: {db_err}")
    except Exception as e:
        messagebox.showerror("Error", f"Operation failed: {e}")
    finally:
        if conn:
            conn.close()

# ---------------- Update GUI ---------------- #
class UpdateThesisApp:
    def __init__(self, master=None):
        init_db()
        self.root = tk.Toplevel(master) if master else tk.Tk()
        self.root.title("📚 Thesis Repository - Update Manager")
        self.root.configure(bg="#ecf0f1")
        self.root.geometry("1400x900")
        self.root.resizable(False, False)
        
        self.current_thesis_id = None
        self.all_theses_data = [] # To store all data for in-memory filtering
        self.setup_ui()
        self.load_tree_data()
        self.root.mainloop()

    def setup_ui(self):
        # ... (UI Setup remains mostly the same) ...
        # Main container with fixed layout
        main_container = tk.Frame(self.root, bg="#ecf0f1")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        main_container.pack_propagate(False)

        # =============== LEFT PANEL (Treeview) ===============
        left_panel = tk.Frame(main_container, bg="white", bd=0, relief="flat", width=850)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 15))
        left_panel.pack_propagate(False)

        # Header
        header_frame = tk.Frame(left_panel, bg="#2c3e50", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="📋 Thesis Records", font=("Segoe UI", 18, "bold"), 
                 bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=20, pady=15)
        
        # Search frame
        search_frame = tk.Frame(left_panel, bg="white", height=80)
        search_frame.pack(fill=tk.X, padx=15, pady=10)
        search_frame.pack_propagate(False)
        
        # Search bar row
        search_bar_frame = tk.Frame(search_frame, bg="white")
        search_bar_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(search_bar_frame, text="🔍", font=("Segoe UI", 14), bg="white").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = tk.Entry(search_bar_frame, font=("Segoe UI", 11), relief="solid", bd=1)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.search_entry.bind("<KeyRelease>", self.filter_treeview)
        
        # Filter row
        filter_frame = tk.Frame(search_frame, bg="white")
        filter_frame.pack(fill=tk.X)
        
        tk.Label(filter_frame, text="Course:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_course = ttk.Combobox(filter_frame, values=["All", "BSCS", "BSOA", "BSBA", "BSED", "BEED", "ABREED"], 
                                          state="readonly", font=("Segoe UI", 10), width=12)
        self.filter_course.pack(side=tk.LEFT, padx=(0, 15))
        self.filter_course.set("All")
        self.filter_course.bind("<<ComboboxSelected>>", self.filter_treeview)
        
        tk.Label(filter_frame, text="Year:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_year = ttk.Combobox(filter_frame, values=["All"], 
                                         state="readonly", font=("Segoe UI", 10), width=12)
        self.filter_year.pack(side=tk.LEFT)
        self.filter_year.set("All")
        self.filter_year.bind("<<ComboboxSelected>>", self.filter_treeview)

        # Treeview
        tree_container = tk.Frame(left_panel, bg="white")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        tree_scroll = ttk.Scrollbar(tree_container)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview", 
                        font=("Segoe UI", 10), 
                        rowheight=35, 
                        fieldbackground="white",
                        background="white",
                        borderwidth=0)
        style.configure("Custom.Treeview.Heading", 
                        font=("Segoe UI", 11, "bold"), 
                        background="#34495e", 
                        foreground="white",
                        borderwidth=1,
                        relief="flat")
        style.map('Custom.Treeview', 
                  background=[('selected', '#3498db')],
                  foreground=[('selected', 'white')])
        
        self.tree = ttk.Treeview(tree_container, 
                                 yscrollcommand=tree_scroll.set, 
                                 selectmode="browse", 
                                 columns=("ID", "Title", "Course", "Date"),
                                 style="Custom.Treeview",
                                 show="tree headings")
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)

        # Configure columns
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.column("ID", anchor="center", width=60, minwidth=60)
        self.tree.column("Title", anchor="w", width=450, minwidth=300)
        self.tree.column("Course", anchor="center", width=120, minwidth=100)
        self.tree.column("Date", anchor="center", width=180, minwidth=150)

        # Headings
        self.tree.heading("ID", text="ID", anchor="center")
        self.tree.heading("Title", text="Title", anchor="w")
        self.tree.heading("Course", text="Course", anchor="center")
        self.tree.heading("Date", text="Date Uploaded", anchor="center")
        
        # Tags
        self.tree.tag_configure('oddrow', background="#f8f9fa")
        self.tree.tag_configure('evenrow', background="white")
        
        self.tree.bind("<Double-1>", self.load_selected_thesis)

        # =============== RIGHT PANEL (Form & Preview) ===============
        right_panel = tk.Frame(main_container, bg="white", bd=0, relief="flat", width=520)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        right_panel.pack_propagate(False)

        # Header
        form_header = tk.Frame(right_panel, bg="#27ae60", height=60)
        form_header.pack(fill=tk.X, side=tk.TOP)
        form_header.pack_propagate(False)
        
        tk.Label(form_header, text="✏️ Edit Thesis", font=("Segoe UI", 18, "bold"), 
                 bg="#27ae60", fg="white").pack(side=tk.LEFT, padx=20, pady=15)

        # Scrollable form area
        canvas_frame = tk.Frame(right_panel, bg="white")
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        form_canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0)
        form_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=form_canvas.yview)
        scrollable_form = tk.Frame(form_canvas, bg="white")
        
        scrollable_form.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.create_window((0, 0), window=scrollable_form, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scrollbar.set)
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            form_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            form_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            form_canvas.unbind_all("<MouseWheel>")
        
        form_canvas.bind('<Enter>', _bind_to_mousewheel)
        form_canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Form fields
        form_content = tk.Frame(scrollable_form, bg="white")
        form_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        def create_field(parent, label_text, row):
            field_frame = tk.Frame(parent, bg="white")
            field_frame.pack(fill=tk.X, pady=8)
            
            tk.Label(field_frame, text=label_text, font=("Segoe UI", 11, "bold"), 
                     bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 5))
            return field_frame

        # Title
        title_frame = create_field(form_content, "📄 Title *", 0)
        self.title_entry = tk.Entry(title_frame, font=("Segoe UI", 11), relief="solid", bd=1)
        self.title_entry.pack(fill=tk.X, ipady=6)

        # Authors
        authors_frame = create_field(form_content, "👥 Authors *", 1)
        self.authors_entry = tk.Entry(authors_frame, font=("Segoe UI", 11), relief="solid", bd=1)
        self.authors_entry.pack(fill=tk.X, ipady=6)

        # Course & Year (side by side)
        course_year_frame = tk.Frame(form_content, bg="white")
        course_year_frame.pack(fill=tk.X, pady=8)
        
        course_container = tk.Frame(course_year_frame, bg="white")
        course_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        tk.Label(course_container, text="🎓 Course *", font=("Segoe UI", 11, "bold"), 
                 bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 5))
        self.course_entry = ttk.Combobox(course_container, 
                                         values=["BSCS","BSOA","BSBA","BSED","BEED","ABREED"], 
                                         state="readonly", 
                                         font=("Segoe UI", 11))
        self.course_entry.pack(fill=tk.X, ipady=4)
        self.course_entry.set("Select Course")
        
        year_container = tk.Frame(course_year_frame, bg="white")
        year_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(year_container, text="📅 Year *", font=("Segoe UI", 11, "bold"), 
                 bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 5))
        self.year_entry = tk.Entry(year_container, font=("Segoe UI", 11), relief="solid", bd=1)
        self.year_entry.pack(fill=tk.X, ipady=6)

        # File
        file_frame = create_field(form_content, "📎 PDF File *", 3)
        file_input_frame = tk.Frame(file_frame, bg="white")
        file_input_frame.pack(fill=tk.X)
        
        self.file_path_var = tk.StringVar()
        file_display = tk.Entry(file_input_frame, textvariable=self.file_path_var, 
                                 font=("Segoe UI", 10), state="readonly", relief="solid", bd=1)
        file_display.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        
        browse_btn = tk.Button(file_input_frame, text="Browse", font=("Segoe UI", 10, "bold"),
                               bg="#3498db", fg="white", relief="flat", bd=0, padx=15, pady=6,
                               cursor="hand2",
                               command=lambda: upload_file_wrapper(
                                   self.course_entry, self.title_entry, self.file_path_var, 
                                   self.pdf_preview_canvas, self.authors_entry, 
                                   self.year_entry, self.keyword_label))
        browse_btn.pack(side=tk.LEFT)

        # Keywords
        keyword_frame = create_field(form_content, "🏷️ Auto-Generated Keywords", 4)
        keyword_container = tk.Frame(keyword_frame, bg="#f8f9fa", relief="solid", bd=1, height=70)
        keyword_container.pack(fill=tk.X)
        keyword_container.pack_propagate(False)
        
        self.keyword_label = tk.Label(keyword_container, 
                                      text="Keywords will appear after uploading...", 
                                      font=("Segoe UI", 10), 
                                      fg="#7f8c8d", 
                                      bg="#f8f9fa",
                                      wraplength=440, 
                                      justify="left", 
                                      anchor="nw",
                                      padx=10, pady=10)
        self.keyword_label.pack(fill=tk.BOTH, expand=True)

        # PDF Preview
        preview_frame = tk.Frame(form_content, bg="white")
        preview_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(preview_frame, text="👁️ PDF Preview", font=("Segoe UI", 12, "bold"), 
                 bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 10))
        
        preview_container = tk.Frame(preview_frame, bg="#ecf0f1", relief="solid", 
                                     bd=1, width=480, height=500)
        preview_container.pack()
        preview_container.pack_propagate(False)
        
        self.pdf_preview_canvas = tk.Label(preview_container, 
                                           bg="#ecf0f1", 
                                           text="📄\n\nPDF preview will\nappear here",
                                           font=("Segoe UI", 12),
                                           fg="#95a5a6")
        self.pdf_preview_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Save Button
        save_btn_frame = tk.Frame(form_content, bg="white")
        save_btn_frame.pack(fill=tk.X, pady=20)
        
        self.save_btn = tk.Button(save_btn_frame, 
                                  text="💾 Save Changes", 
                                  font=("Segoe UI", 13, "bold"),
                                  bg="#27ae60", 
                                  fg="white", 
                                  relief="flat",
                                  bd=0,
                                  cursor="hand2",
                                  padx=30,
                                  pady=12,
                                  command=lambda: save_thesis(
                                      self.title_entry, self.authors_entry, self.course_entry,
                                      self.year_entry, self.file_path_var, self.keyword_label,
                                      self.root, self.pdf_preview_canvas, self.current_thesis_id))
        self.save_btn.pack()
        
        # Hover effects
        def on_enter(e):
            self.save_btn['bg'] = '#229954'
        def on_leave(e):
            self.save_btn['bg'] = '#27ae60'
        self.save_btn.bind("<Enter>", on_enter)
        self.save_btn.bind("<Leave>", on_leave)

    def load_tree_data(self):
        """Loads data from the database into the Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            c.execute("SELECT thesis_id, title, course, year, date_uploaded FROM theses ORDER BY date_uploaded DESC")
            rows = c.fetchall()
            
            # Store all data for filtering
            self.all_theses_data = rows
            
            # Populate year filter dropdown
            years = sorted(set([str(row[3]) for row in rows]), reverse=True)
            self.filter_year['values'] = ["All"] + years
            
            for idx, row in enumerate(rows):
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                # Truncate long titles for display
                title = (row[1][:45] + "...") if len(row[1]) > 48 else row[1]
                self.tree.insert("", "end", values=(row[0], title, row[2], row[4]), tags=(tag,))
        except sqlite3.OperationalError as db_err:
            messagebox.showerror("Database Error", f"Cannot access database. It may be locked by another process.\n\nDetails: {db_err}")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
        finally:
            if conn:
                conn.close()

    def filter_treeview(self, event=None):
        """Filter treeview based on search text, course, and year"""
        search_text = self.search_entry.get().lower()
        selected_course = self.filter_course.get()
        selected_year = self.filter_year.get()
        
        # Clear current treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter and display
        idx = 0
        for row in self.all_theses_data:
            thesis_id, title, course, year, date_uploaded = row
            
            # Apply filters
            course_match = selected_course == "All" or course == selected_course
            year_match = selected_year == "All" or str(year) == selected_year
            search_match = (search_text in title.lower() or 
                            search_text in course.lower() or 
                            search_text in str(year))
            
            if course_match and year_match and search_match:
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                display_title = (title[:45] + "...") if len(title) > 48 else title
                self.tree.insert("", "end", values=(thesis_id, display_title, course, date_uploaded), tags=(tag,))
                idx += 1

    def load_selected_thesis(self, event=None):
        """Loads data from the selected row into the form fields."""
        selected = self.tree.selection()
        if not selected:
            return
            
        thesis_id = self.tree.item(selected[0], "values")[0]
        
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            c.execute("SELECT title, authors, course, year, keywords, file_path FROM theses WHERE thesis_id=?", (thesis_id,))
            thesis = c.fetchone()
        except sqlite3.OperationalError as db_err:
            messagebox.showerror("Database Error", f"Cannot access database. Please close any other programs using it.\n\nDetails: {db_err}")
            return
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return
        finally:
            if conn: 
                conn.close()

        if thesis:
            self.current_thesis_id = thesis_id
            
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, thesis[0])
            self.authors_entry.delete(0, tk.END)
            self.authors_entry.insert(0, thesis[1])
            self.course_entry.set(thesis[2])
            self.year_entry.delete(0, tk.END)
            self.year_entry.insert(0, thesis[3])
            
            self.keyword_label.config(text=thesis[4] if thesis[4] else "No keywords available")
            self.file_path_var.set(thesis[5])
            
            # Load and display the PDF preview
            preview_pdf_first_page(thesis[5], self.pdf_preview_canvas)

# Run the application
if __name__ == '__main__':
    app = UpdateThesisApp()
