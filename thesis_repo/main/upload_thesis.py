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

# Initialize BERT model
kw_model = KeyBERT()
db_path = "thesis_repo/main/thesis_repository.db"

# Initialize the database
def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS theses (
            thesis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            abstract TEXT,
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
    try:
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            top_n=num_keywords
        )
        return ", ".join([kw[0] for kw in keywords])
    except Exception as e:
        return f"Keyword extraction error: {e}"

def upload_file_wrapper(course_entry, title_entry, file_path_var, pdf_preview_canvas, authors_entry=None, year_entry=None):
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        try:
            # Title from filename
            pdf_name = os.path.splitext(os.path.basename(file_path))[0]
            safe_title = re.sub(r'[\\/*?:"<>|\r\n]', "", pdf_name).strip().upper()

            # Read PDF text (first 3 pages)
            doc = fitz.open(file_path)
            all_text = "\n".join([doc[i].get_text() for i in range(min(1, len(doc)))])
            doc.close()

            name_pattern = r'([A-Z][\wñÑáéíóúüÁÉÍÓÚÜ\-]*, [A-Z][a-zA-ZñÑáéíóúüÁÉÍÓÚÜ\-]+)'
            name_lines = re.findall(name_pattern, all_text)

# Remove false positives like "Cainta, Rizal"
            filtered_names = [name for name in name_lines if "Cainta" not in name and "Rizal" not in name]

            authors = ", ".join(filtered_names)

            # Extract year (e.g., "March 2025")
            year_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', all_text)
            year = year_match.group(1) if year_match else ""

            # Fill fields
            title_entry.delete(0, tk.END)
            title_entry.insert(0, safe_title)

            if authors_entry:
                authors_entry.delete(0, tk.END)
                authors_entry.insert(0, authors)

            if year_entry:
                year_entry.delete(0, tk.END)
                year_entry.insert(0, year)

            # Set path and preview
            file_path_var.set(file_path)
            preview_pdf_first_page(file_path, pdf_preview_canvas)

        except Exception as e:
            messagebox.showerror("File Error", f"Failed to process PDF:\n{e}")




def preview_pdf_first_page(pdf_path, pdf_preview_canvas):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image_path = "preview_temp.png"
        pix.save(image_path)

        # Must use PhotoImage inside a Tkinter widget context
        image = Image.open(image_path)
        image.thumbnail((550, 550), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image, master=pdf_preview_canvas)

        pdf_preview_canvas.image = photo  # Keep reference
        pdf_preview_canvas.config(image=photo)

        doc.close()
    except Exception as e:
        messagebox.showerror("Preview Error", f"Could not render PDF preview:\n{e}")



# Save thesis to database
def save_thesis(title_entry, abstract_text, authors_entry, course_entry, year_entry, file_path_var, keyword_debug_label, root, pdf_preview_canvas):
    title = title_entry.get().strip()
    abstract = abstract_text.get("1.0", tk.END).strip()
    authors = authors_entry.get().strip()
    course = course_entry.get().strip()
    year = year_entry.get().strip()
    original_file_path = file_path_var.get().strip()

    if not all([title, authors, course, year, original_file_path]):
        messagebox.showerror("Error", "Please fill in all required fields and upload a PDF.")
        return

    keywords = extract_keywords(f"{title} {abstract}")
    keyword_debug_label.config(text=keywords)

    try:
        # ✅ Use relative folder from project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))  # this script's folder
        thesis_base_dir = os.path.join(project_dir, "thesis_files")
        course_folder = os.path.join(thesis_base_dir, course)

        os.makedirs(course_folder, exist_ok=True)

        # ✅ Clean and copy filename
        filename = os.path.basename(original_file_path)
        safe_filename = re.sub(r'[\\/*?:"<>|\r\n]', "_", filename)
        target_path = os.path.join(course_folder, safe_filename)

        shutil.copy2(original_file_path, target_path)

        # ✅ Save relative path from "main"
        relative_path = os.path.relpath(target_path, start=os.path.join(project_dir, ".."))

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO theses (title, abstract, authors, course, year, keywords, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, abstract, authors, course, int(year), keywords, relative_path))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Thesis entry saved and file uploaded.")
        root.after(3000, lambda: clear_fields(title_entry, abstract_text, authors_entry, course_entry, year_entry, file_path_var, pdf_preview_canvas, keyword_debug_label))

    except Exception as e:
        messagebox.showerror("Database/File Error", str(e))

# Clear the form
def clear_fields(title_entry, abstract_text, authors_entry, course_entry, year_entry, file_path_var, pdf_preview_canvas, keyword_debug_label):
    title_entry.delete(0, tk.END)
    abstract_text.delete("1.0", tk.END)
    authors_entry.delete(0, tk.END)
    course_entry.set("Select Course")
    year_entry.delete(0, tk.END)
    file_path_var.set("")
    pdf_preview_canvas.config(image='')
    pdf_preview_canvas.image = None
    keyword_debug_label.config(text="")

# Main GUI

def open_thesis_entry_form():
    init_db()
    root = tk.Tk()
    root.title("Thesis Entry Form")
    root.geometry("1500x700")
    root.resizable(False, False)

    left_frame = tk.Frame(root, width=600, height=700, padx=20, pady=20)
    left_frame.pack(side=tk.LEFT, fill=tk.Y)
    left_frame.pack_propagate(False)

    right_frame = tk.Frame(root, width=600, height=700, padx=20, pady=20, bg="#f0f0f0")
    right_frame.pack(side=tk.RIGHT, fill=tk.Y)
    right_frame.pack_propagate(False)

    font_label = ("Arial", 12)
    font_entry = ("Arial", 12)
    label_opts = {'sticky': 'w', 'padx': 5, 'pady': 8}

    tk.Label(left_frame, text="Title:*", font=font_label).grid(row=0, column=0, **label_opts)
    title_entry = tk.Entry(left_frame, width=60, font=font_entry)
    title_entry.grid(row=0, column=1, **label_opts)

    tk.Label(left_frame, text="Abstract:", font=font_label).grid(row=1, column=0, **label_opts)
    abstract_text = tk.Text(left_frame, height=7, width=45, font=font_entry)
    abstract_text.grid(row=1, column=1, **label_opts)

    tk.Label(left_frame, text="Authors:*", font=font_label).grid(row=2, column=0, **label_opts)
    authors_entry = tk.Entry(left_frame, width=60, font=font_entry)
    authors_entry.grid(row=2, column=1, **label_opts)

    tk.Label(left_frame, text="Course:*", font=font_label).grid(row=3, column=0, **label_opts)
    course_options = ["BSCS", "BSOA", "BSBA", "BSED", "BEED", "ABREED"]
    course_entry = ttk.Combobox(left_frame, values=course_options, font=font_entry, width=57, state="readonly")
    course_entry.grid(row=3, column=1, **label_opts)
    course_entry.set("Select Course")

    tk.Label(left_frame, text="Year:*", font=font_label).grid(row=4, column=0, **label_opts)
    year_entry = tk.Entry(left_frame, width=60, font=font_entry)
    year_entry.grid(row=4, column=1, **label_opts)

    tk.Label(left_frame, text="PDF File:*", font=font_label).grid(row=5, column=0, **label_opts)
    file_path_var = tk.StringVar()
    tk.Entry(left_frame, textvariable=file_path_var, width=45, font=font_entry, state='readonly').grid(row=5, column=1, sticky='w', padx=5)
    tk.Button(left_frame, text="Browse", font=font_label,
              command=lambda: upload_file_wrapper(course_entry, title_entry, file_path_var, pdf_preview_canvas, authors_entry, year_entry)).grid(row=5, column=1, sticky='e', padx=5)

    tk.Label(left_frame, text="Auto Keywords (Debug):", font=font_label).grid(row=6, column=0, **label_opts)
    keyword_debug_label = tk.Label(left_frame, text="", font=("Arial", 10), fg="blue", wraplength=400, justify="left")
    keyword_debug_label.grid(row=6, column=1, **label_opts)

    tk.Button(left_frame, text="Save Thesis", font=("Arial", 12, "bold"),
              command=lambda: save_thesis(title_entry, abstract_text, authors_entry, course_entry, year_entry, file_path_var, keyword_debug_label, root, pdf_preview_canvas),
              bg="green", fg="white", width=25).grid(row=7, column=0, pady=20, sticky='e')

    tk.Label(right_frame, text="First Page", bg="#f0f0f0", font=("Arial", 14, "bold")).pack(pady=10)
    pdf_preview_canvas = tk.Label(right_frame, bg="#f0f0f0")
    pdf_preview_canvas.pack(pady=10)

    root.mainloop()
