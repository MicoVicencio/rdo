import sqlite3
import fitz  # PyMuPDF
import base64
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)
DATABASE = 'thesis_repository.db'


# --- Database connection helper ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# --- Utility functions ---
def get_thesis_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM theses").fetchone()[0]
    conn.close()
    return count


def get_recent_theses(limit=10):
    conn = get_db_connection()
    theses = conn.execute(
        "SELECT title, course, date_uploaded FROM theses ORDER BY date_uploaded DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()

    formatted_theses = []
    for thesis in theses:
        try:
            dt_obj = datetime.strptime(thesis['date_uploaded'], "%Y-%m-%d %H:%M:%S")
            date_uploaded = dt_obj.strftime("%b %d, %Y - %I:%M %p")
        except:
            date_uploaded = thesis['date_uploaded']

        formatted_theses.append({
            'title': thesis['title'],
            'course': thesis['course'],
            'date_uploaded': date_uploaded
        })
    return formatted_theses


def get_courses():
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT course FROM theses ORDER BY course ASC").fetchall()
    conn.close()
    return [r["course"] for r in rows]


def get_years():
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT year FROM theses WHERE year IS NOT NULL ORDER BY year DESC").fetchall()
    conn.close()
    return [str(r["year"]) for r in rows]


# --- ABSTRACT IMAGE FUNCTION ---
def extract_abstract_images(pdf_path):
    """Extract the page containing 'abstract' and the next page as base64 images."""
    images = []
    try:
        doc = fitz.open(pdf_path)
        abstract_found = False

        for i in range(len(doc)):
            page = doc.load_page(i)
            text = page.get_text()
            
            if not abstract_found and "abstract" in text.lower():
                # Extract this page
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                images.append(base64.b64encode(img_bytes).decode("utf-8"))
                abstract_found = True

                # Extract the next page if it exists
                if i + 1 < len(doc):
                    next_page = doc.load_page(i + 1)
                    pix2 = next_page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes2 = pix2.tobytes("png")
                    images.append(base64.b64encode(img_bytes2).decode("utf-8"))
                break  # Stop after extracting abstract + next page

        doc.close()
    except Exception as e:
        print(f"Error extracting abstract images: {e}")

    return images



# --- ROUTES ---
@app.route('/')
def index():
    total_count = get_thesis_count()
    recent_entries = get_recent_theses(limit=10)
    courses = get_courses()
    years = get_years()
    return render_template(
        'index.html',
        total_count=total_count,
        recent_entries=recent_entries,
        courses=courses,
        years=years
    )


@app.route('/api/search')
def api_search():
    query = request.args.get('query', '').lower()
    year = request.args.get('year', '').strip()
    course = request.args.get('course', '').strip()
    keyword = request.args.get('keyword', '').lower().strip()

    conn = get_db_connection()
    sql = "SELECT title, course, year, date_uploaded, authors, keywords, file_path FROM theses WHERE 1=1"
    params = []

    if query:
        sql += " AND LOWER(title) LIKE ?"
        params.append(f"%{query}%")

    if year:
        sql += " AND CAST(year AS TEXT) = ?"
        params.append(str(year))

    if course:
        sql += " AND course = ?"
        params.append(course)

    if keyword:
        sql += " AND LOWER(keywords) LIKE ?"
        params.append(f"%{keyword}%")

    sql += " ORDER BY date_uploaded DESC LIMIT 100"
    results = conn.execute(sql, params).fetchall()
    conn.close()

    formatted = []
    for r in results:
        try:
            dt = datetime.strptime(r["date_uploaded"], "%Y-%m-%d %H:%M:%S")
            formatted_date = dt.strftime("%b %d, %Y - %I:%M %p")
        except:
            formatted_date = r["date_uploaded"]

        formatted.append({
            "title": r["title"].replace("_", " ").replace("-", " ").strip(),  # cleaned
            "course": r["course"],
            "year": str(r["year"]) if r["year"] else "-",
            "date_uploaded": formatted_date,
            "authors": r["authors"] or "-",
            "keywords": r["keywords"] or "-",
            "pdf_path": r["file_path"]
        })

    return jsonify(formatted)


# --- New route for multiple abstract images ---
@app.route('/get_abstract_image')
def get_abstract_image():
    pdf_file = request.args.get('pdf')
    if not pdf_file:
        return jsonify({"error": "No file path provided."})

    images = extract_abstract_images(pdf_file)
    if not images:
        return jsonify({"error": "Failed to extract images."})

    return jsonify({"images": images})


# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
