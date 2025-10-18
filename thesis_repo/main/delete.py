import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sqlite3
import os
import shutil
from PIL import Image, ImageTk
import fitz  # PyMuPDF

db_path = os.path.join(os.path.dirname(__file__), "thesis_repository.db")


def get_all_theses():
    """Retrieves all thesis records from the database."""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT thesis_id, title, authors, course, year, file_path FROM theses ORDER BY date_uploaded DESC')
        records = c.fetchall()
        conn.close()
        return records
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to load thesis records:\n{e}")
        return []


def delete_selected_thesis(tree, preview_label, on_success=None, on_refresh=None):
    """Deletes the selected thesis entry and its PDF file."""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a thesis to delete.")
        return
    
    item = tree.item(selected[0])
    thesis_id = item['values'][0]
    title = item['values'][1]
    file_path = item['values'][5]
    
    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete this thesis?\n\nTitle: {title}\n\nThis will permanently remove the entry and the PDF file."
    )
    
    if not confirm:
        return
    
    try:
        # Delete from database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('DELETE FROM theses WHERE thesis_id = ?', (thesis_id,))
        conn.commit()
        conn.close()
        
        # Delete PDF file
        project_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(project_dir, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
        
        messagebox.showinfo("Success", "Thesis entry and PDF file deleted successfully!")
        
        # Clear preview
        preview_label.config(image='')
        preview_label.image = None
        
        # Refresh the delete UI list
        if on_success:
            on_success()
        
        # Refresh the main UI
        if on_refresh:
            on_refresh()
            
    except Exception as e:
        messagebox.showerror("Delete Error", f"Failed to delete thesis:\n{e}")


def delete_all_theses(tree, preview_label, on_success=None, on_refresh=None):
    """Deletes all thesis entries and their PDF files."""
    records = get_all_theses()
    
    if not records:
        messagebox.showinfo("No Data", "There are no thesis entries to delete.")
        return
    
    confirm = messagebox.askyesno(
        "Confirm Delete All",
        f"⚠️ WARNING ⚠️\n\nYou are about to delete ALL {len(records)} thesis entries and their PDF files.\n\nThis action CANNOT be undone!\n\nAre you absolutely sure?"
    )
    
    if not confirm:
        return
    
    # Double confirmation for safety
    confirm2 = messagebox.askyesno(
        "Final Confirmation",
        "This is your last chance to cancel.\n\nDelete ALL thesis entries permanently?"
    )
    
    if not confirm2:
        return
    
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        deleted_count = 0
        
        # Delete all PDF files
        for record in records:
            file_path = record[5]
            full_path = os.path.join(project_dir, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                deleted_count += 1
        
        # Delete all database entries
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('DELETE FROM theses')
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", f"All {deleted_count} thesis entries and PDF files deleted successfully!")
        
        # Clear preview
        preview_label.config(image='')
        preview_label.image = None
        
        # Refresh the delete UI list
        if on_success:
            on_success()
        
        # Refresh the main UI
        if on_refresh:
            on_refresh()
            
    except Exception as e:
        messagebox.showerror("Delete Error", f"Failed to delete all theses:\n{e}")


def export_all_pdfs():
    """Exports all thesis PDFs to a user-selected folder."""
    records = get_all_theses()
    
    if not records:
        messagebox.showinfo("No Data", "There are no thesis PDFs to export.")
        return
    
    # Ask user to select destination folder
    dest_folder = filedialog.askdirectory(title="Select Destination Folder for PDF Export")
    
    if not dest_folder:
        return
    
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        export_folder = os.path.join(dest_folder, "Exported_Thesis_PDFs")
        os.makedirs(export_folder, exist_ok=True)
        
        exported_count = 0
        failed_files = []
        
        for record in records:
            thesis_id, title, authors, course, year, file_path = record
            source_path = os.path.join(project_dir, file_path)
            
            if os.path.exists(source_path):
                # Create subfolder by course
                course_folder = os.path.join(export_folder, course)
                os.makedirs(course_folder, exist_ok=True)
                
                # Copy file
                filename = os.path.basename(file_path)
                dest_path = os.path.join(course_folder, filename)
                
                # Handle duplicate filenames
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(course_folder, f"{base}_{counter}{ext}")
                        counter += 1
                
                shutil.copy2(source_path, dest_path)
                exported_count += 1
            else:
                failed_files.append(title)
        
        # Show results
        result_msg = f"Successfully exported {exported_count} PDF files to:\n{export_folder}"
        if failed_files:
            result_msg += f"\n\nFailed to export {len(failed_files)} files (not found):\n" + "\n".join(failed_files[:5])
            if len(failed_files) > 5:
                result_msg += f"\n... and {len(failed_files) - 5} more"
        
        messagebox.showinfo("Export Complete", result_msg)
        
        # Open the folder
        if os.name == 'nt':  # Windows
            os.startfile(export_folder)
        elif os.name == 'posix':  # macOS and Linux
            os.system(f'open "{export_folder}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{export_folder}"')
            
    except Exception as e:
        messagebox.showerror("Export Error", f"Failed to export PDFs:\n{e}")


def preview_pdf_thumbnail(pdf_path, preview_label):
    """Displays a thumbnail preview of the PDF's first page."""
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(project_dir, pdf_path)
        
        if not os.path.exists(full_path):
            preview_label.config(image='', text="PDF file not found")
            return
        
        doc = fitz.open(full_path)
        page = doc.load_page(0)
        zoom = 1.5
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        # Save temp image
        temp_path = "delete_preview_temp.png"
        pix.save(temp_path)
        
        # Display in label
        image = Image.open(temp_path)
        image = image.resize((400, 500), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image, master=preview_label)
        preview_label.config(image=photo, text="")
        preview_label.image = photo
        
        doc.close()
        
    except Exception as e:
        preview_label.config(image='', text=f"Preview error:\n{str(e)}")


def on_tree_select(event, tree, preview_label):
    """Handles selection in the treeview to show PDF preview."""
    selected = tree.selection()
    if selected:
        item = tree.item(selected[0])
        file_path = item['values'][5]
        preview_pdf_thumbnail(file_path, preview_label)


def refresh_tree(tree):
    """Refreshes the treeview with current database records."""
    # Clear existing items
    for item in tree.get_children():
        tree.delete(item)
    
    # Load fresh data
    records = get_all_theses()
    for record in records:
        tree.insert('', 'end', values=record)


def open_delete_management_ui(on_refresh=None):
    """Creates and runs the delete & export management UI.
    
    Args:
        on_refresh: Optional callback function to refresh the main UI after deletions
    """
    root = tk.Toplevel()
    root.title("🗑️ Thesis Delete & Export Manager")
    root.geometry("1400x800")
    root.configure(bg="#f8f9fa")
    root.resizable(True, True)
    
    # Main container
    main_frame = tk.Frame(root, bg="#f8f9fa")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Top button frame
    button_frame = tk.Frame(main_frame, bg="#f8f9fa", height=80)
    button_frame.pack(fill=tk.X, pady=(0, 10))
    button_frame.pack_propagate(False)
    
    tk.Label(button_frame, text="Thesis Management", font=("Arial", 18, "bold"),
             bg="#f8f9fa", fg="#2c3e50").pack(pady=(5, 10))
    
    btn_container = tk.Frame(button_frame, bg="#f8f9fa")
    btn_container.pack()
    
    # Content frame (split into list and preview)
    content_frame = tk.Frame(main_frame, bg="#f8f9fa")
    content_frame.pack(fill=tk.BOTH, expand=True)
    
    # Left side - Treeview
    left_frame = tk.Frame(content_frame, bg="#ffffff", relief="groove", bd=2)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    
    tk.Label(left_frame, text="📚 Thesis Records", font=("Arial", 14, "bold"),
             bg="#ffffff", fg="#2c3e50").pack(pady=10)
    
    # Treeview with scrollbar
    tree_frame = tk.Frame(left_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    scrollbar = ttk.Scrollbar(tree_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    columns = ('ID', 'Title', 'Authors', 'Course', 'Year', 'File Path')
    tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                        yscrollcommand=scrollbar.set, height=20)
    
    # Configure columns
    tree.column('ID', width=50, anchor='center')
    tree.column('Title', width=300, anchor='w')
    tree.column('Authors', width=200, anchor='w')
    tree.column('Course', width=80, anchor='center')
    tree.column('Year', width=60, anchor='center')
    tree.column('File Path', width=200, anchor='w')
    
    for col in columns:
        tree.heading(col, text=col, anchor='center')
    
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=tree.yview)
    
    # Right side - Preview
    right_frame = tk.Frame(content_frame, bg="#f0f3f4", relief="groove", bd=2, width=450)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
    right_frame.pack_propagate(False)
    
    tk.Label(right_frame, text="PDF Preview", font=("Arial", 14, "bold"),
             bg="#f0f3f4", fg="#2c3e50").pack(pady=10)
    
    preview_label = tk.Label(right_frame, bg="#dfe6e9", text="Select a thesis to preview",
                            font=("Arial", 11), fg="#7f8c8d", relief="sunken", bd=1)
    preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    # Bind selection event
    tree.bind('<<TreeviewSelect>>', lambda e: on_tree_select(e, tree, preview_label))
    
    # Load initial data
    refresh_tree(tree)
    
    # Create buttons with refresh callback
    def refresh_callback():
        refresh_tree(tree)
        preview_label.config(image='', text="Select a thesis to preview")
        preview_label.image = None
        
        # Call main UI refresh if provided
        if on_refresh:
            try:
                on_refresh()
            except Exception as e:
                print(f"Main UI refresh error: {e}")
    
    delete_selected_btn = tk.Button(btn_container, text="🗑️ Delete Selected",
                                    font=("Arial", 12, "bold"), bg="#e74c3c", fg="white",
                                    width=18, height=2, relief="raised", bd=2,
                                    command=lambda: delete_selected_thesis(tree, preview_label, refresh_callback, on_refresh))
    delete_selected_btn.pack(side=tk.LEFT, padx=5)
    
    delete_all_btn = tk.Button(btn_container, text="⚠️ Delete All",
                               font=("Arial", 12, "bold"), bg="#c0392b", fg="white",
                               width=18, height=2, relief="raised", bd=2,
                               command=lambda: delete_all_theses(tree, preview_label, refresh_callback, on_refresh))
    delete_all_btn.pack(side=tk.LEFT, padx=5)
    
    export_btn = tk.Button(btn_container, text="📦 Export All PDFs",
                          font=("Arial", 12, "bold"), bg="#3498db", fg="white",
                          width=18, height=2, relief="raised", bd=2,
                          command=export_all_pdfs)
    export_btn.pack(side=tk.LEFT, padx=5)
    
    refresh_btn = tk.Button(btn_container, text="🔄 Refresh",
                           font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                           width=15, height=2, relief="raised", bd=2,
                           command=refresh_callback)
    refresh_btn.pack(side=tk.LEFT, padx=5)
    
    root.mainloop()


# Run the UI
if __name__ == "__main__":
    open_delete_management_ui()