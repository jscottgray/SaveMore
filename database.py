import sqlite3
import os

conn = None
c = None


def connect():
    # Check if DB is already created, if not create and fill with departments
    global conn, c
    db_exists = os.path.isfile('SaveMore.db')
    conn = sqlite3.connect('SaveMore.db')
    c = conn.cursor()

    if not db_exists:
        c.execute('''CREATE TABLE departments
                (Name text PRIMARY KEY, Category int NOT NULL, url text NOT NULL)
                WITHOUT ROWID''')
        c.execute("INSERT INTO departments VALUES ('produce', '588', 'produce')")
        c.execute(
            "INSERT INTO departments VALUES ('meat alternatives', '30219', 'meat%20alternatives')")
        c.execute(
            "INSERT INTO departments VALUES ('meat and seafood', 585, 'meat%20%26%20seafood')")
        c.execute(
            "INSERT INTO departments VALUES ('bulk foods', '1195', 'bulk%20foods')")
        c.execute("INSERT INTO departments VALUES ('deli', '1195', 'deli')")
        c.execute("INSERT INTO departments VALUES ('dairy', '579', 'dairy')")
        c.execute(
            "INSERT INTO departments VALUES ('soup and canned goods', '576', 'soup%20%26%20canned%20goods')")
        c.execute(
            "INSERT INTO departments VALUES ('world cuisine', '583', 'world%20cuisine')")
        c.execute(
            "INSERT INTO departments VALUES ('condiments and sauces', '578', 'condiments%20%26%20sauces')")
        c.execute("INSERT INTO departments VALUES ('snacks', '589', 'snacks')")
        c.execute(
            "INSERT INTO departments VALUES ('pasta, sauces, grains', '586', 'pasta%2C%20sauces%2C%20grains')")
        c.execute("INSERT INTO departments VALUES ('frozen', '581', 'frozen')")
        c.execute("INSERT INTO departments VALUES ('bakery', '573', 'bakery')")
        c.execute(
            "INSERT INTO departments VALUES ('baking and cooking needs', '582', 'baking%20%26%20cooking%20needs')")
        c.execute(
            "INSERT INTO departments VALUES ('breakfast and cereals', '575', 'breakfast%20%26%20cereals')")
        c.execute(
            "INSERT INTO departments VALUES ('health, beauty and wellness', '571', 'health%2C%20beauty%20%26%20wellness')")
        c.execute(
            "INSERT INTO departments VALUES ('baby and child care', '572', 'baby%20%26%20child%20care')")
        c.execute(
            "INSERT INTO departments VALUES ('cleaning, laundry and paper', '1001', 'cleaning%2C%20laundry%20%26%20paper')")
        c.execute(
            "INSERT INTO departments VALUES ('beer and wine making kits', '30000', 'beer%20%26%20wine%20making%20kits')")

        c.execute('''CREATE TABLE products (
                SKU int PRIMARY KEY,
                Name text,
                Description text, 
                Department text, 
                Category text, 
                Size text not null,
                FOREIGN KEY (Department)
                    REFERENCES departments
                    ON DELETE NO ACTION
                    ON UPDATE CASCADE
                ) WITHOUT ROWID''')

        c.execute('''CREATE TABLE prices (
            SKU int,
            Price real,
            Multibuy boolean,
            Saledesc string,
            Date string NOT NULL DEFAULT CURRENT_DATE,
            PRIMARY KEY (SKU, Date),
            FOREIGN KEY (SKU)
                REFERENCES products
                ON DELETE CASCADE
            ) WITHOUT ROWID''')

        conn.commit()


def close_db():
    global conn
    conn.close()


def save_price(SKU, price, multibuy=False, sales_desc=""):
    global conn, c
    c.execute(
        "INSERT INTO prices VALUES (?, ?, ?, ?, CURRENT_DATE)", (SKU, price, multibuy, sales_desc))
    conn.commit()


def new_product(SKU, Name, Description, Department, Category, Size):
    global conn, c
    print(f"tuple {(SKU, Name, Description, Department, Category, Size)}")
    c.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
              (SKU, Name, Description, Department, Category, Size))
    conn.commit()


def get_SKU(Name, Size):
    global c
    c.execute('''SELECT sku
                FROM products
                WHERE Name == ?
                AND Size == ?''', (Name, Size))
    sku = c.fetchone()
    if sku:
        return sku[0]
    else:
        return None


def get_departments():
    global conn, c
    c.execute('''SELECT *
                FROM departments''')
    return c.fetchall()
