import tkinter as tk
from tkinter import filedialog, messagebox
import sqlite3
import os
import shutil
from tkinter import ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import re
from keybert import KeyBERT

# Initialize BERT model for keyword extraction.
kw_model = KeyBERT()
db_path = os.path.join(os.path.dirname(__file__), "thesis_repository.db")


# Initialize the database and table.
def init_db():
    """
    Creates the database file and the 'theses' table if they don't already exist.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
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
    conn.close()


# Extract keywords using KeyBERT
def extract_keywords(text, num_keywords=5):
    """
    Extracts relevant keywords from a given text using the KeyBERT model.
    """
    try:
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            top_n=num_keywords
        )
        return ", ".join([kw[0] for kw in keywords])
    except Exception as e:
        print(f"KeyBERT extraction failed: {e}")
        return ""  # safer fallback


def upload_file_wrapper(course_entry, title_entry, file_path_var, pdf_preview_canvas,
                        authors_entry=None, year_entry=None, keyword_debug_label=None):
    """
    Opens a file dialog to select a PDF and extracts metadata to populate the form.
    """
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        try:
            # Title from filename
            pdf_name = os.path.splitext(os.path.basename(file_path))[0]

            # Convert underscores to spaces and clean
            natural_title = pdf_name.replace('_', ' ')
            safe_title = re.sub(r'[\\/*?:"<>|\r\n]', "", natural_title).strip().upper()

            doc = fitz.open(file_path)

            # --- Authors: only first page ---
            first_page_text = doc[0].get_text()
            name_pattern = r'([A-Z][\wñÑáéíóúüÁÉÍÓÚÜ\-]*, [A-Z][a-zA-ZñÑáéíóúüÁÉÍÓÚÜ\-]+)'
            name_lines = re.findall(name_pattern, first_page_text)
            filtered_names = [name for name in name_lines if "Cainta" not in name and "Rizal" not in name]
            authors = ", ".join(filtered_names)

            # --- Year: look in first page only ---
            year_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', first_page_text)
            year = year_match.group(1) if year_match else ""

            # --- Abstract for keyword extraction: first + second page ---
            num_pages_for_keywords = min(2, len(doc))
            abstract_text = "\n".join([doc[i].get_text() for i in range(num_pages_for_keywords)])

            doc.close()

            # Fill entries
            title_entry.delete(0, tk.END)
            title_entry.insert(0, safe_title)

            if authors_entry:
                authors_entry.delete(0, tk.END)
                authors_entry.insert(0, authors)

            if year_entry:
                year_entry.delete(0, tk.END)
                year_entry.insert(0, year)

            if keyword_debug_label:
                keywords = extract_keywords(abstract_text)
                keyword_debug_label.config(text=keywords)

            # Set file path and preview
            file_path_var.set(file_path)
            preview_pdf_first_page(file_path, pdf_preview_canvas)

        except Exception as e:
            messagebox.showerror("File Error", f"Failed to process PDF:\n{e}")


def preview_pdf_first_page(pdf_path, pdf_preview_canvas):
    """
    Generates an image preview of the first page of a PDF.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        zoom_x, zoom_y = 2, 2
        matrix = fitz.Matrix(zoom_x, zoom_y)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = "preview_temp.png"
        pix.save(image_path)
        image = Image.open(image_path)
        image = image.resize((750, 950), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image, master=pdf_preview_canvas)
        pdf_preview_canvas.image = photo
        pdf_preview_canvas.config(image=photo)
        doc.close()
    except Exception as e:
        messagebox.showerror("Preview Error", f"Could not render PDF preview:\n{e}")


def save_thesis(title_entry, authors_entry, course_entry, year_entry, file_path_var,
                keyword_debug_label, root, pdf_preview_canvas, on_success=None):
    title = title_entry.get().strip()
    authors = authors_entry.get().strip()
    course = course_entry.get().strip()
    year = year_entry.get().strip()
    original_file_path = file_path_var.get().strip()

    if not all([title, authors, course, year, original_file_path]):
        messagebox.showerror("Error", "Please fill in all required fields and upload a PDF.")
        return

    # Use already extracted keywords
    keywords = keyword_debug_label.cget("text")

    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        thesis_base_dir = os.path.join(project_dir, "thesis_files")
        os.makedirs(thesis_base_dir, exist_ok=True)

        course_folder = os.path.join(thesis_base_dir, course.lower())
        os.makedirs(course_folder, exist_ok=True)

        filename = os.path.basename(original_file_path)
        safe_filename = re.sub(r'[\\/*?:"<>|\r\n]', "_", filename)
        target_path = os.path.join(course_folder, safe_filename)
        shutil.copy2(original_file_path, target_path)
        relative_path = os.path.relpath(target_path, start=project_dir)

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO theses (title, authors, course, year, keywords, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, authors, course, int(year), keywords, relative_path))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Thesis entry saved and file uploaded successfully!")

        if on_success:
            try:
                on_success()
            except Exception as e:
                print("Refresh error:", e)

        root.destroy()

    except Exception as e:
        messagebox.showerror("Database/File Error", str(e))


def clear_fields(title_entry, authors_entry, course_entry, year_entry, file_path_var, pdf_preview_canvas, keyword_debug_label):
    """
    Clears all form fields and PDF preview.
    """
    title_entry.delete(0, tk.END)
    authors_entry.delete(0, tk.END)
    course_entry.set("Select Course")
    year_entry.delete(0, tk.END)
    file_path_var.set("")
    pdf_preview_canvas.config(image='')
    pdf_preview_canvas.image = None
    keyword_debug_label.config(text="")


def open_thesis_entry_form(on_success=None):
    """
    Creates and runs the GUI for the thesis entry form.
    """
    init_db()
    root = tk.Toplevel()
    root.title("📚 Thesis Entry Form")
    root.transient()
    root.focus_force()
    root.wait_visibility()
    root.geometry("1700x1000")
    root.configure(bg="#f8f9fa")
    root.resizable(False, False)

    # --- LEFT FRAME ---
    left_frame = tk.Frame(root, width=650, height=900, padx=25, pady=25, bg="#ffffff", relief="groove", bd=2)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
    left_frame.pack_propagate(False)

    header = tk.Label(left_frame, text="Thesis Information", font=("Arial", 18, "bold"), bg="#ffffff", fg="#2c3e50")
    header.grid(row=0, column=0, columnspan=2, pady=(0, 20))

    font_label = ("Arial", 12)
    font_entry = ("Arial", 12)
    label_opts = {'sticky': 'w', 'padx': 5, 'pady': 10}

    # Title
    tk.Label(left_frame, text="Title:*", font=font_label, bg="#ffffff").grid(row=1, column=0, **label_opts)
    title_entry = tk.Entry(left_frame, width=50, font=font_entry)
    title_entry.grid(row=1, column=1, **label_opts)

    # Authors
    tk.Label(left_frame, text="Authors:*", font=font_label, bg="#ffffff").grid(row=2, column=0, **label_opts)
    authors_entry = tk.Entry(left_frame, width=50, font=font_entry)
    authors_entry.grid(row=2, column=1, **label_opts)

    # Course
    tk.Label(left_frame, text="Course:*", font=font_label, bg="#ffffff").grid(row=3, column=0, **label_opts)
    course_options = ["BSCS", "BSOA", "BSBA", "BSED", "BEED", "ABREED"]
    course_entry = ttk.Combobox(left_frame, values=course_options, font=font_entry, width=47, state="readonly")
    course_entry.grid(row=3, column=1, **label_opts)
    course_entry.set("Select Course")

    # Year
    tk.Label(left_frame, text="Year:*", font=font_label, bg="#ffffff").grid(row=4, column=0, **label_opts)
    year_entry = tk.Entry(left_frame, width=50, font=font_entry)
    year_entry.grid(row=4, column=1, **label_opts)

    # PDF File
    tk.Label(left_frame, text="PDF File:*", font=font_label, bg="#ffffff").grid(row=5, column=0, **label_opts)
    file_path_var = tk.StringVar()
    file_entry = tk.Entry(left_frame, textvariable=file_path_var, width=37, font=font_entry, state="normal")
    file_entry.grid(row=5, column=1, sticky='w', padx=5, pady=10)
    pdf_preview_canvas = tk.Label(left_frame, bg="#dfe6e9")
    browse_btn = tk.Button(left_frame, text="📂 Browse", font=font_label, bg="#3498db", fg="white",
                           command=lambda: upload_file_wrapper(
                               course_entry, title_entry, file_path_var, pdf_preview_canvas,
                               authors_entry, year_entry, keyword_debug_label
                           ))
    browse_btn.grid(row=5, column=1, sticky='e', padx=5, pady=10)

    # Keywords
    tk.Label(left_frame, text="Auto Keywords (from Title):", font=font_label, bg="#ffffff").grid(row=6, column=0, **label_opts)
    keyword_debug_label = tk.Label(left_frame, text="", font=("Arial", 10, "italic"), fg="#2980b9",
                                   wraplength=380, justify="left", bg="#ffffff")
    keyword_debug_label.grid(row=6, column=1, **label_opts)

    # Save Button
    save_btn = tk.Button(left_frame, text="💾 Save Thesis", font=("Arial", 13, "bold"),
                         command=lambda: save_thesis(
                             title_entry, authors_entry, course_entry, year_entry,
                             file_path_var, keyword_debug_label, root,
                             pdf_preview_canvas, on_success=on_success
                         ),
                         bg="#27ae60", fg="white", width=25, height=2, relief="raised", bd=2)
    save_btn.grid(row=7, column=0, columnspan=2, pady=25)

    # --- RIGHT FRAME (Preview) ---
    right_frame = tk.Frame(root, width=950, height=900, padx=20, pady=20, bg="#f0f3f4", relief="groove", bd=2)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
    right_frame.pack_propagate(False)

    tk.Label(right_frame, text="PDF Preview", bg="#f0f3f4", font=("Arial", 16, "bold"), fg="#2c3e50").pack(pady=10)
    pdf_preview_canvas = tk.Label(right_frame, bg="#dfe6e9", relief="sunken", bd=1)
    pdf_preview_canvas.pack(pady=15, expand=True, fill=tk.BOTH)

    root.mainloop()


# Run GUI
if __name__ == "__main__":
    open_thesis_entry_form()
