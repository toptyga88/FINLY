import os
import sqlite3
from pathlib import Path
from datetime import datetime

DB_NAME = os.getenv("FINLY_DB_PATH", str(Path(__file__).with_name("finly.db")))


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():
    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # USERS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            telegram_name TEXT,
            display_name TEXT,
            onboarding_completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # BANKS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # ACCOUNTS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            bank_id INTEGER,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'RUB',
            is_main INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

            FOREIGN KEY (bank_id)
                REFERENCES banks(id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # INCOME SOURCES
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS income_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            account_id INTEGER,
            name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            frequency TEXT DEFAULT 'monthly',
            day_of_month INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

            FOREIGN KEY (account_id)
                REFERENCES accounts(id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # CATEGORIES
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📦',
            category_type TEXT DEFAULT 'expense',
            is_active INTEGER DEFAULT 1,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE
        )
    """)

    # =========================
    # TRANSACTIONS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            account_id INTEGER,
            category_id INTEGER,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

            FOREIGN KEY (account_id)
                REFERENCES accounts(id)
                ON DELETE SET NULL,

            FOREIGN KEY (category_id)
                REFERENCES categories(id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # EXPECTED INCOMES
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expected_incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            source_id INTEGER,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            expected_date TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
            FOREIGN KEY (source_id) REFERENCES income_sources(id) ON DELETE SET NULL
        )
    """)

    # =========================
    # RECURRING PAYMENTS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recurring_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            account_id INTEGER,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            day_of_month INTEGER,
            category TEXT,
            is_active INTEGER DEFAULT 1,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

            FOREIGN KEY (account_id)
                REFERENCES accounts(id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # LOANS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            bank_id INTEGER,
            name TEXT NOT NULL,
            loan_type TEXT DEFAULT 'loan',
            remaining_amount REAL DEFAULT 0,
            monthly_payment REAL DEFAULT 0,
            payment_day INTEGER,
            interest_rate REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

            FOREIGN KEY (bank_id)
                REFERENCES banks(id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # GOALS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            account_id INTEGER,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            target_date TEXT,
            is_active INTEGER DEFAULT 1,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

            FOREIGN KEY (account_id)
                REFERENCES accounts(id)
                ON DELETE SET NULL
        )
    """)

    # =========================
    # MONTHLY PLAN SETTINGS
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plan_settings (
            telegram_id INTEGER PRIMARY KEY,
            monthly_reserve REAL DEFAULT 0,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        )
    """)

    # TRANSFERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            from_account_id INTEGER NOT NULL,
            to_account_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
            FOREIGN KEY (from_account_id) REFERENCES accounts(id),
            FOREIGN KEY (to_account_id) REFERENCES accounts(id)
        )
    """)

    conn.commit()
    conn.close()


# =====================================================
# USERS
# =====================================================

def add_user(telegram_id, telegram_name):
    conn = get_connection()

    conn.execute("""
        INSERT OR IGNORE INTO users
        (telegram_id, telegram_name)
        VALUES (?, ?)
    """, (telegram_id, telegram_name))

    conn.commit()
    conn.close()


def get_user(telegram_id):
    conn = get_connection()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,)).fetchone()

    conn.close()
    return user


def set_display_name(telegram_id, name):
    conn = get_connection()

    conn.execute("""
        UPDATE users
        SET display_name = ?
        WHERE telegram_id = ?
    """, (name, telegram_id))

    conn.commit()
    conn.close()


# =====================================================
# BANKS
# =====================================================

def add_bank(telegram_id, name):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO banks
        (telegram_id, name)
        VALUES (?, ?)
    """, (telegram_id, name))

    bank_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return bank_id


def get_banks(telegram_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM banks
        WHERE telegram_id = ?
          AND is_active = 1
        ORDER BY name
    """, (telegram_id,)).fetchall()

    conn.close()
    return rows


def get_bank(bank_id, telegram_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM banks
        WHERE id = ?
          AND telegram_id = ?
          AND is_active = 1
    """, (bank_id, telegram_id)).fetchone()

    conn.close()
    return row


def rename_bank(bank_id, telegram_id, name):
    conn = get_connection()

    conn.execute("""
        UPDATE banks
        SET name = ?
        WHERE id = ?
          AND telegram_id = ?
    """, (name, bank_id, telegram_id))

    conn.commit()
    conn.close()


def delete_bank(bank_id, telegram_id):
    conn = get_connection()

    conn.execute("""
        UPDATE banks
        SET is_active = 0
        WHERE id = ?
          AND telegram_id = ?
    """, (bank_id, telegram_id))

    conn.commit()
    conn.close()


# =====================================================
# ACCOUNTS
# =====================================================

def add_account(
    telegram_id,
    name,
    account_type,
    balance,
    bank_id=None,
    is_main=0
):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO accounts
        (
            telegram_id,
            bank_id,
            name,
            account_type,
            balance,
            is_main
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        bank_id,
        name,
        account_type,
        balance,
        is_main
    ))

    account_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return account_id


def get_accounts(telegram_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            accounts.*,
            banks.name AS bank_name
        FROM accounts
        LEFT JOIN banks
            ON accounts.bank_id = banks.id
        WHERE accounts.telegram_id = ?
          AND accounts.is_active = 1
        ORDER BY
            accounts.is_main DESC,
            banks.name,
            accounts.name
    """, (telegram_id,)).fetchall()

    conn.close()
    return rows


def get_account(account_id, telegram_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT
            accounts.*,
            banks.name AS bank_name
        FROM accounts
        LEFT JOIN banks
            ON accounts.bank_id = banks.id
        WHERE accounts.id = ?
          AND accounts.telegram_id = ?
          AND accounts.is_active = 1
    """, (account_id, telegram_id)).fetchone()

    conn.close()
    return row


def update_account_balance(account_id, telegram_id, balance):
    conn = get_connection()

    conn.execute("""
        UPDATE accounts
        SET balance = ?
        WHERE id = ?
          AND telegram_id = ?
    """, (
        balance,
        account_id,
        telegram_id
    ))

    conn.commit()
    conn.close()


def rename_account(account_id, telegram_id, name):
    conn = get_connection()

    conn.execute("""
        UPDATE accounts
        SET name = ?
        WHERE id = ?
          AND telegram_id = ?
    """, (name, account_id, telegram_id))

    conn.commit()
    conn.close()


def delete_account(account_id, telegram_id):
    conn = get_connection()

    conn.execute("""
        UPDATE accounts
        SET is_active = 0
        WHERE id = ?
          AND telegram_id = ?
    """, (account_id, telegram_id))

    conn.commit()
    conn.close()


# =====================================================
# INCOME SOURCES
# =====================================================

def add_income_source(
    telegram_id,
    name,
    amount,
    frequency,
    day_of_month=None,
    account_id=None
):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO income_sources
        (
            telegram_id,
            account_id,
            name,
            amount,
            frequency,
            day_of_month
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        account_id,
        name,
        amount,
        frequency,
        day_of_month
    ))

    source_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return source_id


def get_income_sources(telegram_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            income_sources.*,
            accounts.name AS account_name
        FROM income_sources
        LEFT JOIN accounts
            ON income_sources.account_id = accounts.id
        WHERE income_sources.telegram_id = ?
          AND income_sources.is_active = 1
        ORDER BY income_sources.id
    """, (telegram_id,)).fetchall()

    conn.close()
    return rows


def get_income_source(source_id, telegram_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM income_sources
        WHERE id = ?
          AND telegram_id = ?
          AND is_active = 1
    """, (source_id, telegram_id)).fetchone()

    conn.close()
    return row


def delete_income_source(source_id, telegram_id):
    conn = get_connection()

    conn.execute("""
        UPDATE income_sources
        SET is_active = 0
        WHERE id = ?
          AND telegram_id = ?
    """, (source_id, telegram_id))

    conn.commit()
    conn.close()


def update_income_source_amount(source_id, telegram_id, amount):
    conn = get_connection()

    conn.execute("""
        UPDATE income_sources
        SET amount = ?
        WHERE id = ?
          AND telegram_id = ?
    """, (
        amount,
        source_id,
        telegram_id
    ))

    conn.commit()
    conn.close()


# =====================================================
# TRANSACTIONS
# =====================================================

def add_transaction(
    telegram_id,
    account_id,
    transaction_type,
    amount,
    description=None,
    category_id=None
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO transactions
        (
            telegram_id,
            account_id,
            category_id,
            transaction_type,
            amount,
            description
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        telegram_id,
        account_id,
        category_id,
        transaction_type,
        amount,
        description
    ))

    if account_id:

        account = conn.execute("""
            SELECT balance
            FROM accounts
            WHERE id = ?
              AND telegram_id = ?
        """, (
            account_id,
            telegram_id
        )).fetchone()

        if account:

            current = account["balance"]

            if transaction_type == "income":
                new_balance = current + amount
            elif transaction_type == "expense":
                new_balance = current - amount
            else:
                new_balance = current

            conn.execute("""
                UPDATE accounts
                SET balance = ?
                WHERE id = ?
                  AND telegram_id = ?
            """, (
                new_balance,
                account_id,
                telegram_id
            ))

    conn.commit()
    conn.close()


# =====================================================
# CATEGORIES + SAFE TRANSACTIONS (FINLY V2)
# =====================================================

DEFAULT_EXPENSE_CATEGORIES = [
    ("Продукты", "🛒"),
    ("Кафе", "🍔"),
    ("Транспорт", "🚕"),
    ("Покупки", "🛍"),
    ("Дом", "🏠"),
    ("Здоровье", "💊"),
    ("Развлечения", "🎮"),
    ("Подписки", "📱"),
    ("Подарки", "🎁"),
    ("Другое", "📦"),
]


def add_default_categories(telegram_id):
    conn = get_connection()
    existing = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM categories
        WHERE telegram_id = ?
          AND category_type = 'expense'
          AND is_active = 1
    """, (telegram_id,)).fetchone()["cnt"]

    if existing == 0:
        conn.executemany("""
            INSERT INTO categories (telegram_id, name, icon, category_type)
            VALUES (?, ?, ?, 'expense')
        """, [(telegram_id, name, icon) for name, icon in DEFAULT_EXPENSE_CATEGORIES])
        conn.commit()
    conn.close()


def get_categories(telegram_id, category_type="expense"):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM categories
        WHERE telegram_id = ?
          AND category_type = ?
          AND is_active = 1
        ORDER BY id
    """, (telegram_id, category_type)).fetchall()
    conn.close()
    return rows


def add_transaction(telegram_id, account_id, transaction_type, amount,
                    description=None, category_id=None):
    conn = get_connection()
    try:
        account = conn.execute("""
            SELECT id, balance FROM accounts
            WHERE id = ? AND telegram_id = ? AND is_active = 1
        """, (account_id, telegram_id)).fetchone() if account_id else None

        if account_id and not account:
            raise ValueError("Счёт не принадлежит пользователю или удалён")

        if category_id:
            category = conn.execute("""
                SELECT id FROM categories
                WHERE id = ? AND telegram_id = ? AND is_active = 1
            """, (category_id, telegram_id)).fetchone()
            if not category:
                raise ValueError("Категория не принадлежит пользователю")

        cur = conn.execute("""
            INSERT INTO transactions
            (telegram_id, account_id, category_id, transaction_type, amount, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (telegram_id, account_id, category_id, transaction_type, amount, description))
        tx_id = cur.lastrowid

        if account:
            delta = amount if transaction_type == "income" else -amount if transaction_type == "expense" else 0
            conn.execute("""
                UPDATE accounts SET balance = balance + ?
                WHERE id = ? AND telegram_id = ?
            """, (delta, account_id, telegram_id))

        conn.commit()
        return tx_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_transactions(telegram_id, limit=30):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, a.name AS account_name, c.name AS category_name, c.icon AS category_icon
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.telegram_id = ?
        ORDER BY t.id DESC
        LIMIT ?
    """, (telegram_id, limit)).fetchall()
    conn.close()
    return rows


def get_transaction(transaction_id, telegram_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT t.*, a.name AS account_name, c.name AS category_name, c.icon AS category_icon
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.id = ? AND t.telegram_id = ?
    """, (transaction_id, telegram_id)).fetchone()
    conn.close()
    return row


def delete_transaction(transaction_id, telegram_id):
    conn = get_connection()
    try:
        tx = conn.execute("""
            SELECT * FROM transactions
            WHERE id = ? AND telegram_id = ?
        """, (transaction_id, telegram_id)).fetchone()
        if not tx:
            return False

        if tx["account_id"]:
            if tx["transaction_type"] == "expense":
                delta = tx["amount"]
            elif tx["transaction_type"] == "income":
                delta = -tx["amount"]
            else:
                delta = 0
            conn.execute("""
                UPDATE accounts SET balance = balance + ?
                WHERE id = ? AND telegram_id = ?
            """, (delta, tx["account_id"], telegram_id))

        conn.execute("""
            DELETE FROM transactions
            WHERE id = ? AND telegram_id = ?
        """, (transaction_id, telegram_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# =====================================================
# EXPENSE ANALYTICS / EDITING
# =====================================================

def get_expenses_for_month(telegram_id, year, month):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, a.name AS account_name, c.name AS category_name, c.icon AS category_icon
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.telegram_id = ? AND t.transaction_type = 'expense'
          AND strftime('%Y', t.created_at) = ? AND strftime('%m', t.created_at) = ?
        ORDER BY t.created_at DESC, t.id DESC
    """, (telegram_id, str(year), f"{month:02d}")).fetchall()
    conn.close()
    return rows


def get_expenses_for_day(telegram_id, date_iso):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.*, a.name AS account_name, c.name AS category_name, c.icon AS category_icon
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.telegram_id = ? AND t.transaction_type = 'expense'
          AND date(t.created_at) = ?
        ORDER BY t.created_at DESC, t.id DESC
    """, (telegram_id, date_iso)).fetchall()
    conn.close()
    return rows


def update_expense(transaction_id, telegram_id, amount=None, account_id=None,
                   category_id=None, description=None, update_description=False):
    conn = get_connection()
    try:
        tx = conn.execute("""
            SELECT * FROM transactions
            WHERE id = ? AND telegram_id = ? AND transaction_type = 'expense'
        """, (transaction_id, telegram_id)).fetchone()
        if not tx:
            return False

        new_amount = float(amount) if amount is not None else float(tx["amount"])
        new_account_id = account_id if account_id is not None else tx["account_id"]
        new_category_id = category_id if category_id is not None else tx["category_id"]
        new_description = description if update_description else tx["description"]

        if new_account_id:
            acc = conn.execute("""
                SELECT id FROM accounts WHERE id = ? AND telegram_id = ? AND is_active = 1
            """, (new_account_id, telegram_id)).fetchone()
            if not acc:
                raise ValueError("Счёт не принадлежит пользователю")
        if new_category_id:
            cat = conn.execute("""
                SELECT id FROM categories WHERE id = ? AND telegram_id = ? AND is_active = 1
            """, (new_category_id, telegram_id)).fetchone()
            if not cat:
                raise ValueError("Категория не принадлежит пользователю")

        # Undo old expense, then apply the edited one.
        if tx["account_id"]:
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ? AND telegram_id = ?",
                         (tx["amount"], tx["account_id"], telegram_id))
        if new_account_id:
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ? AND telegram_id = ?",
                         (new_amount, new_account_id, telegram_id))

        conn.execute("""
            UPDATE transactions
            SET amount = ?, account_id = ?, category_id = ?, description = ?
            WHERE id = ? AND telegram_id = ?
        """, (new_amount, new_account_id, new_category_id, new_description, transaction_id, telegram_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# =====================================================
# INCOME HISTORY + TRANSFERS
# =====================================================

def get_incomes_for_month(telegram_id, year, month):
    conn=get_connection()
    rows=conn.execute("""
        SELECT t.*, a.name AS account_name FROM transactions t
        LEFT JOIN accounts a ON t.account_id=a.id
        WHERE t.telegram_id=? AND t.transaction_type='income'
        AND strftime('%Y',t.created_at)=? AND strftime('%m',t.created_at)=?
        ORDER BY t.created_at DESC,t.id DESC
    """,(telegram_id,str(year),f"{month:02d}")).fetchall()
    conn.close()
    return rows

def add_transfer(telegram_id,from_account_id,to_account_id,amount,description=None):
    if from_account_id==to_account_id or amount<=0:
        raise ValueError("Некорректный перевод")
    conn=get_connection()
    try:
        a=conn.execute("SELECT id FROM accounts WHERE id=? AND telegram_id=? AND is_active=1",
                       (from_account_id,telegram_id)).fetchone()
        b=conn.execute("SELECT id FROM accounts WHERE id=? AND telegram_id=? AND is_active=1",
                       (to_account_id,telegram_id)).fetchone()
        if not a or not b: raise ValueError("Счёт не найден")
        cur=conn.execute("""INSERT INTO transfers
            (telegram_id,from_account_id,to_account_id,amount,description)
            VALUES(?,?,?,?,?)""",(telegram_id,from_account_id,to_account_id,amount,description))
        conn.execute("UPDATE accounts SET balance=balance-? WHERE id=? AND telegram_id=?",
                     (amount,from_account_id,telegram_id))
        conn.execute("UPDATE accounts SET balance=balance+? WHERE id=? AND telegram_id=?",
                     (amount,to_account_id,telegram_id))
        conn.commit()
        return cur.lastrowid
    except:
        conn.rollback(); raise
    finally: conn.close()

def get_transfers(telegram_id,limit=30):
    conn=get_connection()
    rows=conn.execute("""
        SELECT tr.*,fa.name AS from_account_name,ta.name AS to_account_name
        FROM transfers tr
        JOIN accounts fa ON fa.id=tr.from_account_id
        JOIN accounts ta ON ta.id=tr.to_account_id
        WHERE tr.telegram_id=? ORDER BY tr.created_at DESC,tr.id DESC LIMIT ?
    """,(telegram_id,limit)).fetchall()
    conn.close()
    return rows


# =====================================================
# MONTHLY PLAN
# =====================================================
def get_plan_settings(telegram_id):
    conn=get_connection()
    row=conn.execute("SELECT * FROM plan_settings WHERE telegram_id=?",(telegram_id,)).fetchone()
    conn.close(); return row

def set_monthly_reserve(telegram_id, amount):
    conn=get_connection()
    conn.execute("""INSERT INTO plan_settings(telegram_id,monthly_reserve) VALUES(?,?)
                    ON CONFLICT(telegram_id) DO UPDATE SET monthly_reserve=excluded.monthly_reserve""",
                 (telegram_id,float(amount)))
    conn.commit(); conn.close()

def get_month_expense_total(telegram_id, year, month):
    conn=get_connection()
    row=conn.execute("""SELECT COALESCE(SUM(amount),0) total FROM transactions
        WHERE telegram_id=? AND transaction_type='expense'
        AND strftime('%Y',created_at)=? AND strftime('%m',created_at)=?""",
        (telegram_id,str(year),f"{month:02d}")).fetchone()
    conn.close(); return float(row['total'] or 0)

def get_month_income_total(telegram_id, year, month):
    conn=get_connection()
    row=conn.execute("""SELECT COALESCE(SUM(amount),0) total FROM transactions
        WHERE telegram_id=? AND transaction_type='income'
        AND strftime('%Y',created_at)=? AND strftime('%m',created_at)=?""",
        (telegram_id,str(year),f"{month:02d}")).fetchone()
    conn.close(); return float(row['total'] or 0)


# =====================================================
# RECURRING PAYMENTS CRUD
# =====================================================
def add_recurring_payment(telegram_id, name, amount, day_of_month, account_id=None, category=None):
    conn=get_connection()
    try:
        if account_id is not None:
            acc=conn.execute("SELECT id FROM accounts WHERE id=? AND telegram_id=? AND is_active=1",(account_id,telegram_id)).fetchone()
            if not acc: raise ValueError("Счёт не найден")
        cur=conn.execute("""INSERT INTO recurring_payments(telegram_id,account_id,name,amount,day_of_month,category,is_active)
                            VALUES(?,?,?,?,?,?,1)""",(telegram_id,account_id,name,float(amount),int(day_of_month),category))
        conn.commit(); return cur.lastrowid
    finally: conn.close()

def get_recurring_payments(telegram_id):
    conn=get_connection(); rows=conn.execute("""SELECT rp.*,a.name account_name FROM recurring_payments rp
        LEFT JOIN accounts a ON a.id=rp.account_id WHERE rp.telegram_id=? AND rp.is_active=1
        ORDER BY rp.day_of_month,rp.id""",(telegram_id,)).fetchall(); conn.close(); return rows

def delete_recurring_payment(payment_id, telegram_id):
    conn=get_connection(); cur=conn.execute("UPDATE recurring_payments SET is_active=0 WHERE id=? AND telegram_id=?",(payment_id,telegram_id)); conn.commit(); ok=cur.rowcount>0; conn.close(); return ok

# =====================================================
# LOANS CRUD
# =====================================================
def add_loan(telegram_id,name,remaining_amount,monthly_payment,payment_day,interest_rate=0,bank_id=None,loan_type='loan'):
    conn=get_connection()
    try:
        if bank_id is not None:
            bank=conn.execute("SELECT id FROM banks WHERE id=? AND telegram_id=? AND is_active=1",(bank_id,telegram_id)).fetchone()
            if not bank: raise ValueError("Банк не найден")
        cur=conn.execute("""INSERT INTO loans(telegram_id,bank_id,name,loan_type,remaining_amount,monthly_payment,payment_day,interest_rate,is_active)
            VALUES(?,?,?,?,?,?,?,?,1)""",(telegram_id,bank_id,name,loan_type,float(remaining_amount),float(monthly_payment),int(payment_day),float(interest_rate or 0)))
        conn.commit(); return cur.lastrowid
    finally: conn.close()

def get_loans(telegram_id):
    conn=get_connection(); rows=conn.execute("""SELECT l.*,b.name bank_name FROM loans l LEFT JOIN banks b ON b.id=l.bank_id
        WHERE l.telegram_id=? AND l.is_active=1 ORDER BY l.payment_day,l.id""",(telegram_id,)).fetchall(); conn.close(); return rows

def delete_loan(loan_id,telegram_id):
    conn=get_connection(); cur=conn.execute("UPDATE loans SET is_active=0 WHERE id=? AND telegram_id=?",(loan_id,telegram_id)); conn.commit(); ok=cur.rowcount>0; conn.close(); return ok

# =====================================================
# GOALS CRUD
# =====================================================
def add_goal(telegram_id,name,target_amount,current_amount=0,target_date=None,account_id=None):
    conn=get_connection()
    try:
        if account_id is not None:
            acc=conn.execute("SELECT id FROM accounts WHERE id=? AND telegram_id=? AND is_active=1",(account_id,telegram_id)).fetchone()
            if not acc: raise ValueError("Счёт не найден")
        cur=conn.execute("""INSERT INTO goals(telegram_id,account_id,name,target_amount,current_amount,target_date,is_active)
            VALUES(?,?,?,?,?,?,1)""",(telegram_id,account_id,name,float(target_amount),float(current_amount or 0),target_date))
        conn.commit(); return cur.lastrowid
    finally: conn.close()

def get_goals(telegram_id):
    conn=get_connection()
    rows=conn.execute("""
        SELECT g.*, a.name account_name, a.account_type account_type,
               CASE WHEN a.id IS NOT NULL THEN a.balance ELSE g.current_amount END AS saved_amount
        FROM goals g
        LEFT JOIN accounts a ON a.id=g.account_id AND a.telegram_id=g.telegram_id AND a.is_active=1
        WHERE g.telegram_id=? AND g.is_active=1
        ORDER BY g.target_date IS NULL,g.target_date,g.id
    """,(telegram_id,)).fetchall()
    conn.close()
    return rows
def delete_goal(goal_id,telegram_id):
    conn=get_connection(); cur=conn.execute("UPDATE goals SET is_active=0 WHERE id=? AND telegram_id=?",(goal_id,telegram_id)); conn.commit(); ok=cur.rowcount>0; conn.close(); return ok


def get_savings_accounts(telegram_id):
    conn=get_connection()
    rows=conn.execute("""
        SELECT a.*, b.name AS bank_name
        FROM accounts a
        LEFT JOIN banks b ON b.id=a.bank_id
        WHERE a.telegram_id=? AND a.is_active=1 AND a.account_type IN ('savings','deposit')
        ORDER BY a.account_type='savings' DESC, a.id
    """,(telegram_id,)).fetchall()
    conn.close()
    return rows

def link_goal_to_account(goal_id, telegram_id, account_id):
    conn=get_connection()
    try:
        acc=conn.execute("""
            SELECT id FROM accounts
            WHERE id=? AND telegram_id=? AND is_active=1 AND account_type IN ('savings','deposit')
        """,(account_id,telegram_id)).fetchone()
        if not acc:
            return False
        cur=conn.execute("""
            UPDATE goals SET account_id=?
            WHERE id=? AND telegram_id=? AND is_active=1
        """,(account_id,goal_id,telegram_id))
        conn.commit()
        return cur.rowcount>0
    finally:
        conn.close()

def get_month_incoming_transfers_to_account(telegram_id, account_id, year, month):
    conn=get_connection()
    value=conn.execute("""
        SELECT COALESCE(SUM(amount),0) AS total FROM transfers
        WHERE telegram_id=? AND to_account_id=?
        AND strftime('%Y',created_at)=? AND strftime('%m',created_at)=?
    """,(telegram_id,account_id,str(year),f"{month:02d}")).fetchone()["total"]
    conn.close()
    return float(value or 0)

def add_expected_income(telegram_id,name,amount,expected_date,source_id=None):
    conn=get_connection()
    try:
        cur=conn.execute("""INSERT INTO expected_incomes(telegram_id,source_id,name,amount,expected_date,is_active)
                            VALUES(?,?,?,?,?,1)""",(telegram_id,source_id,name,float(amount),expected_date))
        conn.commit(); return cur.lastrowid
    finally: conn.close()

def get_expected_incomes(telegram_id,start_date=None,end_date=None):
    conn=get_connection(); sql="SELECT * FROM expected_incomes WHERE telegram_id=? AND is_active=1"; args=[telegram_id]
    if start_date: sql+=" AND expected_date>=?"; args.append(start_date)
    if end_date: sql+=" AND expected_date<=?"; args.append(end_date)
    rows=conn.execute(sql+" ORDER BY expected_date,id",args).fetchall(); conn.close(); return rows

def delete_expected_income(event_id,telegram_id):
    conn=get_connection(); cur=conn.execute("UPDATE expected_incomes SET is_active=0 WHERE id=? AND telegram_id=?",(event_id,telegram_id))
    conn.commit(); ok=cur.rowcount>0; conn.close(); return ok

def update_account_details(account_id, telegram_id, name=None, account_type=None, bank_id_marker="__KEEP__"):
    conn=get_connection()
    try:
        row=conn.execute("SELECT * FROM accounts WHERE id=? AND telegram_id=? AND is_active=1",(account_id,telegram_id)).fetchone()
        if not row: return False
        new_name=row["name"] if name is None else name
        new_type=row["account_type"] if account_type is None else account_type
        new_bank=row["bank_id"] if bank_id_marker=="__KEEP__" else bank_id_marker
        if new_type=="cash": new_bank=None
        cur=conn.execute("UPDATE accounts SET name=?,account_type=?,bank_id=? WHERE id=? AND telegram_id=?",
                         (new_name,new_type,new_bank,account_id,telegram_id))
        conn.commit(); return cur.rowcount>0
    finally: conn.close()

def update_income_source_details(source_id, telegram_id, name=None, amount=None, frequency=None, day_marker="__KEEP__", account_marker="__KEEP__"):
    conn=get_connection()
    try:
        row=conn.execute("SELECT * FROM income_sources WHERE id=? AND telegram_id=? AND is_active=1",(source_id,telegram_id)).fetchone()
        if not row: return False
        new_name=row["name"] if name is None else name
        new_amount=row["amount"] if amount is None else float(amount)
        new_freq=row["frequency"] if frequency is None else frequency
        new_day=row["day_of_month"] if day_marker=="__KEEP__" else day_marker
        new_account=row["account_id"] if account_marker=="__KEEP__" else account_marker
        if new_freq!="monthly": new_day=None
        cur=conn.execute("""UPDATE income_sources SET name=?,amount=?,frequency=?,day_of_month=?,account_id=?
                            WHERE id=? AND telegram_id=?""",
                         (new_name,new_amount,new_freq,new_day,new_account,source_id,telegram_id))
        conn.commit(); return cur.rowcount>0
    finally: conn.close()

def update_recurring_payment(payment_id,telegram_id,name=None,amount=None,day=None):
    conn=get_connection()
    try:
        r=conn.execute("SELECT * FROM recurring_payments WHERE id=? AND telegram_id=? AND is_active=1",(payment_id,telegram_id)).fetchone()
        if not r:return False
        conn.execute("UPDATE recurring_payments SET name=?,amount=?,day_of_month=? WHERE id=? AND telegram_id=?",
                     (r["name"] if name is None else name,r["amount"] if amount is None else float(amount),r["day_of_month"] if day is None else int(day),payment_id,telegram_id))
        conn.commit(); return True
    finally: conn.close()

def update_loan_details(loan_id,telegram_id,name=None,remaining=None,monthly=None,day=None,rate=None):
    conn=get_connection()
    try:
        r=conn.execute("SELECT * FROM loans WHERE id=? AND telegram_id=? AND is_active=1",(loan_id,telegram_id)).fetchone()
        if not r:return False
        conn.execute("""UPDATE loans SET name=?,remaining_amount=?,monthly_payment=?,payment_day=?,interest_rate=?
                        WHERE id=? AND telegram_id=?""",
                     (r["name"] if name is None else name,r["remaining_amount"] if remaining is None else float(remaining),
                      r["monthly_payment"] if monthly is None else float(monthly),r["payment_day"] if day is None else int(day),
                      r["interest_rate"] if rate is None else float(rate),loan_id,telegram_id))
        conn.commit(); return True
    finally: conn.close()

def update_goal_details(goal_id,telegram_id,name=None,target=None,target_date_marker="__KEEP__",account_marker="__KEEP__"):
    conn=get_connection()
    try:
        r=conn.execute("SELECT * FROM goals WHERE id=? AND telegram_id=? AND is_active=1",(goal_id,telegram_id)).fetchone()
        if not r:return False
        td=r["target_date"] if target_date_marker=="__KEEP__" else target_date_marker
        aid=r["account_id"] if account_marker=="__KEEP__" else account_marker
        if aid is not None:
            a=conn.execute("SELECT id FROM accounts WHERE id=? AND telegram_id=? AND is_active=1 AND account_type IN ('savings','deposit')",(aid,telegram_id)).fetchone()
            if not a:return False
        conn.execute("UPDATE goals SET name=?,target_amount=?,target_date=?,account_id=? WHERE id=? AND telegram_id=?",
                     (r["name"] if name is None else name,r["target_amount"] if target is None else float(target),td,aid,goal_id,telegram_id))
        conn.commit(); return True
    finally: conn.close()

def update_expected_income(event_id,telegram_id,name=None,amount=None,expected_date=None):
    conn=get_connection()
    try:
        r=conn.execute("SELECT * FROM expected_incomes WHERE id=? AND telegram_id=? AND is_active=1",(event_id,telegram_id)).fetchone()
        if not r:return False
        conn.execute("UPDATE expected_incomes SET name=?,amount=?,expected_date=? WHERE id=? AND telegram_id=?",
                     (r["name"] if name is None else name,r["amount"] if amount is None else float(amount),
                      r["expected_date"] if expected_date is None else expected_date,event_id,telegram_id))
        conn.commit(); return True
    finally: conn.close()

def get_expense_insights_data(telegram_id, start_date, end_date):
    """Фактические расходы за диапазон дат с категориями."""
    conn=get_connection()
    rows=conn.execute("""
        SELECT t.id,t.amount,t.description,t.created_at,
               COALESCE(c.name,'Без категории') AS category_name
        FROM transactions t
        LEFT JOIN categories c ON c.id=t.category_id
        WHERE t.telegram_id=? AND t.transaction_type='expense'
          AND date(t.created_at)>=date(?) AND date(t.created_at)<=date(?)
        ORDER BY t.created_at
    """,(telegram_id,start_date,end_date)).fetchall()
    conn.close()
    return rows

def get_monthly_expense_stats(uid, start_date, end_date):
    conn=get_connection()
    rows=conn.execute("""SELECT date(created_at) day, SUM(amount) total, COUNT(*) n
        FROM transactions WHERE telegram_id=? AND transaction_type='expense'
        AND date(created_at) BETWEEN ? AND ? GROUP BY date(created_at) ORDER BY day""",
        (uid,start_date,end_date)).fetchall()
    conn.close()
    return rows


# =====================================================
# FINLY — SAFE TRANSACTION EDITING
# =====================================================

def update_transaction(
    transaction_id,
    telegram_id,
    amount,
    account_id,
    category_id,
    description,
    created_at
):
    import math
    from datetime import datetime

    amount = float(amount)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    if not isinstance(created_at, str):
        raise ValueError("Некорректная дата")

    try:
        parsed_date = datetime.strptime(created_at, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД")

    if parsed_date.strftime("%Y-%m-%d") != created_at:
        raise ValueError("Некорректная дата")

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        tx = conn.execute("""
            SELECT * FROM transactions
            WHERE id = ? AND telegram_id = ?
        """, (transaction_id, telegram_id)).fetchone()

        if not tx:
            raise ValueError("Операция не найдена")

        kind = tx["transaction_type"]
        if kind not in ("income", "expense"):
            raise ValueError("Этот тип операции нельзя редактировать")

        if account_id is not None:
            account = conn.execute("""
                SELECT id FROM accounts
                WHERE id = ? AND telegram_id = ? AND is_active = 1
            """, (account_id, telegram_id)).fetchone()

            if not account:
                raise ValueError("Счёт не найден или недоступен")

        if category_id is not None:
            category = conn.execute("""
                SELECT id FROM categories
                WHERE id = ? AND telegram_id = ? AND is_active = 1
            """, (category_id, telegram_id)).fetchone()

            if not category:
                raise ValueError("Категория не найдена или недоступна")

        old_account = tx["account_id"]
        old_amount = float(tx["amount"])

        sign = 1 if kind == "income" else -1

        deltas = {}

        if old_account is not None:
            deltas[old_account] = deltas.get(old_account, 0) - sign * old_amount

        if account_id is not None:
            deltas[account_id] = deltas.get(account_id, 0) + sign * amount

        for acc_id, delta in deltas.items():
            row = conn.execute("""
                SELECT balance FROM accounts
                WHERE id = ? AND telegram_id = ?
            """, (acc_id, telegram_id)).fetchone()

            if not row:
                raise ValueError("Связанный счёт не найден")

            new_balance = float(row["balance"]) + delta

            if new_balance < -0.000001:
                raise ValueError(
                    "После изменения баланс счёта станет отрицательным"
                )

            conn.execute("""
                UPDATE accounts
                SET balance = ?
                WHERE id = ? AND telegram_id = ?
            """, (round(new_balance, 2), acc_id, telegram_id))

        conn.execute("""
            UPDATE transactions
            SET amount = ?,
                account_id = ?,
                category_id = ?,
                description = ?,
                created_at = ?
            WHERE id = ? AND telegram_id = ?
        """, (
            amount,
            account_id,
            category_id,
            description,
            (
                tx["created_at"]
                if str(tx["created_at"] or "")[:10] == created_at
                else created_at + " " + (
                    str(tx["created_at"] or "")[11:19]
                    if len(str(tx["created_at"] or "")) >= 19
                    else "12:00:00"
                )
            ),
            transaction_id,
            telegram_id
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
