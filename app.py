from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import datetime
import requests
import pandas as pd
import os

app = Flask(__name__)
DB_NAME = "library.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Books table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year_pub TEXT NOT NULL,
            publisher TEXT NOT NULL,
            genre TEXT NOT NULL,
            copies INTEGER NOT NULL,
            date_added TEXT DEFAULT (date('now')),
            date_updated TEXT DEFAULT NULL
        )
        ''')

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


timestap = datetime.datetime.now().strftime("%Y-%m-%d")
current_dir = os.getcwd()
library_tsv = os.path.join(current_dir, "library.tsv")

def export_library_db_to_tsv(db_path="library.db", output_path=library_tsv):
    """
    Exports all tables from a SQLite database to a single TSV file.
    
    Parameters:
        db_path (str): Path to the SQLite database file.
        output_path (str): Path for the output TSV file.
    """
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    
    with open(output_path, "w", encoding="utf-8") as f:
        for table in tables:
            if table == "books":
                f.write(f"## Table: {table}\n")  # header to separate tables
                
                # Load table into DataFrame
                df = pd.read_sql_query(f"SELECT * FROM {table};", conn)
                
                # Export to TSV format (without header line breaks)
                df.to_csv(f, sep="\t", index=False)
                f.write("\n\n")  # space between tables
    
    conn.close()
    print(f"Export complete! TSV saved to: {output_path}")


@app.route('/')
def index():
    return render_template("index.html")

# ---------------------------
# BOOK MANAGEMENT ROUTES
# ---------------------------
@app.route("/books")
def books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("books.html", books=books)

@app.route("/books/download")
def download_books():
    app_folder = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(
        directory=app_folder,
        path="library.tsv",
        as_attachment=True
    )

def greeklish_to_greek(text):
    mapping = {
        'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε', 'z': 'ζ', 'h': 'η',
        'th': 'θ', 'i': 'ι', 'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 'ks': 'ξ',
        'o': 'ο', 'p': 'π', 'r': 'ρ', 's': 'σ', 't': 'τ', 'y': 'υ', 'f': 'φ',
        'ch': 'χ', 'ps': 'ψ', 'w': 'ω'
    }
    for latin, greek in sorted(mapping.items(), key=lambda x: -len(x[0])):
        text = text.replace(latin, greek)
    return text



def get_info(isbn, lang="el"):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&langRestrict={lang}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        return -1

    data = response.json()
    items = data.get("items")
    
    if not items:
        print(f"No information found for ISBN: {isbn}")
        return -1
    
    volume_info = items[0].get("volumeInfo", {})
    
    title = volume_info.get("title", "N/A")
    authors = ", ".join(volume_info.get("authors", ["Unknown"]))
    year_pub = volume_info.get("publishedDate", "N/A").split("-")[0]  # just the year
    publisher = volume_info.get("publisher", "N/A")

    # title = greeklish_to_greek(title)
    # authors = greeklish_to_greek(authors)
    # year_pub = greeklish_to_greek(year_pub)
    # publisher = greeklish_to_greek(publisher)

    book_data = {
        "title": title,
        "author": authors,
        "year_pub": year_pub,
        "publisher": publisher
    }
    
    return book_data

@app.route("/books/add_full_info", methods=("GET", "POST"))
def add_book_full_info():

    conn = get_db_connection()
    date_added = datetime.datetime.now().strftime("%Y-%m-%d")
    date_updated = None

    if request.method == "POST":
        isbn = request.form["isbn"]
        copies = request.form["copies"]
        title = request.form["title"]
        author = request.form["author"]
        year_pub = request.form["year_pub"]
        publisher = request.form["publisher"]
        genre = request.form["genre"]

        conn.execute("INSERT INTO books (isbn, title, author, year_pub, publisher, genre, copies, date_added, date_updated) VALUES (?,?, ?,?, ?, ?,?, ?, ?)",
                    (isbn, title, author, year_pub, publisher, genre, copies, date_added, date_updated))
        conn.commit()
        conn.close()
        export_library_db_to_tsv()
        return redirect(url_for("books"))

    return render_template("add_book_full_info.html", current_date=date_added)


@app.route("/books/add", methods=("GET", "POST"))
def add_book():
    conn = get_db_connection()
    date_added = datetime.datetime.now().strftime("%Y-%m-%d")
    date_updated = None
    
    if request.method == "POST":
        isbn = request.form["isbn"]
        copies = request.form["copies"]

        # ✅ Check if ISBN already exists
        existing = conn.execute("SELECT * FROM books WHERE isbn = ?", (isbn,)).fetchone()
        if existing:
            conn.close()
            return "Βιβλίο με αυτό το ISBN υπάρχει ήδη!", 400

        book_info = get_info(isbn)
        if book_info != -1:
            title = book_info["title"]
            author = book_info["author"]
            year_pub = book_info["year_pub"]
            publisher = book_info["publisher"]
            genre = "Unknown"

            conn.execute("INSERT INTO books (isbn, title, author, year_pub, publisher, genre, copies, date_added, date_updated) VALUES (?,?, ?,?, ?, ?,?, ?, ?)",
                        (isbn, title, author,  year_pub, publisher, genre, copies, date_added, date_updated))
            conn.commit()
            conn.close()
            export_library_db_to_tsv()
            return redirect(url_for("books"))
        else:
            return redirect(url_for("add_book_full_info"))

    return render_template("add_book.html", current_date=date_added)


@app.route("/books/edit/<int:id>", methods=("GET", "POST"))
def edit_book(id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (id,)).fetchone()

    date_updated = datetime.datetime.now().strftime("%Y-%m-%d")
    if request.method == "POST":
        isbn = request.form["isbn"]
        title = request.form["title"]
        author = request.form["author"]
        year_pub = request.form['year_pub']
        publisher = request.form["publisher"]
        genre = request.form["genre"]
        copies = request.form["copies"]

        conn.execute("UPDATE books SET isbn=?, title=?, author=?, year_pub=?, publisher=?, genre=?, copies=?, date_updated=? WHERE id=?",
                     (isbn, title, author, year_pub, publisher, genre, copies, date_updated, id))
        conn.commit()
        conn.close()
        return redirect(url_for("books"))

    conn.close()
    return render_template("edit_book.html", book=book)

# ---------------------------
# BOOK SEARCH ROUTE
# ---------------------------
@app.route("/books/search")
def search_books():
    search_query = request.args.get("q", "").strip()
    conn = get_db_connection()

    books = []
    if search_query:
        books = conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ?",
            (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")
        ).fetchall()

    conn.close()
    return render_template("search_books.html", books=books, search_query=search_query)


if __name__ == "__main__":
    init_db()
    export_library_db_to_tsv()
    app.run(port=5000, debug=True)