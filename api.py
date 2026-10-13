import asyncio
import json
import hmac
import hashlib
import time
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import BOT_TOKEN
from analytics import router as analytics_router
from database import (
    create_database,
    get_connection,
    get_user,
    get_accounts,
    get_account,
    get_banks,
    get_goals,
    get_recurring_payments,
    get_loans,
    get_transactions,
    get_categories,
    add_default_categories,
    add_transaction,
    delete_transaction,
    add_transfer,
    get_transfers,
    add_account,
    update_account_details,
    update_account_balance,
    delete_account,
    add_goal,
    update_goal_details,
    delete_goal,
)

from main import (
    bot,
    dp,
    get_cashflow_health,
    _goal_due_now,
    get_plan_settings,
)


ROOT = Path(__file__).parent
_bot_task = None


# =========================================================
# TELEGRAM AUTH
# =========================================================

def telegram_user(init_data: str):

    if not init_data:
        raise HTTPException(
            status_code=401,
            detail="Открой FINLY из Telegram"
        )

    data = dict(
        parse_qsl(
            init_data,
            keep_blank_values=True
        )
    )

    received_hash = data.pop(
        "hash",
        None
    )

    if not received_hash:
        raise HTTPException(
            status_code=401,
            detail="Некорректные данные Telegram"
        )

    try:
        auth_date = int(
            data.get(
                "auth_date",
                "0"
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Некорректная дата авторизации"
        )

    if (
        not auth_date
        or abs(
            time.time() - auth_date
        ) > 86400
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Сессия Telegram устарела. "
                "Переоткрой FINLY."
            )
        )

    check_string = "\n".join(
        f"{key}={value}"
        for key, value
        in sorted(data.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    expected_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected_hash,
        received_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Неверная подпись Telegram"
        )

    try:
        user_data = json.loads(
            data["user"]
        )

        return int(
            user_data["id"]
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Пользователь Telegram не найден"
        )


# =========================================================
# HELPERS
# =========================================================

def rows(items):
    return [
        dict(item)
        for item in items
    ]


def safe_float(
    value,
    name="Сумма"
):

    try:
        number = float(value)

    except (
        TypeError,
        ValueError
    ):
        raise HTTPException(
            status_code=400,
            detail=f"{name}: неверное значение"
        )

    if number < 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{name} не может быть "
                "отрицательной"
            )
        )

    return number


# =========================================================
# DASHBOARD
# =========================================================

def dashboard_data(uid: int):

    add_default_categories(uid)

    accounts = rows(
        get_accounts(uid)
    )

    total = sum(
        float(
            account.get("balance")
            or 0
        )
        for account in accounts
    )

    protected = sum(
        float(
            account.get("balance")
            or 0
        )
        for account in accounts
        if account.get(
            "account_type"
        ) in (
            "savings",
            "deposit",
            "investment"
        )
    )

    spendable = (
        total - protected
    )

    # -----------------------------------------
    # УМНЫЙ ЛИМИТ ИЗ TELEGRAM-БОТА
    # -----------------------------------------

    try:

        health = (
            get_cashflow_health(uid)
        )

        goal_due = float(
            _goal_due_now(
                uid,
                health
            )
            or 0
        )

        settings = (
            get_plan_settings(uid)
        )

        reserve = (
            float(
                settings[
                    "monthly_reserve"
                ]
                or 0
            )
            if settings
            else 0
        )

        free = max(
            0,
            float(
                health[
                    "safe_until_income"
                ]
            )
            - reserve
            - goal_due
        )

        horizon = (
            health["horizon"]
        )

        days = budget_days(health)

        if (
            health["mode"]
            == "deficit"
        ):
            today_limit = 0
        else:
            today_limit = (
                free / days
            )

        week_limit = (
            today_limit
            * min(
                7,
                days
            )
        )

        health_mode = (
            health["mode"]
        )

        obligations = float(
            health[
                "obligations"
            ]
            or 0
        )

    except Exception:

        today_limit = (
            0
        )

        week_limit = (
            0
        )

        health_mode = (
            "normal"
        )

        obligations = 0


    # -----------------------------------------
    # ОПЕРАЦИИ
    # -----------------------------------------

    transactions = rows(
        get_transactions(
            uid,
            80
        )
    )

    month_prefix = (
        date.today()
        .strftime(
            "%Y-%m"
        )
    )

    month_transactions = [
        item
        for item
        in transactions
        if str(
            item.get(
                "created_at",
                ""
            )
        ).startswith(
            month_prefix
        )
    ]

    month_expense = sum(
        float(
            item.get(
                "amount"
            )
            or 0
        )
        for item
        in month_transactions
        if item.get(
            "transaction_type"
        ) == "expense"
    )

    month_income = sum(
        float(
            item.get(
                "amount"
            )
            or 0
        )
        for item
        in month_transactions
        if item.get(
            "transaction_type"
        ) == "income"
    )


    # -----------------------------------------
    # КАТЕГОРИИ
    # -----------------------------------------

    category_totals = {}

    for item in month_transactions:

        if (
            item.get(
                "transaction_type"
            )
            != "expense"
        ):
            continue

        name = (
            item.get(
                "category_name"
            )
            or "Без категории"
        )

        category_totals[name] = (
            category_totals.get(
                name,
                0
            )
            + float(
                item.get(
                    "amount"
                )
                or 0
            )
        )

    top_categories = [
        {
            "name": name,
            "amount": amount
        }
        for name, amount
        in sorted(
            category_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:6]
    ]


    return {

        "user": (
            dict(
                get_user(uid)
            )
            if get_user(uid)
            else {}
        ),

        "total": total,

        "spendable": spendable,

        "protected": protected,

        "today_limit": (
            today_limit
        ),

        "week_limit": (
            week_limit
        ),

        "health_mode": (
            health_mode
        ),

        "obligations": (
            obligations
        ),

        "month_expense": (
            month_expense
        ),

        "month_income": (
            month_income
        ),

        "accounts": accounts,

        "banks": rows(
            get_banks(uid)
        ),

        "goals": rows(
            get_goals(uid)
        ),

        "payments": rows(
            get_recurring_payments(
                uid
            )
        ),

        "loans": rows(
            get_loans(uid)
        ),

        "categories": rows(
            get_categories(
                uid,
                "expense"
            )
        ),

        "transactions": (
            transactions[:30]
        ),

        "transfers": rows(
            get_transfers(
                uid,
                20
            )
        ),

        "top_categories": (
            top_categories
        ),
    }


# =========================================================
# REQUEST MODELS
# =========================================================

class TransactionInput(
    BaseModel
):

    account_id: int

    amount: float

    description: (
        str | None
    ) = None

    category_id: (
        int | None
    ) = None


class TransferInput(
    BaseModel
):

    from_account_id: int

    to_account_id: int

    amount: float

    description: (
        str | None
    ) = None


class AccountInput(
    BaseModel
):

    name: str

    account_type: str = "card"

    balance: float = 0

    bank_id: (
        int | None
    ) = None


class AccountEdit(
    BaseModel
):

    name: (
        str | None
    ) = None

    account_type: (
        str | None
    ) = None

    balance: (
        float | None
    ) = None

    bank_id: (
        int | None
    ) = None


class GoalInput(
    BaseModel
):

    name: str

    target_amount: float

    target_date: (
        str | None
    ) = None

    account_id: (
        int | None
    ) = None


class GoalEdit(
    BaseModel
):

    name: (
        str | None
    ) = None

    target_amount: (
        float | None
    ) = None

    target_date: (
        str | None
    ) = None

    account_id: (
        int | None
    ) = None


# =========================================================
# BOT
# =========================================================

async def run_bot():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(
        bot
    )


@asynccontextmanager
async def lifespan(app: FastAPI):

    global _bot_task

    create_database()

    _bot_task = (
        asyncio.create_task(
            run_bot()
        )
    )

    yield

    if _bot_task:

        _bot_task.cancel()

        try:
            await _bot_task

        except asyncio.CancelledError:
            pass

    await bot.session.close()


app = FastAPI(
    title="FINLY",
    lifespan=lifespan
)

app.include_router(analytics_router)


# =========================================================
# BASE
# =========================================================

@app.get("/")
def index():

    return FileResponse(
        ROOT / "index.html"
    )



@app.get("/analytics-ui.js")
def analytics_ui_script():
    return FileResponse(
        ROOT / "analytics-ui.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"}
    )

@app.get("/health")
def health():

    return {
        "status": "ok",
        "app": "FINLY"
    }


# =========================================================
# DASHBOARD API
# =========================================================

@app.get(
    "/api/dashboard"
)
def dashboard(
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    return dashboard_data(
        uid
    )


# =========================================================
# EXPENSE
# =========================================================

@app.post(
    "/api/expense"
)
def add_expense(
    body: TransactionInput,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    amount = safe_float(
        body.amount
    )

    if amount <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Сумма должна быть "
                "больше нуля"
            )
        )

    account = get_account(
        body.account_id,
        uid
    )

    if not account:

        raise HTTPException(
            status_code=404,
            detail="Счёт не найден"
        )

    if (
        float(
            account["balance"]
            or 0
        )
        < amount
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "На счёте "
                "недостаточно денег"
            )
        )

    try:

        transaction_id = (
            add_transaction(
                uid,
                body.account_id,
                "expense",
                amount,
                body.description,
                body.category_id
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "ok": True,
        "id": transaction_id,
        "dashboard": (
            dashboard_data(uid)
        )
    }


# =========================================================
# INCOME
# =========================================================

@app.post(
    "/api/income"
)
def add_income(
    body: TransactionInput,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    amount = safe_float(
        body.amount
    )

    if amount <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Сумма должна быть "
                "больше нуля"
            )
        )

    if not get_account(
        body.account_id,
        uid
    ):

        raise HTTPException(
            status_code=404,
            detail="Счёт не найден"
        )

    transaction_id = (
        add_transaction(
            uid,
            body.account_id,
            "income",
            amount,
            body.description,
            None
        )
    )

    return {
        "ok": True,
        "id": transaction_id,
        "dashboard": (
            dashboard_data(uid)
        )
    }


# =========================================================
# DELETE TRANSACTION
# =========================================================

@app.delete(
    "/api/transactions/{transaction_id}"
)
def remove_transaction(
    transaction_id: int,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    result = delete_transaction(
        transaction_id,
        uid
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail=(
                "Операция не найдена"
            )
        )

    return {
        "ok": True,
        "dashboard": (
            dashboard_data(uid)
        )
    }


# =========================================================
# TRANSFER
# =========================================================

@app.post(
    "/api/transfer"
)
def transfer_money(
    body: TransferInput,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    amount = safe_float(
        body.amount
    )

    if amount <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Сумма должна быть "
                "больше нуля"
            )
        )

    if (
        body.from_account_id
        == body.to_account_id
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Выбери разные счета"
            )
        )

    source = get_account(
        body.from_account_id,
        uid
    )

    target = get_account(
        body.to_account_id,
        uid
    )

    if (
        not source
        or not target
    ):

        raise HTTPException(
            status_code=404,
            detail="Счёт не найден"
        )

    if (
        float(
            source["balance"]
            or 0
        )
        < amount
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "На исходном счёте "
                "недостаточно денег"
            )
        )

    add_transfer(
        uid,
        body.from_account_id,
        body.to_account_id,
        amount,
        body.description
    )

    return {
        "ok": True,
        "dashboard": (
            dashboard_data(uid)
        )
    }


# =========================================================
# ACCOUNTS
# =========================================================

@app.post(
    "/api/accounts"
)
def create_account_api(
    body: AccountInput,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    name = body.name.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail=(
                "Укажи название счёта"
            )
        )

    allowed_types = (
        "card",
        "cash",
        "savings",
        "deposit",
        "investment"
    )

    if (
        body.account_type
        not in allowed_types
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Неизвестный тип счёта"
            )
        )

    account_id = add_account(
        uid,
        name,
        body.account_type,
        safe_float(
            body.balance
        ),
        body.bank_id
    )

    return {
        "ok": True,
        "id": account_id,
        "dashboard": (
            dashboard_data(uid)
        )
    }


@app.patch(
    "/api/accounts/{account_id}"
)
def edit_account_api(
    account_id: int,
    body: AccountEdit,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    if not get_account(
        account_id,
        uid
    ):

        raise HTTPException(
            status_code=404,
            detail="Счёт не найден"
        )

    if (
        body.account_type
        and body.account_type
        not in (
            "card",
            "cash",
            "savings",
            "deposit",
            "investment"
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Неизвестный тип счёта"
            )
        )

    update_account_details(
        account_id,
        uid,
        name=(
            body.name.strip()
            if body.name
            is not None
            else None
        ),
        account_type=(
            body.account_type
        ),
        bank_id_marker=(
            body.bank_id
            if body.bank_id
            is not None
            else "__KEEP__"
        )
    )

    if (
        body.balance
        is not None
    ):

        update_account_balance(
            account_id,
            uid,
            safe_float(
                body.balance
            )
        )

    return {
        "ok": True,
        "dashboard": (
            dashboard_data(uid)
        )
    }


@app.delete(
    "/api/accounts/{account_id}"
)
def remove_account_api(
    account_id: int,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    if not get_account(
        account_id,
        uid
    ):

        raise HTTPException(
            status_code=404,
            detail="Счёт не найден"
        )

    delete_account(
        account_id,
        uid
    )

    return {
        "ok": True,
        "dashboard": (
            dashboard_data(uid)
        )
    }


# =========================================================
# GOALS
# =========================================================

@app.post(
    "/api/goals"
)
def create_goal_api(
    body: GoalInput,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    target = safe_float(
        body.target_amount,
        "Цель"
    )

    if (
        target <= 0
        or not body.name.strip()
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Проверь название "
                "и сумму цели"
            )
        )

    goal_id = add_goal(
        uid,
        body.name.strip(),
        target,
        0,
        body.target_date or None,
        body.account_id
    )

    return {
        "ok": True,
        "id": goal_id,
        "dashboard": (
            dashboard_data(uid)
        )
    }


@app.patch(
    "/api/goals/{goal_id}"
)
def edit_goal_api(
    goal_id: int,
    body: GoalEdit,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    goals = {
        int(item["id"]): item
        for item
        in rows(
            get_goals(uid)
        )
    }

    if goal_id not in goals:

        raise HTTPException(
            status_code=404,
            detail="Цель не найдена"
        )

    update_goal_details(
        goal_id,
        uid,

        name=(
            body.name.strip()
            if body.name
            is not None
            else None
        ),

        target=(
            safe_float(
                body.target_amount,
                "Цель"
            )
            if body.target_amount
            is not None
            else None
        ),

        target_date_marker=(
            body.target_date
            if body.target_date
            is not None
            else "__KEEP__"
        ),

        account_marker=(
            body.account_id
            if body.account_id
            is not None
            else "__KEEP__"
        )
    )

    return {
        "ok": True,
        "dashboard": (
            dashboard_data(uid)
        )
    }


@app.delete(
    "/api/goals/{goal_id}"
)
def remove_goal_api(
    goal_id: int,
    x_telegram_init_data: str
    = Header(default="")
):

    uid = telegram_user(
        x_telegram_init_data
    )

    delete_goal(
        goal_id,
        uid
    )

    return {
        "ok": True,
        "dashboard": (
            dashboard_data(uid)
        )
    }


# =========================================================
# EDIT TRANSACTION — FINLY
# =========================================================

from database import update_transaction

class TransactionEditInput(BaseModel):
    amount: float
    account_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    created_at: str


@app.patch("/api/transactions/{transaction_id}")
def edit_transaction(
    transaction_id: int,
    body: TransactionEditInput,
    x_telegram_init_data: str = Header(default="")
):
    uid = telegram_user(x_telegram_init_data)

    try:
        update_transaction(
            transaction_id=transaction_id,
            telegram_id=uid,
            amount=body.amount,
            account_id=body.account_id,
            category_id=body.category_id,
            description=body.description,
            created_at=body.created_at
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "ok": True,
        "dashboard": dashboard_data(uid)
    }

