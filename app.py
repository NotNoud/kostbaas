from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date
import os

app = Flask(__name__)


def get_db_path():
    if os.path.isdir('/data'):
        return '/data/expenses.db'
    os.makedirs('data', exist_ok=True)
    return 'data/expenses.db'


DB_PATH = get_db_path()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            amount       REAL,
            percentage   REAL,
            day_of_month INTEGER DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS monthly_payments (
            expense_id  INTEGER,
            month       INTEGER,
            year        INTEGER,
            paid        INTEGER DEFAULT 0,
            overridden  INTEGER DEFAULT 0,
            PRIMARY KEY (expense_id, month, year),
            FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS monthly_income (
            month   INTEGER,
            year    INTEGER,
            amount  REAL DEFAULT 0,
            PRIMARY KEY (month, year)
        );
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    today = date.today()
    return render_template('index.html',
        default_month=today.month,
        default_year=today.year,
        today_day=today.day,
        today_month=today.month,
        today_year=today.year
    )


@app.route('/api/data')
def get_data():
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)

    conn = get_db()

    inc = conn.execute(
        'SELECT amount FROM monthly_income WHERE month=? AND year=?', (month, year)
    ).fetchone()
    income = inc['amount'] if inc else 0

    expenses_rows = conn.execute(
        'SELECT * FROM expenses ORDER BY day_of_month IS NULL, day_of_month, name'
    ).fetchall()

    payments = {p['expense_id']: p for p in conn.execute(
        'SELECT * FROM monthly_payments WHERE month=? AND year=?', (month, year)
    ).fetchall()}

    conn.close()

    is_current = (month == today.month and year == today.year)
    result = []

    for exp in expenses_rows:
        eid = exp['id']
        p = payments.get(eid)

        if exp['percentage'] is not None:
            amount = round((exp['percentage'] / 100) * income, 2)
        else:
            amount = exp['amount'] or 0

        day = exp['day_of_month']
        # day_of_month NULL = handmatige last, nooit auto-afvinken
        if day is not None:
            auto_paid = is_current and day <= today.day
        else:
            auto_paid = False

        if p and p['overridden']:
            paid = bool(p['paid'])
            auto = False
        else:
            paid = auto_paid
            auto = auto_paid

        result.append({
            'id': eid,
            'name': exp['name'],
            'amount': amount,
            'percentage': exp['percentage'],
            'day_of_month': exp['day_of_month'],
            'paid': paid,
            'auto': auto,
            'overridden': bool(p['overridden']) if p else False
        })

    total = round(sum(e['amount'] for e in result), 2)
    paid_sum = round(sum(e['amount'] for e in result if e['paid']), 2)
    remaining = round(total - paid_sum, 2)
    disposable = round(income - total, 2)

    return jsonify({
        'income': income,
        'expenses': result,
        'summary': {
            'total': total,
            'paid': paid_sum,
            'remaining': remaining,
            'disposable': disposable
        }
    })


@app.route('/api/income', methods=['POST'])
def update_income():
    d = request.json
    conn = get_db()
    conn.execute('''
        INSERT INTO monthly_income (month, year, amount) VALUES (?, ?, ?)
        ON CONFLICT(month, year) DO UPDATE SET amount=excluded.amount
    ''', (d['month'], d['year'], d['amount']))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/expenses', methods=['POST'])
def add_expense():
    d = request.json
    conn = get_db()
    day = int(d['day_of_month']) if d.get('day_of_month') is not None else None
    if d.get('is_percentage'):
        conn.execute(
            'INSERT INTO expenses (name, percentage, day_of_month) VALUES (?, ?, ?)',
            (d['name'], float(d['percentage']), day)
        )
    else:
        conn.execute(
            'INSERT INTO expenses (name, amount, day_of_month) VALUES (?, ?, ?)',
            (d['name'], float(d['amount']), day)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/expenses/<int:eid>', methods=['PUT'])
def update_expense(eid):
    d = request.json
    conn = get_db()
    day = int(d['day_of_month']) if d.get('day_of_month') is not None else None
    if d.get('is_percentage'):
        conn.execute(
            'UPDATE expenses SET name=?, amount=NULL, percentage=?, day_of_month=? WHERE id=?',
            (d['name'], float(d['percentage']), day, eid)
        )
    else:
        conn.execute(
            'UPDATE expenses SET name=?, amount=?, percentage=NULL, day_of_month=? WHERE id=?',
            (d['name'], float(d['amount']), day, eid)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
def delete_expense(eid):
    conn = get_db()
    conn.execute('DELETE FROM monthly_payments WHERE expense_id=?', (eid,))
    conn.execute('DELETE FROM expenses WHERE id=?', (eid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/expenses/<int:eid>/toggle', methods=['POST'])
def toggle_payment(eid):
    d = request.json
    month, year = d['month'], d['year']
    today = date.today()

    conn = get_db()
    p = conn.execute(
        'SELECT paid, overridden FROM monthly_payments WHERE expense_id=? AND month=? AND year=?',
        (eid, month, year)
    ).fetchone()

    exp = conn.execute('SELECT day_of_month FROM expenses WHERE id=?', (eid,)).fetchone()
    day = exp['day_of_month']
    is_current = (month == today.month and year == today.year)
    auto_paid = day is not None and is_current and day <= today.day

    if p is None:
        new_paid = not auto_paid
        new_overridden = 0 if (new_paid == auto_paid) else 1
        conn.execute('''
            INSERT INTO monthly_payments (expense_id, month, year, paid, overridden)
            VALUES (?, ?, ?, ?, ?)
        ''', (eid, month, year, 1 if new_paid else 0, new_overridden))
    else:
        if p['overridden']:
            new_paid = not bool(p['paid'])
        else:
            new_paid = not auto_paid
        # Als de nieuwe staat overeenkomt met auto, reset overridden
        new_overridden = 0 if (new_paid == auto_paid) else 1
        conn.execute('''
            UPDATE monthly_payments SET paid=?, overridden=?
            WHERE expense_id=? AND month=? AND year=?
        ''', (1 if new_paid else 0, new_overridden, eid, month, year))

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'paid': new_paid})


if __name__ == '__main__':
    init_db()
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug)
