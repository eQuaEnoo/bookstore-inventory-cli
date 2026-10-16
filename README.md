# Bookstore Inventory CLI (shelf_track)

A command-line inventory manager for a bookstore, built with Python and
SQLite. A clerk can add, update, delete and search books, and view every
book alongside its author's details.

## Features

- **Add books:** shows the list of authors with their IDs first, and warns
  if the author already has a book with that title (offering to add to its
  quantity instead of creating a duplicate)
- **Update books:** change a book's quantity (default), title or author,
  or edit the author's name and country
- **Delete books:** shows the book and asks for confirmation first
- **Search books:** look up a book by its ID
- **View all books:** every book with its author's name and country, using
  an SQL `INNER JOIN`
- **Safe by design:** parameterised queries (no SQL injection), input
  validation, foreign key enforcement, and one transaction per action
  (rolled back if a database error occurs)

## Requirements

Python 3.8+. No third-party packages: only the standard library.

## Run

```
python shelf_track.py
```

The `ebookstore.db` database is created and seeded with sample books and
authors on first run.

```
1. Enter book
2. Update book
3. Delete book
4. Search books
5. View details of all books
0. Exit
```

### Example: adding a book

```
Available authors:
ID    Name                     Country
---------------------------------------------
2356  C.S. Lewis               Ireland
1290  Charles Dickens          England
8937  J.K. Rowling             England
6380  J.R.R. Tolkien           South Africa
5620  Lewis Carroll            England

What is the author ID (4 digits, or 0 to cancel): 1290
Enter the book title: Oliver Twist
Enter the quantity of the book: 15
Book added successfully with ID 3006.
```

## Database schema

| Table  | Columns                                                 |
|--------|---------------------------------------------------------|
| author | `id` (PK), `name`, `country`                            |
| book   | `id` (PK), `title`, `authorID` (FK -> author.id), `qty` |

## Notes

Originally written as a HyperionDev capstone project, then refactored for
modularity, validation and error handling.
