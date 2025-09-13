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
# This model is loaded once to be used later.
kw_model = KeyBERT()
db_path = "thesis_repo/main/thesis_repository.db"


# Initialize the database and table.
def init_db():
    """
    Creates the database file and the 'theses' table if they don't already exist.
    This ensures the application has a consistent place to store data.
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

    Args:
        text (str): The input text to analyze.
        num_keywords (int): The number of keywords to extract.

    Returns:
        str: A comma-separated string of the extracted keywords, or an empty string on failure.
    """
    try:
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            top_n=num_keywords
        )
        return ", ".join([kw[0] for kw in keywords])
    except:
        return ""  # safer fallback


def upload_file_wrapper(course_entry, title_entry, file_path_var, pdf_preview_canvas, authors_entry=None, year_entry=None, keyword_debug_label=None):
    """
    Opens a file dialog for the user to select a PDF.
    On selection, it automatically extracts metadata (title, authors, year)
    and a preview image from the PDF to populate the form fields.

    Args:
        course_entry (ttk.Combobox): Tkinter widget for the course.
        title_entry (tk.Entry): Tkinter widget for the title.
        file_path_var (tk.StringVar): Tkinter variable to store the file path.
        pdf_preview_canvas (tk.Label): Tkinter widget to display the PDF preview.
        authors_entry (tk.Entry, optional): Tkinter widget for authors.
        year_entry (tk.Entry, optional): Tkinter widget for the year.
        keyword_debug_label (tk.Label, optional): Tkinter widget to display keywords.
    """
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        try:
            # Title from filename
            pdf_name = os.path.splitext(os.path.basename(file_path))[0]
            safe_title = re.sub(r'[\\/*?:"<>|\r\n]', "", pdf_name).strip().upper()

            # Read PDF text (first 3 pages) for metadata extraction
            doc = fitz.open(file_path)
            all_text = "\n".join([doc[i].get_text() for i in range(min(3, len(doc)))])
            doc.close()

            # Extract author names using a regular expression
            name_pattern = r'([A-Z][\wñÑáéíóúüÁÉÍÓÚÜ\-]*, [A-Z][a-zA-ZñÑáéíóúüÁÉÍÓÚÜ\-]+)'
            name_lines = re.findall(name_pattern, all_text)

            # Filter out irrelevant names (e.g., location names)
            filtered_names = [name for name in name_lines if "Cainta" not in name and "Rizal" not in name]
            authors = ", ".join(filtered_names)

            # Extract year (e.g., "March 2025")
            year_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', all_text)
            year = year_match.group(1) if year_match else ""

            # Fill the entry fields with the extracted metadata
            title_entry.delete(0, tk.END)
            title_entry.insert(0, safe_title)

            if authors_entry:
                authors_entry.delete(0, tk.END)
                authors_entry.insert(0, authors)

            if year_entry:
                year_entry.delete(0, tk.END)
                year_entry.insert(0, year)

            # Generate keywords from the title and update the keyword label
            if keyword_debug_label:
                keywords = extract_keywords(safe_title)
                keyword_debug_label.config(text=keywords)

            # Set the file path and generate a preview of the PDF's first page
            file_path_var.set(file_path)
            preview_pdf_first_page(file_path, pdf_preview_canvas)

        except Exception as e:
            messagebox.showerror("File Error", f"Failed to process PDF:\n{e}")


def preview_pdf_first_page(pdf_path, pdf_preview_canvas):
    """
    Generates an image preview of the first page of a PDF file
    and displays it on a Tkinter canvas.

    Args:
        pdf_path (str): The file path of the PDF.
        pdf_preview_canvas (tk.Label): The Tkinter widget to display the preview.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image_path = "preview_temp.png"
        pix.save(image_path)

        image = Image.open(image_path)
        image.thumbnail((550, 550), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image, master=pdf_preview_canvas)

        pdf_preview_canvas.image = photo  # Keep reference
        pdf_preview_canvas.config(image=photo)

        doc.close()
    except Exception as e:
        messagebox.showerror("Preview Error", f"Could not render PDF preview:\n{e}")


# Save thesis to database
def save_thesis(title_entry, authors_entry, course_entry, year_entry, file_path_var,
                keyword_debug_label, root, pdf_preview_canvas):
    """
    Validates form data, saves the PDF file to a structured directory,
    inserts the thesis metadata into the database, and clears the form.

    Args:
        title_entry (tk.Entry): Widget for the thesis title.
        authors_entry (tk.Entry): Widget for the author names.
        course_entry (ttk.Combobox): Widget for the course.
        year_entry (tk.Entry): Widget for the year.
        file_path_var (tk.StringVar): Variable holding the file path.
        keyword_debug_label (tk.Label): Widget to display keywords.
        root (tk.Tk): The root Tkinter window.
        pdf_preview_canvas (tk.Label): The widget for the PDF preview.
    """
    title = title_entry.get().strip()
    authors = authors_entry.get().strip()
    course = course_entry.get().strip()
    year = year_entry.get().strip()
    original_file_path = file_path_var.get().strip()

    if not all([title, authors, course, year, original_file_path]):
        messagebox.showerror("Error", "Please fill in all required fields and upload a PDF.")
        return

    # Extract keywords from the title before saving
    keywords = extract_keywords(title)
    keyword_debug_label.config(text=keywords)

    try:
        # Determine the project directory and the target directory for the file.
        project_dir = os.path.dirname(os.path.abspath(__file__))
        thesis_base_dir = os.path.join(project_dir, "thesis_files")

        # Create a subdirectory for the course if it doesn't exist.
        course_folder = os.path.join(thesis_base_dir, course.lower())
        os.makedirs(course_folder, exist_ok=True)

        # Sanitize the filename to prevent path issues.
        filename = os.path.basename(original_file_path)
        safe_filename = re.sub(r'[\\/*?:"<>|\r\n]', "_", filename)
        target_path = os.path.join(course_folder, safe_filename)

        # Copy the PDF file to the new location.
        shutil.copy2(original_file_path, target_path)

        # Get the relative path for database storage.
        relative_path = os.path.relpath(target_path, start=project_dir)

        # --- Insert into database ---
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO theses (title, authors, course, year, keywords, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, authors, course, int(year), keywords, relative_path))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Thesis entry saved and file uploaded.")

        # Clear fields after 3 seconds for user feedback.
        root.after(3000, lambda: clear_fields(title_entry, authors_entry, course_entry,
                                             year_entry, file_path_var, pdf_preview_canvas,
                                             keyword_debug_label))
        root.destroy()

    except Exception as e:
        messagebox.showerror("Database/File Error", str(e))


# Clear the form
def clear_fields(title_entry, authors_entry, course_entry, year_entry, file_path_var, pdf_preview_canvas, keyword_debug_label):
    """
    Clears all input fields and the PDF preview to reset the form.

    Args:
        title_entry (tk.Entry): Widget for the thesis title.
        authors_entry (tk.Entry): Widget for the author names.
        course_entry (ttk.Combobox): Widget for the course.
        year_entry (tk.Entry): Widget for the year.
        file_path_var (tk.StringVar): Variable holding the file path.
        pdf_preview_canvas (tk.Label): The widget for the PDF preview.
        keyword_debug_label (tk.Label): Widget to display keywords.
    """
    title_entry.delete(0, tk.END)
    authors_entry.delete(0, tk.END)
    course_entry.set("Select Course")
    year_entry.delete(0, tk.END)
    file_path_var.set("")
    pdf_preview_canvas.config(image='')
    pdf_preview_canvas.image = None
    keyword_debug_label.config(text="")


# Main GUI
def open_thesis_entry_form():
    """
    Creates and runs the main GUI for the thesis entry form.
    """
    init_db()
    root = tk.Tk()
    root.title("Thesis Entry Form")
    root.geometry("1600x700")
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

    tk.Label(left_frame, text="Authors:*", font=font_label).grid(row=1, column=0, **label_opts)
    authors_entry = tk.Entry(left_frame, width=60, font=font_entry)
    authors_entry.grid(row=1, column=1, **label_opts)

    tk.Label(left_frame, text="Course:*", font=font_label).grid(row=2, column=0, **label_opts)
    course_options = ["BSCS", "BSOA", "BSBA", "BSED", "BEED", "ABREED"]
    course_entry = ttk.Combobox(left_frame, values=course_options, font=font_entry, width=57, state="readonly")
    course_entry.grid(row=2, column=1, **label_opts)
    course_entry.set("Select Course")

    tk.Label(left_frame, text="Year:*", font=font_label).grid(row=3, column=0, **label_opts)
    year_entry = tk.Entry(left_frame, width=60, font=font_entry)
    year_entry.grid(row=3, column=1, **label_opts)

    tk.Label(left_frame, text="PDF File:*", font=font_label).grid(row=4, column=0, **label_opts)
    file_path_var = tk.StringVar()
    tk.Entry(left_frame, textvariable=file_path_var, width=45, font=font_entry, state='readonly').grid(row=4, column=1, sticky='w', padx=5)
    tk.Button(
    left_frame, text="Browse", font=font_label,
    command=lambda: upload_file_wrapper(
        course_entry, title_entry, file_path_var, pdf_preview_canvas,
        authors_entry, year_entry, keyword_debug_label
    )
).grid(row=4, column=1, sticky='e', padx=5)

    tk.Label(left_frame, text="Auto Keywords (from Title):", font=font_label).grid(row=5, column=0, **label_opts)
    keyword_debug_label = tk.Label(left_frame, text="", font=("Arial", 10), fg="blue", wraplength=400, justify="left")
    keyword_debug_label.grid(row=5, column=1, **label_opts)

    tk.Button(left_frame, text="Save Thesis", font=("Arial", 12, "bold"),
              command=lambda: save_thesis(title_entry, authors_entry, course_entry, year_entry, file_path_var, keyword_debug_label, root, pdf_preview_canvas),
              bg="green", fg="white", width=25).grid(row=6, column=0, pady=20, sticky='e')

    tk.Label(right_frame, text="First Page", bg="#f0f0f0", font=("Arial", 14, "bold")).pack(pady=10)
    pdf_preview_canvas = tk.Label(right_frame, bg="#f0f0f0")
    pdf_preview_canvas.pack(pady=10)

    root.mainloop()


# Run GUI
if __name__ == "__main__":
    open_thesis_entry_form()
