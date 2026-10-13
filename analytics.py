from fastapi import HTTPException
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from calendar import monthrange

from fastapi import APIRouter, Header, HTTPException, Query
from database import get_connection

router = APIRouter()


def _date_range(period, start, end):
    today = date.today()

    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    if period == "90d":
        return today - timedelta(days=89), today
    if period == "year":
        return date(today.year, 1, 1), today
    if period == "all":
        return date(2000, 1, 1), today
    if period == "custom":
        if not start or not end:
            raise HTTPException(400, "Укажи начало и конец периода")
        try:
            a = date.fromisoformat(start)
            b = date.fromisoformat(end)
        except ValueError:
            raise HTTPException(400, "Неверный формат даты")
        if a > b:
            raise HTTPException(400, "Начало периода позже конца")
        return a, b

    return date(today.year, today.month, 1), today


def build_analytics(uid, period, start, end, account_id, category_id):
    start_date, end_date = _date_range(period, start, end)

    conn = get_connection()
    try:
        filters = [
            "t.telegram_id = ?",
            "date(t.created_at) BETWEEN ? AND ?",
            "t.transaction_type IN ('income', 'expense')",
        ]
        params = [uid, start_date.isoformat(), end_date.isoformat()]

        if account_id is not None:
            filters.append("t.account_id = ?")
            params.append(account_id)

        if category_id is not None:
            filters.append("t.category_id = ?")
            params.append(category_id)

        sql = """
            SELECT t.id, t.amount, t.transaction_type,
                   t.created_at, t.account_id, t.category_id,
                   COALESCE(c.name, 'Без категории') AS category_name,
                   COALESCE(a.name, 'Без счёта') AS account_name
            FROM transactions t
            LEFT JOIN categories c
                ON c.id = t.category_id AND c.telegram_id = t.telegram_id
            LEFT JOIN accounts a
                ON a.id = t.account_id AND a.telegram_id = t.telegram_id
            WHERE """ + " AND ".join(filters) + """
            ORDER BY t.created_at
        """

        rows = conn.execute(sql, params).fetchall()

        categories = defaultdict(float)
        accounts = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        daily = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        weekdays = defaultdict(float)
        calendar = defaultdict(float)

        income = expense = 0.0
        income_count = expense_count = 0
        biggest_expense = 0.0

        for row in rows:
            amount = float(row["amount"] or 0)
            kind = row["transaction_type"]
            day = str(row["created_at"])[:10]
            month = day[:7]

            if kind == "income":
                income += amount
                income_count += 1
            else:
                expense += amount
                expense_count += 1
                biggest_expense = max(biggest_expense, amount)
                categories[row["category_name"]] += amount
                calendar[day] += amount

                try:
                    weekday = date.fromisoformat(day).weekday()
                    weekdays[weekday] += amount
                except ValueError:
                    pass

            accounts[row["account_name"]][kind] += amount
            daily[day][kind] += amount
            monthly[month][kind] += amount

        def money(value):
            return round(value, 2)

        category_chart = [
            {"name": name, "amount": money(amount)}
            for name, amount in sorted(
                categories.items(), key=lambda item: -item[1]
            )
        ]

        account_chart = [
            {
                "name": name,
                "income": money(values["income"]),
                "expense": money(values["expense"]),
            }
            for name, values in accounts.items()
        ]

        daily_chart = [
            {
                "date": day,
                "income": money(values["income"]),
                "expense": money(values["expense"]),
            }
            for day, values in sorted(daily.items())
        ]

        monthly_chart = [
            {
                "month": month,
                "income": money(values["income"]),
                "expense": money(values["expense"]),
            }
            for month, values in sorted(monthly.items())
        ]

        calendar_chart = [
            {"date": day, "amount": money(amount)}
            for day, amount in sorted(calendar.items())
        ]

        weekday_chart = [
            {"day": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][i],
             "amount": money(weekdays[i])}
            for i in range(7)
        ]

        days = max(1, (end_date - start_date).days + 1)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "income": money(income),
                "expense": money(expense),
                "net": money(income - expense),
                "income_count": income_count,
                "expense_count": expense_count,
                "average_daily_expense": money(expense / days),
                "average_transaction": money(
                    expense / expense_count if expense_count else 0
                ),
                "biggest_expense": money(biggest_expense),
                "savings_rate_pct": round(
                    (income - expense) / income * 100, 1
                ) if income > 0 else None,
            },
            "categories": category_chart,
            "accounts": account_chart,
            "daily": daily_chart,
            "monthly": monthly_chart,
            "calendar": calendar_chart,
            "weekdays": weekday_chart,
        }
    finally:
        conn.close()


@router.get("/api/analytics")
def analytics(
    x_telegram_init_data: str = Header(default=""),
    period: str = Query(default="month"),
    start: str | None = None,
    end: str | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
):
    # Импорт внутри функции исключает циклический импорт.
    from api import telegram_user

    uid = telegram_user(x_telegram_init_data)

    return build_analytics(
        uid, period, start, end, account_id, category_id
    )

# =========================================================
# FINLY — детализация интерактивных графиков
# =========================================================

@router.get("/api/analytics/transactions")
def analytics_transactions(
    x_telegram_init_data: str = Header(default=""),
    period: str = Query(default="month"),
    start: str | None = None,
    end: str | None = None,
    category: str | None = None,
    day: str | None = None,
    month: str | None = None,
    account: str | None = None,
    kind: str = "expense",
):
    from api import telegram_user

    uid = telegram_user(x_telegram_init_data)
    start_date, end_date = _date_range(period, start, end)

    if kind not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="Invalid transaction type")

    filters = [
        "t.telegram_id = ?",
        "t.transaction_type = ?",
        "date(t.created_at) BETWEEN ? AND ?",
    ]
    params = [uid, kind, start_date.isoformat(), end_date.isoformat()]

    if category is not None:
        filters.append("COALESCE(c.name, 'Без категории') = ?")
        params.append(category)

    if day is not None:
        try:
            date.fromisoformat(day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date")
        filters.append("date(t.created_at) = ?")
        params.append(day)

    if month is not None:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise HTTPException(status_code=400, detail="Invalid month")
        filters.append("substr(t.created_at, 1, 7) = ?")
        params.append(month)

    if account is not None:
        filters.append("COALESCE(a.name, 'Без счёта') = ?")
        params.append(account)

    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                t.id,
                t.amount,
                t.transaction_type,
                t.created_at,
                COALESCE(c.name, 'Без категории') AS category_name,
                COALESCE(a.name, 'Без счёта') AS account_name
            FROM transactions t
            LEFT JOIN categories c
                ON c.id = t.category_id
                AND c.telegram_id = t.telegram_id
            LEFT JOIN accounts a
                ON a.id = t.account_id
                AND a.telegram_id = t.telegram_id
            WHERE """ + " AND ".join(filters) + """
            ORDER BY t.created_at DESC, t.id DESC
            LIMIT 200
        """, params).fetchall()

        return {
            "transactions": [
                {
                    "id": row["id"],
                    "amount": float(row["amount"] or 0),
                    "type": row["transaction_type"],
                    "date": row["created_at"],
                    "category": row["category_name"],
                    "account": row["account_name"],
                }
                for row in rows
            ],
            "limit": 200,
        }
    finally:
        conn.close()
