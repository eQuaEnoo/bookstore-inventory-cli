"""shelf_track - a command-line inventory manager for a bookstore.

Lets a clerk add, update, delete and search books stored in a SQLite
database (ebookstore.db), and view every book together with its author's
details. Books reference authors through a foreign key.
"""

import sqlite3
from contextlib import closing

DB_NAME = "ebookstore.db"
ID_LENGTH = 4

SEED_AUTHORS = [
    (1290, "Charles Dickens", "England"),
    (8937, "J.K. Rowling", "England"),
    (2356, "C.S. Lewis", "Ireland"),
    (6380, "J.R.R. Tolkien", "South Africa"),
    (5620, "Lewis Carroll", "England"),
]

SEED_BOOKS = [
    (3001, "A Tale of Two Cities", 1290, 30),
    (3002, "Harry Potter and the Philosopher's Stone", 8937, 40),
    (3003, "The Lion, the Witch and the Wardrobe", 2356, 25),
    (3004, "The Lord of the Rings", 6380, 37),
    (3005, "Alice's Adventures in Wonderland", 5620, 12),
]


# --------------------------------------------------------------------------
# Input helpers
# --------------------------------------------------------------------------

def is_valid_id(id_str):
    """Return True if id_str is a 4-digit numeric string."""
    return (id_str.isascii() and id_str.isdigit()
            and len(id_str) == ID_LENGTH)


def get_valid_qty(prompt):
    """Prompt until the user enters a non-negative whole number."""
    while True:
        try:
            qty = int(input(prompt).strip())
        except ValueError:
            print("Invalid quantity - please enter a whole number.")
            continue
        if qty < 0:
            print("Quantity cannot be negative. Try again.")
            continue
        return qty


def prompt_for_id(prompt, lookup):
    """Prompt for a 4-digit ID until `lookup(id)` returns a record.

    Enter 0 to cancel. Returns (id, record), or (None, None) if the
    user cancelled.
    """
    while True:
        id_str = input(f"{prompt} ({ID_LENGTH} digits, or 0 to cancel): ")
        id_str = id_str.strip()

        if id_str == "0":
            return None, None

        if not is_valid_id(id_str):
            print(f"Invalid ID - must be exactly {ID_LENGTH} digits. "
                  "Try again.")
            continue

        record = lookup(int(id_str))
        if record is None:
            print("No record found with that ID. Try again.")
            continue

        return int(id_str), record


# --------------------------------------------------------------------------
# Database setup
# --------------------------------------------------------------------------

def connect_db():
    """Open the ebookstore database with foreign keys enforced."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(cursor):
    """Create the author and book tables if they don't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS author (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            authorID INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            FOREIGN KEY (authorID) REFERENCES author(id)
        )
    """)


def seed_table(cursor, table, insert_sql, rows):
    """Insert `rows` into `table` only if the table is empty."""
    cursor.execute(f"SELECT COUNT(*) FROM {table}")  # table is a constant
    if cursor.fetchone()[0] == 0:
        cursor.executemany(insert_sql, rows)


def seed_data(cursor):
    """Populate the author and book tables with the starting data."""
    seed_table(cursor, "author",
               "INSERT INTO author (id, name, country) VALUES (?, ?, ?)",
               SEED_AUTHORS)
    seed_table(cursor, "book",
               "INSERT INTO book (id, title, authorID, qty) "
               "VALUES (?, ?, ?, ?)",
               SEED_BOOKS)


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------

def find_book(cursor, book_id):
    """Return (id, title, authorID, qty) for a book, or None."""
    cursor.execute(
        "SELECT id, title, authorID, qty FROM book WHERE id = ?",
        (book_id,))
    return cursor.fetchone()


def find_author(cursor, author_id):
    """Return (id, name, country) for an author, or None."""
    cursor.execute(
        "SELECT id, name, country FROM author WHERE id = ?", (author_id,))
    return cursor.fetchone()


def find_duplicate_book(cursor, title, author_id):
    """Return the book with this title (ignoring case) by this author,
    as (id, title, authorID, qty), or None."""
    cursor.execute(
        "SELECT id, title, authorID, qty FROM book "
        "WHERE LOWER(title) = LOWER(?) AND authorID = ?",
        (title, author_id))
    return cursor.fetchone()


def print_book(book):
    """Display a single book record."""
    book_id, title, author_id, qty = book
    print(f"ID:        {book_id}")
    print(f"Title:     {title}")
    print(f"Author ID: {author_id}")
    print(f"Quantity:  {qty}")


def list_authors(cursor):
    """Print every author with their ID so the clerk can pick one."""
    cursor.execute("SELECT id, name, country FROM author ORDER BY name")
    print("\nAvailable authors:")
    print(f"{'ID':<6}{'Name':<25}Country")
    print("-" * 45)
    for author_id, name, country in cursor.fetchall():
        print(f"{author_id:<6}{name:<25}{country}")
    print()


# --------------------------------------------------------------------------
# Menu actions
# --------------------------------------------------------------------------

def add_book(cursor):
    """Add a new book. The book ID is generated by the database.

    The author ID is requested because it is a foreign key: the author
    must already exist in the author table.
    """
    list_authors(cursor)
    author_id, _ = prompt_for_id(
        "What is the author ID", lambda i: find_author(cursor, i))
    if author_id is None:
        print("Add cancelled.")
        return

    title = input("Enter the book title: ").strip()
    if not title:
        print("Title cannot be empty. Add cancelled.")
        return

    duplicate = find_duplicate_book(cursor, title, author_id)
    if duplicate is not None:
        add_stock_to_existing(cursor, duplicate)
        return

    qty = get_valid_qty("Enter the quantity of the book: ")

    cursor.execute(
        "INSERT INTO book (title, authorID, qty) VALUES (?, ?, ?)",
        (title, author_id, qty))
    print(f"Book added successfully with ID {cursor.lastrowid}.")


def add_stock_to_existing(cursor, book):
    """Warn that a book already exists and offer to add to its quantity
    instead of creating a duplicate record."""
    book_id, _, _, current_qty = book
    print("\nThis author already has a book with that title:")
    print_book(book)

    answer = input(
        "\nAdd to the existing quantity instead? (y/n): ").strip().lower()
    if answer != "y":
        print("Add cancelled - no duplicate created.")
        return

    extra = get_valid_qty("How many copies are you adding? ")
    cursor.execute("UPDATE book SET qty = qty + ? WHERE id = ?",
                   (extra, book_id))
    print(f"Quantity for book {book_id} is now {current_qty + extra}.")


def update_book(cursor):
    """Update a book's quantity (default), title or author, or edit the
    details of its author."""
    book_id, book = prompt_for_id(
        "Enter the book ID to update", lambda i: find_book(cursor, i))
    if book is None:
        print("Update cancelled.")
        return

    print("\nCurrent book details:")
    print_book(book)

    print("\n1. Quantity (default)")
    print("2. Title")
    print("3. Author ID (reassign book to a different author)")
    print("4. Author details (name/country)")
    choice = input("What would you like to update? (1/2/3/4): ").strip()

    if choice == "2":
        new_title = input("Enter the new title: ").strip()
        if not new_title:
            print("Title cannot be empty. Update cancelled.")
            return
        cursor.execute("UPDATE book SET title = ? WHERE id = ?",
                       (new_title, book_id))
        print("Title updated.")

    elif choice == "3":
        list_authors(cursor)
        new_author_id, _ = prompt_for_id(
            "Enter the new author ID", lambda i: find_author(cursor, i))
        if new_author_id is None:
            print("Update cancelled.")
            return
        cursor.execute("UPDATE book SET authorID = ? WHERE id = ?",
                       (new_author_id, book_id))
        print("Author ID updated.")

    elif choice == "4":
        update_author_details(cursor, book[2])

    else:
        new_qty = get_valid_qty("Enter the new quantity: ")
        cursor.execute("UPDATE book SET qty = ? WHERE id = ?",
                       (new_qty, book_id))
        print("Quantity updated.")


def update_author_details(cursor, author_id):
    """Show an author's current details and save any changes."""
    author = find_author(cursor, author_id)
    if author is None:
        print("No matching author found.")
        return

    _, name, country = author
    print("\nCurrent author details:")
    print(f"Name:    {name}")
    print(f"Country: {country}\n")

    new_name = input(f"Enter new name (blank to keep '{name}'): ").strip()
    new_country = input(
        f"Enter new country (blank to keep '{country}'): ").strip()

    cursor.execute(
        "UPDATE author SET name = ?, country = ? WHERE id = ?",
        (new_name or name, new_country or country, author_id))
    print("Author details updated.")


def delete_book(cursor):
    """Delete a book, but only after the user confirms."""
    book_id, book = prompt_for_id(
        "Enter the book ID to delete", lambda i: find_book(cursor, i))
    if book_id is None:
        print("Delete cancelled.")
        return

    print("\nBook to delete:")
    print_book(book)

    confirm = input(
        "\nAre you sure you want to delete this book? (y/n): ")
    if confirm.strip().lower() == "y":
        cursor.execute("DELETE FROM book WHERE id = ?", (book_id,))
        print(f"Book with ID {book_id} deleted.")
    else:
        print("Delete cancelled.")


def search_book(cursor):
    """Find a book by ID and display it."""
    book_id, book = prompt_for_id(
        "Enter the book ID to search for", lambda i: find_book(cursor, i))
    if book_id is None:
        print("Search cancelled.")
        return

    print()
    print_book(book)


def view_all_books(cursor):
    """Show every book with its author's name and country."""
    cursor.execute("""
        SELECT book.id, book.title, author.name, author.country
        FROM book
        INNER JOIN author ON book.authorID = author.id
        ORDER BY book.id
    """)
    rows = cursor.fetchall()

    print("\nDetails")
    print("-" * 50)
    if not rows:
        print("No books found.")
        return
    for book_id, title, name, country in rows:
        print(f"Book ID: {book_id}")
        print(f"Title: {title}")
        print(f"Author's Name: {name}")
        print(f"Author's Country: {country}")
        print("-" * 50)


# --------------------------------------------------------------------------
# Main program
# --------------------------------------------------------------------------

MENU = """
1. Enter book
2. Update book
3. Delete book
4. Search books
5. View details of all books
0. Exit"""

ACTIONS = {
    "1": add_book,
    "2": update_book,
    "3": delete_book,
    "4": search_book,
    "5": view_all_books,
}


def main():
    """Set up the database and run the menu loop."""
    with closing(connect_db()) as conn:
        with conn:  # commits on success, rolls back on error
            cursor = conn.cursor()
            create_tables(cursor)
            seed_data(cursor)

        while True:
            print(MENU)
            choice = input("Select an option: ").strip()

            if choice == "0":
                print("Goodbye!")
                break

            action = ACTIONS.get(choice)
            if action is None:
                print("Invalid option. Please try again.")
                continue

            try:
                # Each action is one transaction: committed if it
                # finishes, rolled back if a database error occurs.
                with conn:
                    action(conn.cursor())
            except sqlite3.Error as error:
                print(f"A database error occurred: {error}")


if __name__ == "__main__":
    main()
