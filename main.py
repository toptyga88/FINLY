import os
import asyncio
import re
from datetime import datetime, date, timedelta
from calendar import monthrange

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    FSInputFile
)

from config import BOT_TOKEN

MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()

from database import (
    create_database,
    add_user,
    get_user,
    set_display_name,

    add_bank,
    get_banks,
    get_bank,
    delete_bank,

    add_account,
    get_accounts,
    get_account,
    update_account_balance,
    update_account_details,
    delete_account,

    add_income_source,
    get_income_sources,
    get_income_source,
    delete_income_source,
    update_income_source_details,

    get_categories,
    add_default_categories,
    add_transaction,
    get_transactions,
    get_transaction,
    delete_transaction,
    get_expenses_for_month,
    get_expenses_for_day,
    update_expense,
    get_incomes_for_month,
    add_transfer,
    get_transfers,
    get_plan_settings,
    set_monthly_reserve,
    get_month_expense_total,
    get_month_income_total,
    get_expense_insights_data,
    get_monthly_expense_stats,
    add_recurring_payment,
    get_recurring_payments,
    delete_recurring_payment,
    update_recurring_payment,
    add_loan,
    get_loans,
    delete_loan,
    update_loan_details,
    add_goal,
    get_goals,
    delete_goal,
    update_goal_details,
    get_savings_accounts,
    link_goal_to_account,
    get_month_incoming_transfers_to_account,
    add_expected_income,
    get_expected_incomes,
    delete_expected_income,
    update_expected_income,
)


# =========================================================
# FINLY
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# STATES
# =========================================================

class Setup(StatesGroup):
    name = State()


class AddBank(StatesGroup):
    name = State()


class AddAccount(StatesGroup):
    account_type = State()
    bank = State()
    name = State()
    balance = State()


class EditAccount(StatesGroup):
    balance = State()
    name = State()


class EditIncomeSource(StatesGroup):
    name = State()
    amount = State()
    day = State()

class AddIncome(StatesGroup):
    name = State()
    amount = State()
    frequency = State()
    day = State()
    account = State()


class AddExpense(StatesGroup):
    amount = State()
    account = State()
    category = State()
    comment = State()


class EditExpense(StatesGroup):
    amount = State()
    comment = State()


class QuickIncome(StatesGroup):
    source = State()
    amount = State()
    account = State()
    comment = State()

class TransferMoney(StatesGroup):
    source = State()
    target = State()
    amount = State()
    comment = State()


class ExpectedIncomeFlow(StatesGroup):
    source = State()
    name = State()
    amount = State()
    expected_date = State()

class PlanSettings(StatesGroup):
    reserve = State()

class EditCommitment(StatesGroup):
    value = State()

class AddPayment(StatesGroup):
    name = State()
    amount = State()
    day = State()

class AddLoanFlow(StatesGroup):
    name = State()
    remaining = State()
    monthly = State()
    day = State()
    rate = State()

class AddGoalFlow(StatesGroup):
    name = State()
    target = State()
    account = State()
    target_date = State()


# =========================================================
# HELPERS
# =========================================================

def money(value):
    """Красивое отображение денег."""

    if value is None:
        value = 0

    return f"{value:,.0f}".replace(",", " ") + " ₽"


def parse_money(text):
    """Понимает 25000, 25 000, 25000 ₽ и т.д."""

    if not text:
        return None

    cleaned = text.lower().strip()

    words = [
        "₽",
        "рублей",
        "рубля",
        "рубль",
        "руб.",
        "руб"
    ]

    for word in words:
        cleaned = cleaned.replace(word, "")

    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace(",", ".")

    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)

    try:
        return float(cleaned)
    except ValueError:
        return None


def account_icon(account_type):

    icons = {
        "card": "💳",
        "cash": "💵",
        "savings": "🏦",
        "deposit": "🔐",
        "investment": "📈"
    }

    return icons.get(account_type, "💰")


def frequency_name(frequency):

    names = {
        "monthly": "Каждый месяц",
        "irregular": "Нерегулярно",
        "once": "Разово"
    }

    return names.get(frequency, frequency)


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            *(
                [[InlineKeyboardButton(
                    text="🚀 Открыть FINLY",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )]]
                if MINI_APP_URL.startswith("https://")
                else [[InlineKeyboardButton(
                    text="🚀 Mini App: настрой HTTPS",
                    callback_data="miniapp_setup"
                )]]
            ),
            [
                InlineKeyboardButton(
                    text="💸 Расход",
                    callback_data="expense"
                ),
                InlineKeyboardButton(
                    text="💰 Доход",
                    callback_data="quick_income"
                )
            ],
            [
                InlineKeyboardButton(text="📊 Расходы", callback_data="expenses"),
                InlineKeyboardButton(text="💳 Мои деньги", callback_data="money")
            ],
            [
                InlineKeyboardButton(text="📊 План", callback_data="plan"),
                InlineKeyboardButton(text="🗓 Календарь", callback_data="money_calendar")
            ],
            [
                InlineKeyboardButton(text="🔥 Мой лимит", callback_data="smart_budget"),
                InlineKeyboardButton(text="🧠 Инсайты", callback_data="insights")
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Накопления",
                    callback_data="goals"
                ),
                InlineKeyboardButton(
                    text="📅 Платежи",
                    callback_data="payments"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Кредиты",
                    callback_data="loans"
                ),
                InlineKeyboardButton(
                    text="⚙️ Управление",
                    callback_data="manage"
                )
            ]
        ]
    )


def manage_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏛 Банки",
                    callback_data="banks"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Счета",
                    callback_data="accounts"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Источники дохода",
                    callback_data="income_sources"
                )
            ],            [
                InlineKeyboardButton(
                    text="🔄 Перевод между счетами",
                    callback_data="transfer"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📅 Платежи",
                    callback_data="payments"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Кредиты",
                    callback_data="loans"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Накопления",
                    callback_data="goals"
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Главная",
                    callback_data="home"
                )
            ]
        ]
    )


def _goal_due_now(uid, health=None):
    now=datetime.now()
    accounts=get_accounts(uid)
    spendable=sum(float(a["balance"] or 0) for a in accounts if a["account_type"] not in ("savings","deposit"))
    settings=get_plan_settings(uid)
    reserve=float(settings["monthly_reserve"] or 0) if settings else 0
    dim=monthrange(now.year,now.month)[1]
    payment_due=sum(float(x["amount"] or 0) for x in get_recurring_payments(uid) if min(int(x["day_of_month"] or 1),dim)>=now.day)
    loan_due=sum(float(x["monthly_payment"] or 0) for x in get_loans(uid) if min(int(x["payment_day"] or 1),dim)>=now.day)
    base_free=max(0,spendable-reserve-payment_due-loan_due)
    health=health or get_cashflow_health(uid)
    if health["mode"]=="deficit":
        return 0
    due=0
    for g in get_goals(uid):
        recommended=_goal_monthly_amount(g,base_free)
        if health["mode"]=="tight" and not g["target_date"]:
            recommended*=0.5
        already=0
        if g["account_id"]:
            already=get_month_incoming_transfers_to_account(uid,g["account_id"],now.year,now.month)
        due+=max(0,recommended-already)
    return due



def budget_days(health):
    """Дни распределения денег с защитой от дохода, ожидаемого сегодня."""
    today = date.today()
    horizon = health["horizon"]
    next_income = health["next_income"]

    if next_income and horizon <= today:
        horizon = date(
            today.year,
            today.month,
            monthrange(today.year, today.month)[1]
        )
        return max(1, (horizon - today).days + 1)

    return max(
        1,
        (horizon - today).days + (0 if next_income else 1)
    )


def build_smart_budget(uid):
    today=date.today()
    health=get_cashflow_health(uid)
    goal_due=_goal_due_now(uid,health)
    settings=get_plan_settings(uid)
    reserve=float(settings["monthly_reserve"] or 0) if settings else 0

    # Свободные деньги до ближайшего дохода после обязательств/резерва/актуальных накоплений.
    free=max(0,health["safe_until_income"]-reserve-goal_due)
    days=budget_days(health)
    daily=free/days

    # Недельный лимит не превышает оставшийся горизонт.
    week_days=min(7,days)
    weekly=daily*week_days

    if health["mode"]=="deficit":
        status="🚨 Есть риск нехватки денег"
        advice="Сейчас лучше не планировать необязательные накопления и покупки."
        daily=0; weekly=0
    elif health["mode"]=="tight":
        status="🟡 Деньги впритык"
        advice="Лимит сделан осторожнее. Небольшие накопления можно пропустить без чувства вины."
    else:
        status="🟢 Бюджет выглядит устойчиво"
        advice="Если сегодня потратишь меньше лимита, запас автоматически останется на следующие дни."

    if health["next_income"]:
        d,_,amount,name=health["next_income"]
        horizon=f"до {d.strftime('%d.%m')} · {name} {money(amount)}"
    else:
        horizon=f"до конца месяца · {health['horizon'].strftime('%d.%m')}"

    return (
        "🔥 <b>МОЙ ЛИМИТ</b>\n\n"
        f"{status}\n\n"
        f"💵 После обязательств доступно: <b>{money(free)}</b>\n"
        f"📆 Горизонт: <b>{horizon}</b>\n\n"
        f"🔥 Сегодня безопасно: <b>{money(daily)}</b>\n"
        f"🗓 На ближайшие {week_days} дн.: <b>{money(weekly)}</b>\n\n"
        f"🎯 Ещё желательно отложить: <b>{money(goal_due)}</b>\n"
        f"🔒 Доп. резерв: <b>{money(reserve)}</b>\n\n"
        f"<i>{advice}</i>\n\n"
        "Лимит пересчитывается по текущему балансу. После нового расхода или дохода открой этот экран снова — сумма уже будет новой."
    )


def build_home_text(uid):
    user=get_user(uid)
    name=user["display_name"] if user and user["display_name"] else "Пользователь"
    accounts=get_accounts(uid)
    total=sum(float(a["balance"] or 0) for a in accounts)
    savings=sum(float(a["balance"] or 0) for a in accounts if a["account_type"] in ("savings","deposit"))
    spendable=total-savings
    health=get_cashflow_health(uid)
    goal_due=_goal_due_now(uid,health)
    settings=get_plan_settings(uid)
    reserve=float(settings["monthly_reserve"] or 0) if settings else 0
    free=max(0,health["safe_until_income"]-reserve-goal_due)
    days=budget_days(health)
    daily=0 if health["mode"]=="deficit" else free/days
    weekly=daily*min(7,days)

    if health["mode"]=="deficit":
        status=f"🚨 <b>Есть риск нехватки {money(health['shortage'])}</b>"
    elif health["mode"]=="tight":
        status="🟡 <b>Деньги впритык</b>"
    else:
        status="🟢 <b>Всё нормально</b>"

    if health["next_income"]:
        d,_,amount,iname=health["next_income"]
        next_income=f"💰 Следующий доход: <b>{money(amount)}</b> · {iname} · {d.strftime('%d.%m')}"
        days_income=max(0,(d-date.today()).days)
        next_income+=f"\n⏳ До него: <b>{days_income} дн.</b>"
    else:
        next_income="💰 Ожидаемых доходов до конца месяца нет"

    return (
        "◼️ <b>FINLY</b>\n\n"
        f"Привет, <b>{name}</b>\n\n"
        f"💵 Доступно для жизни: <b>{money(spendable)}</b>\n"
        f"🔒 В накоплениях: <b>{money(savings)}</b>\n"
        f"💰 Всего: {money(total)}\n\n"
        f"🔥 Сегодня можно: <b>{money(daily)}</b>\n"
        f"📆 На ближайшие {min(7,days)} дн.: <b>{money(weekly)}</b>\n\n"
        f"{next_income}\n"
        f"📤 Обязательства до него: <b>{money(health['obligations'])}</b>\n"
        f"🎯 Ещё желательно отложить: <b>{money(goal_due)}</b>\n\n"
        f"{status}"
    )



# =========================================================
# HOME
# =========================================================

async def send_home(message, telegram_id):
    await message.answer(
        build_home_text(telegram_id),
        parse_mode="HTML",
        reply_markup=main_menu()
    )



@dp.callback_query(F.data == "miniapp_setup")
async def miniapp_setup_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🚀 <b>FINLY Mini App почти готов.</b>\n\n"
        "Интерфейс уже лежит в <code>index.html</code>, а API — в <code>api.py</code>.\n"
        "Telegram открывает Mini Apps только по HTTPS, поэтому в <code>.env</code> нужно добавить:\n\n"
        "<code>MINI_APP_URL=https://твой-https-адрес</code>\n\n"
        "После этого перезапусти бота — эта кнопка автоматически станет кнопкой запуска Mini App.",
        parse_mode="HTML"
    )


@dp.callback_query(F.data=="smart_budget")
async def smart_budget_callback(callback:CallbackQuery,state:FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        build_smart_budget(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Пересчитать",callback_data="smart_budget")],
            [InlineKeyboardButton(text="🗓 Календарь",callback_data="money_calendar")],
            [InlineKeyboardButton(text="← Главная",callback_data="home")]
        ])
    )


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext
):

    await state.clear()

    telegram_name = (
        message.from_user.first_name
        or message.from_user.username
        or "Пользователь"
    )

    add_user(
        message.from_user.id,
        telegram_name
    )

    user = get_user(
        message.from_user.id
    )

    if user and user["display_name"]:

        await send_home(
            message,
            message.from_user.id
        )

        return

    await state.set_state(
        Setup.name
    )

    welcome_photo = FSInputFile("/opt/finly/static/welcome.png")

    await message.answer_photo(
        photo=welcome_photo
    )

    await message.answer(
        "◼️ <b>FINLY</b>\n\n"

        "<b>Твои деньги. Один план.</b>\n\n"

        "Finly объединит:\n\n"

        "🏛 разные банки\n"
        "💳 карты и счета\n"
        "💵 наличные\n"
        "💰 источники дохода\n"
        "📅 обязательные платежи\n"
        "🏦 кредиты\n"
        "🎯 накопления\n\n"

        "Для начала познакомимся.\n\n"

        "<b>Как мне к тебе обращаться?</b>",

        parse_mode="HTML"
    )


# =========================================================
# FIRST SETUP
# =========================================================

@dp.message(Setup.name)
async def setup_name(
    message: Message,
    state: FSMContext
):

    if not message.text:
        return

    name = message.text.strip()

    if len(name) < 2:

        await message.answer(
            "Напиши имя хотя бы из двух символов."
        )

        return

    if len(name) > 30:

        await message.answer(
            "Давай немного короче 🙂"
        )

        return

    set_display_name(
        message.from_user.id,
        name
    )

    await state.clear()

    await message.answer(
        f"Приятно познакомиться, <b>{name}</b>.\n\n"

        "Finly готов.\n\n"

        "Начни с раздела <b>⚙️ Управление</b>.\n"
        "Там можно добавить банки, счета "
        "и источники дохода.",

        parse_mode="HTML",
        reply_markup=main_menu()
    )


# =========================================================
# HOME CALLBACK
# =========================================================

@dp.callback_query(F.data == "home")
async def home_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await send_home(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# MANAGEMENT
# =========================================================

@dp.callback_query(F.data == "manage")
async def manage_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await callback.message.answer(
        "⚙️ <b>УПРАВЛЕНИЕ FINLY</b>\n\n"

        "Здесь находится вся структура твоих финансов.\n\n"

        "Можно добавлять несколько банков, "
        "несколько счетов и разные источники дохода.",

        parse_mode="HTML",
        reply_markup=manage_menu()
    )


# =========================================================
# BANKS
# =========================================================

async def show_banks(
    message,
    telegram_id
):

    banks = get_banks(
        telegram_id
    )

    keyboard = []

    for bank in banks:

        keyboard.append([
            InlineKeyboardButton(
                text=f"🏛 {bank['name']}",
                callback_data=f"bank:{bank['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="＋ Добавить банк",
            callback_data="add_bank"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="← Управление",
            callback_data="manage"
        )
    ])

    if banks:

        text = (
            "🏛 <b>МОИ БАНКИ</b>\n\n"
            "Здесь можно хранить несколько банков.\n\n"
            "Выбери банк или добавь новый."
        )

    else:

        text = (
            "🏛 <b>МОИ БАНКИ</b>\n\n"
            "Ты пока не добавил ни одного банка.\n\n"
            "Например:\n"
            "• Т-Банк\n"
            "• Сбер\n"
            "• Альфа-Банк"
        )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )


@dp.callback_query(F.data == "banks")
async def banks_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await show_banks(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# ADD BANK
# =========================================================

@dp.callback_query(F.data == "add_bank")
async def add_bank_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await state.update_data(
        creating_bank_for_account=False
    )

    await state.set_state(
        AddBank.name
    )

    await callback.message.answer(
        "🏛 <b>НОВЫЙ БАНК</b>\n\n"

        "Напиши название банка.\n\n"

        "Например:\n"
        "<code>Т-Банк</code>\n"
        "<code>Сбер</code>\n"
        "<code>Альфа-Банк</code>",

        parse_mode="HTML"
    )


@dp.message(AddBank.name)
async def add_bank_name(
    message: Message,
    state: FSMContext
):

    if not message.text:
        return

    name = message.text.strip()

    if len(name) < 2:

        await message.answer(
            "Название слишком короткое."
        )

        return

    data = await state.get_data()

    bank_id = add_bank(
        message.from_user.id,
        name
    )

    # Если банк создаётся во время добавления счёта
    if data.get("creating_bank_for_account"):

        account_type = data.get(
            "account_type"
        )

        await state.clear()

        await state.update_data(
            account_type=account_type,
            bank_id=bank_id
        )

        await state.set_state(
            AddAccount.name
        )

        await message.answer(
            f"✓ Банк <b>{name}</b> добавлен.\n\n"
            "Теперь напиши название счёта.\n\n"
            "Например:\n"
            "<code>Основная карта</code>",

            parse_mode="HTML"
        )

        return

    await state.clear()

    await message.answer(
        f"✓ Банк <b>{name}</b> добавлен.",
        parse_mode="HTML"
    )

    await show_banks(
        message,
        message.from_user.id
    )


# =========================================================
# BANK DETAILS
# =========================================================

@dp.callback_query(
    F.data.startswith("bank:")
)
async def bank_detail(
    callback: CallbackQuery
):

    await callback.answer()

    bank_id = int(
        callback.data.split(":")[1]
    )

    bank = get_bank(
        bank_id,
        callback.from_user.id
    )

    if not bank:

        await callback.message.answer(
            "Банк не найден."
        )

        return

    accounts = get_accounts(
        callback.from_user.id
    )

    bank_accounts = [
        account
        for account in accounts
        if account["bank_id"] == bank_id
    ]

    total = sum(
        account["balance"]
        for account in bank_accounts
    )

    lines = [
        f"🏛 <b>{bank['name']}</b>",
        "",
        f"Всего: <b>{money(total)}</b>",
        ""
    ]

    if bank_accounts:

        lines.append("<b>Счета</b>")

        for account in bank_accounts:

            lines.append(
                f"{account_icon(account['account_type'])} "
                f"{account['name']} · "
                f"{money(account['balance'])}"
            )

    else:

        lines.append(
            "В этом банке пока нет счетов."
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Удалить банк",
                    callback_data=f"delete_bank:{bank_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Банки",
                    callback_data="banks"
                )
            ]
        ]
    )

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================================================
# DELETE BANK
# =========================================================

@dp.callback_query(
    F.data.startswith("delete_bank:")
)
async def delete_bank_callback(
    callback: CallbackQuery
):

    await callback.answer()

    bank_id = int(
        callback.data.split(":")[1]
    )

    bank = get_bank(
        bank_id,
        callback.from_user.id
    )

    if not bank:

        return

    delete_bank(
        bank_id,
        callback.from_user.id
    )

    await callback.message.answer(
        f"✓ Банк <b>{bank['name']}</b> удалён из активных.\n\n"
        "Сами счета не уничтожены.",
        parse_mode="HTML"
    )

    await show_banks(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# ACCOUNTS
# =========================================================

async def show_accounts(
    message,
    telegram_id
):

    accounts = get_accounts(
        telegram_id
    )

    keyboard = []

    total = sum(
        account["balance"]
        for account in accounts
    )

    for account in accounts:

        bank_name = (
            account["bank_name"]
            if account["bank_name"]
            else "Без банка"
        )

        keyboard.append([
            InlineKeyboardButton(
                text=(
                    f"{account_icon(account['account_type'])} "
                    f"{account['name']} · "
                    f"{money(account['balance'])}"
                ),
                callback_data=f"account:{account['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="＋ Добавить счёт",
            callback_data="add_account"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="← Управление",
            callback_data="manage"
        )
    ])

    if accounts:

        text = (
            "💳 <b>МОИ СЧЕТА</b>\n\n"
            f"Общий баланс\n"
            f"<b>{money(total)}</b>\n\n"
            "Выбери счёт для управления."
        )

    else:

        text = (
            "💳 <b>МОИ СЧЕТА</b>\n\n"
            "Счетов пока нет.\n\n"
            "Можно добавить карту, наличные, "
            "накопительный счёт, вклад или инвестиции."
        )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )


@dp.callback_query(F.data == "accounts")
async def accounts_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await show_accounts(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# ADD ACCOUNT
# =========================================================

@dp.callback_query(F.data == "add_account")
async def add_account_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await state.set_state(
        AddAccount.account_type
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Дебетовая карта",
                    callback_data="atype:card"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Накопительный счёт",
                    callback_data="atype:savings"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔐 Вклад",
                    callback_data="atype:deposit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📈 Инвестиции",
                    callback_data="atype:investment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💵 Наличные",
                    callback_data="atype:cash"
                )
            ]
        ]
    )

    await callback.message.answer(
        "💳 <b>НОВЫЙ СЧЁТ</b>\n\n"
        "Выбери тип:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# =========================================================
# SELECT ACCOUNT TYPE
# =========================================================

@dp.callback_query(
    AddAccount.account_type,
    F.data.startswith("atype:")
)
async def account_type_selected(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    account_type = (
        callback.data.split(":")[1]
    )

    await state.update_data(
        account_type=account_type
    )

    # Наличные не относятся к банку
    if account_type == "cash":

        await state.update_data(
            bank_id=None
        )

        await state.set_state(
            AddAccount.name
        )

        await callback.message.answer(
            "💵 Как назовём наличные?\n\n"
            "Например:\n"
            "<code>Наличные</code>\n"
            "<code>Кошелёк</code>",
            parse_mode="HTML"
        )

        return

    banks = get_banks(
        callback.from_user.id
    )

    keyboard = []

    for bank in banks:

        keyboard.append([
            InlineKeyboardButton(
                text=f"🏛 {bank['name']}",
                callback_data=f"choosebank:{bank['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="＋ Добавить новый банк",
            callback_data="account_new_bank"
        )
    ])

    await state.set_state(
        AddAccount.bank
    )

    if banks:

        text = (
            "🏛 <b>В каком банке находится счёт?</b>"
        )

    else:

        text = (
            "🏛 У тебя пока нет банков.\n\n"
            "Добавь банк для этого счёта."
        )

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )


# =========================================================
# SELECT BANK FOR ACCOUNT
# =========================================================

@dp.callback_query(
    AddAccount.bank,
    F.data.startswith("choosebank:")
)
async def account_bank_selected(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    bank_id = int(
        callback.data.split(":")[1]
    )

    bank = get_bank(
        bank_id,
        callback.from_user.id
    )

    if not bank:

        await callback.message.answer(
            "Банк не найден."
        )

        return

    await state.update_data(
        bank_id=bank_id
    )

    await state.set_state(
        AddAccount.name
    )

    await callback.message.answer(
        f"🏛 <b>{bank['name']}</b>\n\n"
        "Как назовём счёт?\n\n"
        "Например:\n"
        "<code>Основная карта</code>\n"
        "<code>Зарплатная</code>\n"
        "<code>Накопительный</code>",

        parse_mode="HTML"
    )


# =========================================================
# CREATE BANK DURING ACCOUNT CREATION
# =========================================================

@dp.callback_query(
    AddAccount.bank,
    F.data == "account_new_bank"
)
async def account_new_bank(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    data = await state.get_data()

    account_type = data.get(
        "account_type"
    )

    await state.clear()

    await state.update_data(
        creating_bank_for_account=True,
        account_type=account_type
    )

    await state.set_state(
        AddBank.name
    )

    await callback.message.answer(
        "🏛 <b>НОВЫЙ БАНК</b>\n\n"
        "Напиши название банка.\n\n"
        "Например:\n"
        "<code>Т-Банк</code>",
        parse_mode="HTML"
    )


# =========================================================
# ACCOUNT NAME
# =========================================================

@dp.message(AddAccount.name)
async def account_name_handler(
    message: Message,
    state: FSMContext
):

    if not message.text:
        return

    name = message.text.strip()

    if len(name) < 2:

        await message.answer(
            "Название слишком короткое."
        )

        return

    await state.update_data(
        account_name=name
    )

    await state.set_state(
        AddAccount.balance
    )

    await message.answer(
        f"<b>{name}</b>\n\n"
        "Какой баланс на этом счёте сейчас?\n\n"

        "Например:\n"
        "<code>25000</code>\n"
        "<code>25 000 ₽</code>",

        parse_mode="HTML"
    )


# =========================================================
# ACCOUNT BALANCE
# =========================================================

@dp.message(AddAccount.balance)
async def account_balance_handler(
    message: Message,
    state: FSMContext
):

    balance = parse_money(
        message.text
    )

    if balance is None:

        await message.answer(
            "Не смог понять сумму.\n\n"
            "Напиши, например:\n"
            "<code>25000</code>",
            parse_mode="HTML"
        )

        return

    if balance < 0:

        await message.answer(
            "Для обычного счёта баланс "
            "пока должен быть 0 ₽ или больше."
        )

        return

    data = await state.get_data()

    add_account(
        telegram_id=message.from_user.id,
        bank_id=data.get("bank_id"),
        name=data["account_name"],
        account_type=data["account_type"],
        balance=balance
    )

    await state.clear()

    await message.answer(
        "✓ <b>СЧЁТ ДОБАВЛЕН</b>\n\n"
        f"{account_icon(data['account_type'])} "
        f"<b>{data['account_name']}</b>\n\n"
        f"Баланс: <b>{money(balance)}</b>",
        parse_mode="HTML"
    )

    await show_accounts(
        message,
        message.from_user.id
    )


# =========================================================
# ACCOUNT DETAILS
# =========================================================

@dp.callback_query(
    F.data.startswith("account:")
)
async def account_detail(
    callback: CallbackQuery
):

    await callback.answer()

    account_id = int(
        callback.data.split(":")[1]
    )

    account = get_account(
        account_id,
        callback.from_user.id
    )

    if not account:

        await callback.message.answer(
            "Счёт не найден."
        )

        return

    bank = (
        account["bank_name"]
        if account["bank_name"]
        else "Без банка"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Название",callback_data=f"editaccname:{account_id}"),
                InlineKeyboardButton(text="💰 Баланс",callback_data=f"editbalance:{account_id}")
            ],
            [
                InlineKeyboardButton(text="🏷 Тип счёта",callback_data=f"editacctype:{account_id}"),
                InlineKeyboardButton(text="🏛 Банк",callback_data=f"editaccbank:{account_id}")
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить счёт",
                    callback_data=f"deleteaccount:{account_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Счета",
                    callback_data="accounts"
                )
            ]
        ]
    )

    await callback.message.answer(
        f"{account_icon(account['account_type'])} "
        f"<b>{account['name']}</b>\n\n"

        f"🏛 Банк\n"
        f"{bank}\n\n"

        f"💰 Баланс\n"
        f"<b>{money(account['balance'])}</b>",

        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("editaccname:"))
async def edit_account_name_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); aid=int(c.data.split(":")[1])
    if not get_account(aid,c.from_user.id): return
    await state.clear(); await state.update_data(edit_account_id=aid); await state.set_state(EditAccount.name)
    await c.message.answer("✏️ Напиши новое название счёта.")

@dp.message(EditAccount.name)
async def edit_account_name_finish(m:Message,state:FSMContext):
    name=(m.text or "").strip()
    if len(name)<2: await m.answer("Название слишком короткое."); return
    x=await state.get_data(); update_account_details(x["edit_account_id"],m.from_user.id,name=name)
    await state.clear(); await m.answer("✓ Название счёта изменено."); await show_accounts(m,m.from_user.id)

@dp.callback_query(F.data.startswith("editacctype:"))
async def edit_account_type_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); aid=int(c.data.split(":")[1])
    if not get_account(aid,c.from_user.id): return
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта",callback_data=f"setacctype:{aid}:card")],
        [InlineKeyboardButton(text="🏦 Накопительный",callback_data=f"setacctype:{aid}:savings")],
        [InlineKeyboardButton(text="🔐 Вклад",callback_data=f"setacctype:{aid}:deposit")],
        [InlineKeyboardButton(text="📈 Инвестиции",callback_data=f"setacctype:{aid}:investment")],
        [InlineKeyboardButton(text="💵 Наличные",callback_data=f"setacctype:{aid}:cash")]
    ])
    await c.message.answer("Выбери новый тип счёта:",reply_markup=kb)

@dp.callback_query(F.data.startswith("setacctype:"))
async def edit_account_type_finish(c:CallbackQuery):
    await c.answer(); _,aid,atype=c.data.split(":")
    update_account_details(int(aid),c.from_user.id,account_type=atype)
    await c.message.answer("✓ Тип счёта изменён."); await show_accounts(c.message,c.from_user.id)

@dp.callback_query(F.data.startswith("editaccbank:"))
async def edit_account_bank_start(c:CallbackQuery):
    await c.answer(); aid=int(c.data.split(":")[1]); acc=get_account(aid,c.from_user.id)
    if not acc: return
    if acc["account_type"]=="cash":
        await c.message.answer("💵 Наличные не привязываются к банку."); return
    kb=[[InlineKeyboardButton(text=f"🏛 {b['name']}",callback_data=f"setaccbank:{aid}:{b['id']}")] for b in get_banks(c.from_user.id)]
    kb.append([InlineKeyboardButton(text="Без банка",callback_data=f"setaccbank:{aid}:none")])
    await c.message.answer("Выбери банк:",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("setaccbank:"))
async def edit_account_bank_finish(c:CallbackQuery):
    await c.answer(); _,aid,bid=c.data.split(":"); bank_id=None if bid=="none" else int(bid)
    update_account_details(int(aid),c.from_user.id,bank_id_marker=bank_id)
    await c.message.answer("✓ Банк счёта изменён."); await show_accounts(c.message,c.from_user.id)


# =========================================================
# EDIT ACCOUNT BALANCE
# =========================================================

@dp.callback_query(
    F.data.startswith("editbalance:")
)
async def edit_balance_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    account_id = int(
        callback.data.split(":")[1]
    )

    await state.clear()

    await state.update_data(
        edit_account_id=account_id
    )

    await state.set_state(
        EditAccount.balance
    )

    await callback.message.answer(
        "✏️ <b>НОВЫЙ БАЛАНС</b>\n\n"
        "Напиши актуальную сумму.",
        parse_mode="HTML"
    )


@dp.message(EditAccount.balance)
async def edit_balance_finish(
    message: Message,
    state: FSMContext
):

    balance = parse_money(
        message.text
    )

    if balance is None:

        await message.answer(
            "Не понял сумму."
        )

        return

    data = await state.get_data()

    update_account_balance(
        data["edit_account_id"],
        message.from_user.id,
        balance
    )

    await state.clear()

    await message.answer(
        f"✓ Баланс изменён на "
        f"<b>{money(balance)}</b>",
        parse_mode="HTML"
    )

    await show_accounts(
        message,
        message.from_user.id
    )


# =========================================================
# DELETE ACCOUNT
# =========================================================

@dp.callback_query(
    F.data.startswith("deleteaccount:")
)
async def delete_account_callback(
    callback: CallbackQuery
):

    await callback.answer()

    account_id = int(
        callback.data.split(":")[1]
    )

    account = get_account(
        account_id,
        callback.from_user.id
    )

    if not account:
        return

    delete_account(
        account_id,
        callback.from_user.id
    )

    await callback.message.answer(
        f"✓ Счёт <b>{account['name']}</b> удалён.",
        parse_mode="HTML"
    )

    await show_accounts(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# INCOME SOURCES
# =========================================================

async def show_income_sources(
    message,
    telegram_id
):

    sources = get_income_sources(
        telegram_id
    )

    keyboard = []

    regular_total = 0

    for source in sources:

        if source["frequency"] == "monthly":
            regular_total += source["amount"]

        keyboard.append([
            InlineKeyboardButton(
                text=(
                    f"💰 {source['name']} · "
                    f"{money(source['amount'])}"
                ),
                callback_data=f"incomesource:{source['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="＋ Добавить источник дохода",
            callback_data="add_income_source"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text="← Управление",
            callback_data="manage"
        )
    ])

    if sources:

        text = (
            "💰 <b>ИСТОЧНИКИ ДОХОДА</b>\n\n"

            "Ожидаемый регулярный доход в месяц\n"
            f"<b>{money(regular_total)}</b>\n\n"

            "Ожидаемые деньги не прибавляются "
            "к балансу автоматически."
        )

    else:

        text = (
            "💰 <b>ИСТОЧНИКИ ДОХОДА</b>\n\n"

            "Источников пока нет.\n\n"

            "Можно добавить зарплату, аванс, "
            "подработку или любой другой доход."
        )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )


@dp.callback_query(
    F.data == "income_sources"
)
async def income_sources_callback(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await show_income_sources(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# ADD INCOME SOURCE
# =========================================================

@dp.callback_query(
    F.data == "add_income_source"
)
async def add_income_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    await state.clear()

    await state.set_state(
        AddIncome.name
    )

    await callback.message.answer(
        "💰 <b>НОВЫЙ ИСТОЧНИК ДОХОДА</b>\n\n"

        "Как называется источник?\n\n"

        "Например:\n"
        "<code>Зарплата</code>\n"
        "<code>Аванс</code>\n"
        "<code>Подработка</code>\n"
        "<code>Аренда</code>",

        parse_mode="HTML"
    )


@dp.message(AddIncome.name)
async def income_name_handler(
    message: Message,
    state: FSMContext
):

    if not message.text:
        return

    name = message.text.strip()

    if len(name) < 2:

        await message.answer(
            "Название слишком короткое."
        )

        return

    await state.update_data(
        income_name=name
    )

    await state.set_state(
        AddIncome.amount
    )

    await message.answer(
        f"💰 <b>{name}</b>\n\n"
        "Какая сумма обычно приходит?\n\n"
        "Например:\n"
        "<code>85000</code>",
        parse_mode="HTML"
    )


@dp.message(AddIncome.amount)
async def income_amount_handler(
    message: Message,
    state: FSMContext
):

    amount = parse_money(
        message.text
    )

    if amount is None or amount <= 0:

        await message.answer(
            "Не понял сумму.\n\n"
            "Напиши, например:\n"
            "<code>85000</code>",
            parse_mode="HTML"
        )

        return

    await state.update_data(
        income_amount=amount
    )

    await state.set_state(
        AddIncome.frequency
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Каждый месяц",
                    callback_data="freq:monthly"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Нерегулярно",
                    callback_data="freq:irregular"
                )
            ],
            [
                InlineKeyboardButton(
                    text="1️⃣ Разово",
                    callback_data="freq:once"
                )
            ]
        ]
    )

    await message.answer(
        "Как часто приходит этот доход?",
        reply_markup=keyboard
    )


# =========================================================
# INCOME FREQUENCY
# =========================================================

@dp.callback_query(
    AddIncome.frequency,
    F.data.startswith("freq:")
)
async def income_frequency_handler(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    frequency = (
        callback.data.split(":")[1]
    )

    await state.update_data(
        income_frequency=frequency
    )

    if frequency == "monthly":

        await state.set_state(
            AddIncome.day
        )

        await callback.message.answer(
            "📅 Какого числа обычно приходит доход?\n\n"
            "Например:\n"
            "<code>5</code>",
            parse_mode="HTML"
        )

        return

    await state.update_data(
        income_day=None
    )

    await ask_income_account(
        callback.message,
        callback.from_user.id,
        state
    )


# =========================================================
# INCOME DAY
# =========================================================

@dp.message(AddIncome.day)
async def income_day_handler(
    message: Message,
    state: FSMContext
):

    try:
        day = int(
            message.text.strip()
        )

    except (ValueError, AttributeError):

        await message.answer(
            "Напиши число от 1 до 31."
        )

        return

    if not 1 <= day <= 31:

        await message.answer(
            "День должен быть от 1 до 31."
        )

        return

    await state.update_data(
        income_day=day
    )

    await ask_income_account(
        message,
        message.from_user.id,
        state
    )


# =========================================================
# SELECT ACCOUNT FOR INCOME
# =========================================================

async def ask_income_account(
    message,
    telegram_id,
    state
):

    accounts = get_accounts(
        telegram_id
    )

    keyboard = []

    for account in accounts:

        bank = (
            f"{account['bank_name']} · "
            if account["bank_name"]
            else ""
        )

        keyboard.append([
            InlineKeyboardButton(
                text=(
                    f"{account_icon(account['account_type'])} "
                    f"{bank}{account['name']}"
                ),
                callback_data=f"incomeaccount:{account['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="Не привязывать к счёту",
            callback_data="incomeaccount:none"
        )
    ])

    await state.set_state(
        AddIncome.account
    )

    await message.answer(
        "💳 <b>Куда обычно приходит этот доход?</b>\n\n"
        "Выбери счёт.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )


# =========================================================
# FINISH INCOME SOURCE
# =========================================================

@dp.callback_query(
    AddIncome.account,
    F.data.startswith("incomeaccount:")
)
async def income_account_handler(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()

    value = (
        callback.data.split(":")[1]
    )

    if value == "none":
        account_id = None
    else:
        account_id = int(value)

    data = await state.get_data()

    add_income_source(
        telegram_id=callback.from_user.id,
        name=data["income_name"],
        amount=data["income_amount"],
        frequency=data["income_frequency"],
        day_of_month=data.get("income_day"),
        account_id=account_id
    )

    await state.clear()

    await callback.message.answer(
        "✓ <b>ИСТОЧНИК ДОХОДА ДОБАВЛЕН</b>\n\n"

        f"💰 {data['income_name']}\n"
        f"<b>{money(data['income_amount'])}</b>\n\n"

        "Finly запомнил ожидаемый доход.\n\n"

        "<b>Баланс счёта не увеличен.</b>\n"
        "Позже Finly спросит, действительно ли "
        "деньги пришли.",

        parse_mode="HTML"
    )

    await show_income_sources(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# INCOME SOURCE DETAILS
# =========================================================

@dp.callback_query(
    F.data.startswith("incomesource:")
)
async def income_source_detail(
    callback: CallbackQuery
):

    await callback.answer()

    source_id = int(
        callback.data.split(":")[1]
    )

    source = get_income_source(
        source_id,
        callback.from_user.id
    )

    if not source:

        await callback.message.answer(
            "Источник дохода не найден."
        )

        return

    account_text = "Не привязан"

    accounts = get_accounts(
        callback.from_user.id
    )

    for account in accounts:

        if account["id"] == source["account_id"]:

            if account["bank_name"]:

                account_text = (
                    f"{account['bank_name']} / "
                    f"{account['name']}"
                )

            else:

                account_text = account["name"]

            break

    day_text = (
        str(source["day_of_month"])
        if source["day_of_month"]
        else "—"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Название",callback_data=f"editincname:{source_id}"),
                InlineKeyboardButton(text="💰 Сумма",callback_data=f"editincamount:{source_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Периодичность",callback_data=f"editincfreq:{source_id}"),
                InlineKeyboardButton(text="📅 День",callback_data=f"editincday:{source_id}")
            ],
            [
                InlineKeyboardButton(text="💳 Счёт",callback_data=f"editincaccount:{source_id}")
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить источник",
                    callback_data=f"deleteincome:{source_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Источники дохода",
                    callback_data="income_sources"
                )
            ]
        ]
    )

    await callback.message.answer(
        f"💰 <b>{source['name']}</b>\n\n"

        f"Сумма\n"
        f"<b>{money(source['amount'])}</b>\n\n"

        f"Периодичность\n"
        f"{frequency_name(source['frequency'])}\n\n"

        f"День поступления\n"
        f"{day_text}\n\n"

        f"Счёт\n"
        f"{account_text}",

        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("editincname:"))
async def edit_income_name_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); sid=int(c.data.split(":")[1])
    if not get_income_source(sid,c.from_user.id): return
    await state.clear(); await state.update_data(edit_income_id=sid); await state.set_state(EditIncomeSource.name)
    await c.message.answer("Новое название источника дохода:")

@dp.message(EditIncomeSource.name)
async def edit_income_name_finish(m:Message,state:FSMContext):
    name=(m.text or "").strip()
    if len(name)<2: await m.answer("Название слишком короткое."); return
    x=await state.get_data(); update_income_source_details(x["edit_income_id"],m.from_user.id,name=name)
    await state.clear(); await m.answer("✓ Название изменено."); await show_income_sources(m,m.from_user.id)

@dp.callback_query(F.data.startswith("editincamount:"))
async def edit_income_amount_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); sid=int(c.data.split(":")[1])
    if not get_income_source(sid,c.from_user.id): return
    await state.clear(); await state.update_data(edit_income_id=sid); await state.set_state(EditIncomeSource.amount)
    await c.message.answer("Какая теперь ожидаемая сумма?")

@dp.message(EditIncomeSource.amount)
async def edit_income_amount_finish(m:Message,state:FSMContext):
    v=parse_money(m.text)
    if v is None or v<=0: await m.answer("Напиши сумму больше нуля."); return
    x=await state.get_data(); update_income_source_details(x["edit_income_id"],m.from_user.id,amount=v)
    await state.clear(); await m.answer("✓ Сумма изменена."); await show_income_sources(m,m.from_user.id)

@dp.callback_query(F.data.startswith("editincfreq:"))
async def edit_income_freq_start(c:CallbackQuery):
    await c.answer(); sid=int(c.data.split(":")[1])
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Каждый месяц",callback_data=f"setincfreq:{sid}:monthly")],
        [InlineKeyboardButton(text="🔄 Нерегулярно",callback_data=f"setincfreq:{sid}:irregular")],
        [InlineKeyboardButton(text="1️⃣ Разово",callback_data=f"setincfreq:{sid}:once")]
    ])
    await c.message.answer("Как теперь приходит этот доход?",reply_markup=kb)

@dp.callback_query(F.data.startswith("setincfreq:"))
async def edit_income_freq_finish(c:CallbackQuery,state:FSMContext):
    await c.answer(); _,sid,freq=c.data.split(":"); sid=int(sid)
    if freq=="monthly":
        update_income_source_details(sid,c.from_user.id,frequency=freq)
        await state.clear(); await state.update_data(edit_income_id=sid); await state.set_state(EditIncomeSource.day)
        await c.message.answer("Какого числа обычно приходит доход? 1–31"); return
    update_income_source_details(sid,c.from_user.id,frequency=freq,day_marker=None)
    await c.message.answer("✓ Периодичность изменена."); await show_income_sources(c.message,c.from_user.id)

@dp.callback_query(F.data.startswith("editincday:"))
async def edit_income_day_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); sid=int(c.data.split(":")[1]); src=get_income_source(sid,c.from_user.id)
    if not src: return
    if src["frequency"]!="monthly":
        await c.message.answer("День месяца используется только для регулярного ежемесячного дохода."); return
    await state.clear(); await state.update_data(edit_income_id=sid); await state.set_state(EditIncomeSource.day)
    await c.message.answer("Новое число поступления: 1–31")

@dp.message(EditIncomeSource.day)
async def edit_income_day_finish(m:Message,state:FSMContext):
    try: day=int((m.text or "").strip())
    except ValueError: day=0
    if not 1<=day<=31: await m.answer("Нужно число от 1 до 31."); return
    x=await state.get_data(); update_income_source_details(x["edit_income_id"],m.from_user.id,day_marker=day)
    await state.clear(); await m.answer("✓ День поступления изменён."); await show_income_sources(m,m.from_user.id)

@dp.callback_query(F.data.startswith("editincaccount:"))
async def edit_income_account_start(c:CallbackQuery):
    await c.answer(); sid=int(c.data.split(":")[1])
    kb=[]
    for a in get_accounts(c.from_user.id):
        kb.append([InlineKeyboardButton(text=f"{account_icon(a['account_type'])} {a['name']}",callback_data=f"setincaccount:{sid}:{a['id']}")])
    kb.append([InlineKeyboardButton(text="Не привязывать",callback_data=f"setincaccount:{sid}:none")])
    await c.message.answer("Куда обычно приходит доход?",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("setincaccount:"))
async def edit_income_account_finish(c:CallbackQuery):
    await c.answer(); _,sid,aid=c.data.split(":"); account_id=None if aid=="none" else int(aid)
    update_income_source_details(int(sid),c.from_user.id,account_marker=account_id)
    await c.message.answer("✓ Счёт поступления изменён."); await show_income_sources(c.message,c.from_user.id)


# =========================================================
# DELETE INCOME SOURCE
# =========================================================

@dp.callback_query(
    F.data.startswith("deleteincome:")
)
async def delete_income_callback(
    callback: CallbackQuery
):

    await callback.answer()

    source_id = int(
        callback.data.split(":")[1]
    )

    source = get_income_source(
        source_id,
        callback.from_user.id
    )

    if not source:
        return

    delete_income_source(
        source_id,
        callback.from_user.id
    )

    await callback.message.answer(
        f"✓ Источник <b>{source['name']}</b> удалён.",
        parse_mode="HTML"
    )

    await show_income_sources(
        callback.message,
        callback.from_user.id
    )


# =========================================================
# MONEY OVERVIEW
# =========================================================

@dp.callback_query(F.data == "money")
async def money_overview(
    callback: CallbackQuery
):

    await callback.answer()

    accounts = get_accounts(
        callback.from_user.id
    )

    if not accounts:

        await callback.message.answer(
            "💳 <b>СЧЕТОВ ПОКА НЕТ</b>\n\n"
            "Открой:\n"
            "⚙️ Управление → 💳 Счета",
            parse_mode="HTML"
        )

        return

    total = sum(
        account["balance"]
        for account in accounts
    )

    banks = {}
    no_bank = []

    for account in accounts:

        if account["bank_name"]:

            banks.setdefault(
                account["bank_name"],
                []
            ).append(account)

        else:

            no_bank.append(account)

    lines = [
        "💳 <b>МОИ ДЕНЬГИ</b>",
        "",
        "Общий баланс",
        f"<b>{money(total)}</b>",
        ""
    ]

    for bank_name, bank_accounts in banks.items():

        bank_total = sum(
            account["balance"]
            for account in bank_accounts
        )

        lines.append(
            f"🏛 <b>{bank_name}</b>"
        )

        lines.append(
            f"{money(bank_total)}"
        )

        for account in bank_accounts:

            lines.append(
                f"   {account_icon(account['account_type'])} "
                f"{account['name']} · "
                f"{money(account['balance'])}"
            )

        lines.append("")

    if no_bank:

        lines.append(
            "💵 <b>БЕЗ БАНКА</b>"
        )

        for account in no_bank:

            lines.append(
                f"   {account['name']} · "
                f"{money(account['balance'])}"
            )

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⚙️ Управление",
                        callback_data="manage"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="← Главная",
                        callback_data="home"
                    )
                ]
            ]
        )
    )


# =========================================================
# EXPENSES
# =========================================================

async def ask_expense_account(message, telegram_id, state):
    accounts = get_accounts(telegram_id)

    if not accounts:
        await state.clear()
        await message.answer(
            "💳 <b>Сначала добавь хотя бы один счёт.</b>\n\n"
            "Открой ⚙️ Управление → 💳 Счета.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        return

    keyboard = []
    for account in accounts:
        bank = f"{account['bank_name']} · " if account["bank_name"] else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{account_icon(account['account_type'])} {bank}{account['name']} · {money(account['balance'])}",
                callback_data=f"expenseaccount:{account['id']}"
            )
        ])

    await state.set_state(AddExpense.account)
    await message.answer(
        "💳 <b>С какого счёта потратил?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@dp.callback_query(F.data == "expense")
async def expense_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(AddExpense.amount)
    await callback.message.answer(
        "💸 <b>НОВЫЙ РАСХОД</b>\n\n"
        "Сколько потратил?\n\n"
        "Например: <code>1250</code> или <code>1 250 ₽</code>",
        parse_mode="HTML"
    )


@dp.message(AddExpense.amount)
async def expense_amount_handler(message: Message, state: FSMContext):
    amount = parse_money(message.text)
    if amount is None or amount <= 0:
        await message.answer("Не понял сумму. Напиши, например: <code>1250</code>", parse_mode="HTML")
        return

    await state.update_data(expense_amount=amount)
    await ask_expense_account(message, message.from_user.id, state)


@dp.callback_query(AddExpense.account, F.data.startswith("expenseaccount:"))
async def expense_account_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    account_id = int(callback.data.split(":")[1])
    account = get_account(account_id, callback.from_user.id)
    if not account:
        await callback.message.answer("Счёт не найден.")
        return

    await state.update_data(expense_account_id=account_id)
    add_default_categories(callback.from_user.id)
    categories = get_categories(callback.from_user.id, "expense")

    keyboard = []
    row = []
    for category in categories:
        row.append(InlineKeyboardButton(
            text=f"{category['icon']} {category['name']}",
            callback_data=f"expensecategory:{category['id']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await state.set_state(AddExpense.category)
    await callback.message.answer(
        "📂 <b>Выбери категорию</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@dp.callback_query(AddExpense.category, F.data.startswith("expensecategory:"))
async def expense_category_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category_id = int(callback.data.split(":")[1])
    await state.update_data(expense_category_id=category_id)
    await state.set_state(AddExpense.comment)

    await callback.message.answer(
        "💬 <b>Комментарий к трате</b>\n\n"
        "Напиши, на что именно ушли деньги.\n"
        "Например: <code>ужин с девушкой</code>\n\n"
        "Комментарий необязателен.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏭ Без комментария", callback_data="expensecomment:skip")
        ]])
    )


async def finish_expense(message, telegram_id, state, comment=None):
    data = await state.get_data()
    account = get_account(data["expense_account_id"], telegram_id)
    if not account:
        await state.clear()
        await message.answer("Счёт не найден.")
        return

    tx_id = add_transaction(
        telegram_id=telegram_id,
        account_id=data["expense_account_id"],
        transaction_type="expense",
        amount=data["expense_amount"],
        description=comment,
        category_id=data["expense_category_id"]
    )

    new_account = get_account(data["expense_account_id"], telegram_id)
    await state.clear()

    comment_line = f"\n💬 {comment}" if comment else ""
    await message.answer(
        "✓ <b>РАСХОД ЗАПИСАН</b>\n\n"
        f"💸 <b>{money(data['expense_amount'])}</b>\n"
        f"💳 {account['name']}"
        f"{comment_line}\n\n"
        f"Остаток на счёте: <b>{money(new_account['balance'])}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Отменить эту трату", callback_data=f"deletetx:{tx_id}")],
            [InlineKeyboardButton(text="← Главная", callback_data="home")]
        ])
    )


@dp.message(AddExpense.comment)
async def expense_comment_handler(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Напиши комментарий текстом или нажми «Без комментария».")
        return
    comment = message.text.strip()
    if len(comment) > 300:
        await message.answer("Комментарий слишком длинный. Максимум 300 символов.")
        return
    await finish_expense(message, message.from_user.id, state, comment)


@dp.callback_query(AddExpense.comment, F.data == "expensecomment:skip")
async def expense_comment_skip(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await finish_expense(callback.message, callback.from_user.id, state, None)


@dp.callback_query(F.data.startswith("deletetx:"))
async def delete_transaction_callback(callback: CallbackQuery):
    await callback.answer()
    tx_id = int(callback.data.split(":")[1])
    tx = get_transaction(tx_id, callback.from_user.id)
    if not tx:
        await callback.message.answer("Операция не найдена или уже удалена.")
        return

    delete_transaction(tx_id, callback.from_user.id)
    await callback.message.answer(
        f"✓ Операция на <b>{money(tx['amount'])}</b> удалена. Баланс восстановлен.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# =========================================================
# EXPENSE JOURNAL / ANALYTICS
# =========================================================

MONTHS_RU = ["", "январь", "февраль", "март", "апрель", "май", "июнь",
             "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


def month_shift(year, month, delta):
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


async def show_expense_month(message, telegram_id, year=None, month=None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    rows = get_expenses_for_month(telegram_id, year, month)
    total = sum(float(r["amount"]) for r in rows)

    by_category = {}
    by_day = {}
    for r in rows:
        key = (r["category_icon"] or "📦", r["category_name"] or "Без категории")
        by_category[key] = by_category.get(key, 0) + float(r["amount"])
        day = r["created_at"][:10]
        by_day[day] = by_day.get(day, 0) + float(r["amount"])

    lines = [f"📊 <b>РАСХОДЫ · {MONTHS_RU[month].upper()} {year}</b>", "",
             "Потрачено", f"<b>{money(total)}</b>", ""]
    if rows:
        lines.append("<b>По категориям</b>")
        for (icon, name), amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            pct = round(amount / total * 100) if total else 0
            lines.append(f"{icon} {name}: <b>{money(amount)}</b> · {pct}%")
        lines += ["", f"🔥 Самый дорогой день: <b>{money(max(by_day.values()))}</b>",
                  f"📅 Среднее за день с тратами: <b>{money(total / len(by_day))}</b>"]
    else:
        lines.append("В этом месяце расходов пока нет.")

    py, pm = month_shift(year, month, -1)
    ny, nm = month_shift(year, month, 1)
    keyboard = [
        [InlineKeyboardButton(text="◀️ Пред. месяц", callback_data=f"expensesmonth:{py}:{pm}"),
         InlineKeyboardButton(text="След. месяц ▶️", callback_data=f"expensesmonth:{ny}:{nm}")],
        [InlineKeyboardButton(text="📅 По дням", callback_data=f"expensedays:{year}:{month}")],
        [InlineKeyboardButton(text="🧾 Все операции", callback_data=f"expenseops:{year}:{month}")],
        [InlineKeyboardButton(text="← Главная", callback_data="home")]
    ]
    await message.answer("\n".join(lines), parse_mode="HTML",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@dp.callback_query(F.data == "expenses")
async def expenses_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer(); await state.clear()
    await show_expense_month(callback.message, callback.from_user.id)


@dp.callback_query(F.data.startswith("expensesmonth:"))
async def expenses_month_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer(); await state.clear()
    _, y, m = callback.data.split(":")
    await show_expense_month(callback.message, callback.from_user.id, int(y), int(m))


@dp.callback_query(F.data.startswith("expensedays:"))
async def expense_days_callback(callback: CallbackQuery):
    await callback.answer()
    _, y, m = callback.data.split(":"); y, m = int(y), int(m)
    rows = get_expenses_for_month(callback.from_user.id, y, m)
    days = {}
    for r in rows:
        d = r["created_at"][:10]; days[d] = days.get(d, 0) + float(r["amount"])
    keyboard = []
    for d, amount in sorted(days.items(), reverse=True):
        dt = datetime.strptime(d, "%Y-%m-%d")
        keyboard.append([InlineKeyboardButton(text=f"{dt.day:02d}.{dt.month:02d} · {money(amount)}",
                                              callback_data=f"expenseday:{d}")])
    if not keyboard:
        keyboard.append([InlineKeyboardButton(text="Расходов нет", callback_data="noop")])
    keyboard.append([InlineKeyboardButton(text="← К месяцу", callback_data=f"expensesmonth:{y}:{m}")])
    await callback.message.answer("📅 <b>РАСХОДЫ ПО ДНЯМ</b>", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@dp.callback_query(F.data.startswith("expenseday:"))
async def expense_day_callback(callback: CallbackQuery):
    await callback.answer(); date_iso = callback.data.split(":", 1)[1]
    rows = get_expenses_for_day(callback.from_user.id, date_iso)
    total = sum(float(r["amount"]) for r in rows)
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    lines = [f"📅 <b>{dt.day:02d}.{dt.month:02d}.{dt.year}</b>", f"Всего: <b>{money(total)}</b>", ""]
    keyboard = []
    for r in rows:
        comment = f" · {r['description']}" if r["description"] else ""
        lines.append(f"{r['category_icon'] or '📦'} {money(r['amount'])} · {r['category_name'] or 'Без категории'}{comment}")
        keyboard.append([InlineKeyboardButton(text=f"{r['category_icon'] or '📦'} {money(r['amount'])} · открыть",
                                              callback_data=f"expenseview:{r['id']}")])
    keyboard.append([InlineKeyboardButton(text="← К дням", callback_data=f"expensedays:{dt.year}:{dt.month}")])
    await callback.message.answer("\n".join(lines), parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@dp.callback_query(F.data.startswith("expenseops:"))
async def expense_ops_callback(callback: CallbackQuery):
    await callback.answer(); _, y, m = callback.data.split(":"); y, m = int(y), int(m)
    rows = get_expenses_for_month(callback.from_user.id, y, m)
    keyboard = []
    for r in rows[:50]:
        d = datetime.fromisoformat(r["created_at"]).strftime("%d.%m")
        keyboard.append([InlineKeyboardButton(text=f"{d} · {r['category_icon'] or '📦'} {money(r['amount'])}",
                                              callback_data=f"expenseview:{r['id']}")])
    if not keyboard: keyboard.append([InlineKeyboardButton(text="Расходов нет", callback_data="noop")])
    keyboard.append([InlineKeyboardButton(text="← К месяцу", callback_data=f"expensesmonth:{y}:{m}")])
    await callback.message.answer("🧾 <b>ОПЕРАЦИИ ЗА МЕСЯЦ</b>", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@dp.callback_query(F.data.startswith("expenseview:"))
async def expense_view_callback(callback: CallbackQuery):
    await callback.answer(); tx_id = int(callback.data.split(":")[1])
    tx = get_transaction(tx_id, callback.from_user.id)
    if not tx or tx["transaction_type"] != "expense":
        await callback.message.answer("Расход не найден."); return
    dt = datetime.fromisoformat(tx["created_at"])
    text = (f"💸 <b>РАСХОД</b>\n\n<b>{money(tx['amount'])}</b>\n"
            f"{tx['category_icon'] or '📦'} {tx['category_name'] or 'Без категории'}\n"
            f"💳 {tx['account_name'] or 'Счёт удалён'}\n📅 {dt:%d.%m.%Y %H:%M}\n"
            f"💬 {tx['description'] or 'Без комментария'}")
    kb = [[InlineKeyboardButton(text="💰 Изменить сумму", callback_data=f"editexpenseamount:{tx_id}")],
          [InlineKeyboardButton(text="💬 Изменить комментарий", callback_data=f"editexpensecomment:{tx_id}")],
          [InlineKeyboardButton(text="💳 Изменить счёт", callback_data=f"editexpenseaccount:{tx_id}")],
          [InlineKeyboardButton(text="📂 Изменить категорию", callback_data=f"editexpensecategory:{tx_id}")],
          [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"deletetx:{tx_id}")],
          [InlineKeyboardButton(text="← Расходы", callback_data=f"expensesmonth:{dt.year}:{dt.month}")]]
    await callback.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("editexpenseamount:"))
async def edit_expense_amount_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer(); tx_id = int(callback.data.split(":")[1])
    if not get_transaction(tx_id, callback.from_user.id): return
    await state.clear(); await state.update_data(edit_expense_id=tx_id); await state.set_state(EditExpense.amount)
    await callback.message.answer("💰 Напиши новую сумму расхода:")


@dp.message(EditExpense.amount)
async def edit_expense_amount_finish(message: Message, state: FSMContext):
    amount = parse_money(message.text)
    if amount is None or amount <= 0:
        await message.answer("Напиши корректную сумму больше 0."); return
    data = await state.get_data(); tx_id = data["edit_expense_id"]
    update_expense(tx_id, message.from_user.id, amount=amount); await state.clear()
    await message.answer("✓ Сумма изменена, баланс пересчитан.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть расход", callback_data=f"expenseview:{tx_id}")]]))


@dp.callback_query(F.data.startswith("editexpensecomment:"))
async def edit_expense_comment_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer(); tx_id = int(callback.data.split(":")[1])
    if not get_transaction(tx_id, callback.from_user.id): return
    await state.clear(); await state.update_data(edit_expense_id=tx_id); await state.set_state(EditExpense.comment)
    await callback.message.answer("💬 Напиши новый комментарий. Чтобы убрать его, отправь <code>-</code>", parse_mode="HTML")


@dp.message(EditExpense.comment)
async def edit_expense_comment_finish(message: Message, state: FSMContext):
    if not message.text: return
    comment = message.text.strip(); comment = None if comment == "-" else comment[:300]
    data = await state.get_data(); tx_id = data["edit_expense_id"]
    update_expense(tx_id, message.from_user.id, description=comment, update_description=True); await state.clear()
    await message.answer("✓ Комментарий изменён.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть расход", callback_data=f"expenseview:{tx_id}")]]))


@dp.callback_query(F.data.startswith("editexpenseaccount:"))
async def edit_expense_account_start(callback: CallbackQuery):
    await callback.answer(); tx_id = int(callback.data.split(":")[1])
    if not get_transaction(tx_id, callback.from_user.id): return
    kb = [[InlineKeyboardButton(text=f"{account_icon(a['account_type'])} {a['name']} · {money(a['balance'])}",
                                callback_data=f"setexpenseaccount:{tx_id}:{a['id']}")] for a in get_accounts(callback.from_user.id)]
    await callback.message.answer("💳 Выбери новый счёт:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("setexpenseaccount:"))
async def set_expense_account(callback: CallbackQuery):
    await callback.answer(); _, tx, acc = callback.data.split(":"); tx, acc = int(tx), int(acc)
    update_expense(tx, callback.from_user.id, account_id=acc)
    await callback.message.answer("✓ Счёт изменён, оба баланса пересчитаны.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть расход", callback_data=f"expenseview:{tx}")]]))


@dp.callback_query(F.data.startswith("editexpensecategory:"))
async def edit_expense_category_start(callback: CallbackQuery):
    await callback.answer(); tx_id = int(callback.data.split(":")[1]); add_default_categories(callback.from_user.id)
    if not get_transaction(tx_id, callback.from_user.id): return
    kb = [[InlineKeyboardButton(text=f"{c['icon']} {c['name']}", callback_data=f"setexpensecategory:{tx_id}:{c['id']}")]
          for c in get_categories(callback.from_user.id, "expense")]
    await callback.message.answer("📂 Выбери новую категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("setexpensecategory:"))
async def set_expense_category(callback: CallbackQuery):
    await callback.answer(); _, tx, cat = callback.data.split(":"); tx, cat = int(tx), int(cat)
    update_expense(tx, callback.from_user.id, category_id=cat)
    await callback.message.answer("✓ Категория изменена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть расход", callback_data=f"expenseview:{tx}")]]))


@dp.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()



# =========================================================
# FACTUAL INCOME
# =========================================================
@dp.callback_query(F.data == "quick_income")
async def quick_income_start(callback: CallbackQuery,state:FSMContext):
    await callback.answer(); await state.clear()
    sources=get_income_sources(callback.from_user.id)
    kb=[[InlineKeyboardButton(text=f"💰 {s['name']} · {money(s['amount'])}",callback_data=f"qis:{s['id']}")] for s in sources]
    kb += [[InlineKeyboardButton(text="＋ Другой доход",callback_data="qis:other")],
           [InlineKeyboardButton(text="← Главная",callback_data="home")]]
    await state.set_state(QuickIncome.source)
    await callback.message.answer("💰 <b>ДОХОД</b>\\n\\nВыбери источник. Баланс увеличится только после записи фактически полученных денег.",
                                  parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(QuickIncome.source,F.data.startswith("qis:"))
async def qi_source(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); v=callback.data.split(":")[1]; name="Другой доход"
    if v!="other":
        s=get_income_source(int(v),callback.from_user.id)
        if not s:return
        name=s["name"]
    await state.update_data(qi_name=name); await state.set_state(QuickIncome.amount)
    await callback.message.answer(f"💰 <b>{name}</b>\\n\\nСколько реально пришло?\\nНапример: <code>85000</code>",parse_mode="HTML")

@dp.message(QuickIncome.amount)
async def qi_amount(message:Message,state:FSMContext):
    amount=parse_money(message.text)
    if amount is None or amount<=0:
        await message.answer("Напиши корректную сумму."); return
    accounts=get_accounts(message.from_user.id)
    if not accounts:
        await state.clear(); await message.answer("Сначала добавь счёт.",reply_markup=main_menu()); return
    await state.update_data(qi_amount=amount); await state.set_state(QuickIncome.account)
    kb=[[InlineKeyboardButton(text=f"{account_icon(a['account_type'])} {a['name']} · {money(a['balance'])}",
                              callback_data=f"qia:{a['id']}")] for a in accounts]
    await message.answer("💳 Куда пришли деньги?",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(QuickIncome.account,F.data.startswith("qia:"))
async def qi_account(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); aid=int(callback.data.split(":")[1])
    if not get_account(aid,callback.from_user.id):return
    await state.update_data(qi_account=aid); await state.set_state(QuickIncome.comment)
    await callback.message.answer("💬 Комментарий к доходу или пропусти.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить",callback_data="qi_skip")]]))

async def qi_finish(message,uid,state,comment=None):
    d=await state.get_data()
    add_transaction(uid,d["qi_account"],"income",d["qi_amount"],comment or d.get("qi_name"))
    acc=get_account(d["qi_account"],uid); await state.clear()
    await message.answer(f"✓ <b>ДОХОД ЗАПИСАН</b>\\n\\n💰 <b>+{money(d['qi_amount'])}</b>\\nСчёт: {acc['name']}\\nБаланс: <b>{money(acc['balance'])}</b>",
                         parse_mode="HTML",reply_markup=main_menu())

@dp.message(QuickIncome.comment)
async def qi_comment(message:Message,state:FSMContext):
    await qi_finish(message,message.from_user.id,state,message.text.strip() if message.text else None)

@dp.callback_query(QuickIncome.comment,F.data=="qi_skip")
async def qi_skip(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); await qi_finish(callback.message,callback.from_user.id,state)

# =========================================================
# TRANSFERS
# =========================================================
@dp.callback_query(F.data=="transfer")
async def transfer_start(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); await state.clear(); accounts=get_accounts(callback.from_user.id)
    if len(accounts)<2:
        await callback.message.answer("Для перевода нужны минимум два счёта."); return
    await state.set_state(TransferMoney.source)
    kb=[[InlineKeyboardButton(text=f"{a['name']} · {money(a['balance'])}",callback_data=f"tf:{a['id']}")] for a in accounts]
    kb.append([InlineKeyboardButton(text="📜 История переводов",callback_data="transfer_history")])
    await callback.message.answer("🔄 <b>ПЕРЕВОД</b>\\n\\nС какого счёта?",parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(TransferMoney.source,F.data.startswith("tf:"))
async def transfer_from(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); aid=int(callback.data.split(":")[1])
    if not get_account(aid,callback.from_user.id):return
    await state.update_data(tf=aid); await state.set_state(TransferMoney.target)
    accounts=[a for a in get_accounts(callback.from_user.id) if a["id"]!=aid]
    kb=[[InlineKeyboardButton(text=f"{a['name']} · {money(a['balance'])}",callback_data=f"tt:{a['id']}")] for a in accounts]
    await callback.message.answer("На какой счёт?",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(TransferMoney.target,F.data.startswith("tt:"))
async def transfer_to(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); aid=int(callback.data.split(":")[1])
    if not get_account(aid,callback.from_user.id):return
    await state.update_data(tt=aid); await state.set_state(TransferMoney.amount)
    await callback.message.answer("💸 Сколько переводим?")

@dp.message(TransferMoney.amount)
async def transfer_sum(message:Message,state:FSMContext):
    amount=parse_money(message.text)
    if amount is None or amount<=0:
        await message.answer("Напиши корректную сумму."); return
    await state.update_data(ta=amount); await state.set_state(TransferMoney.comment)
    await message.answer("💬 Комментарий или пропусти.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить",callback_data="tr_skip")]]))

async def transfer_finish(message,uid,state,comment=None):
    d=await state.get_data()
    add_transfer(uid,d["tf"],d["tt"],d["ta"],comment)
    a=get_account(d["tf"],uid); b=get_account(d["tt"],uid); await state.clear()
    await message.answer(f"✓ <b>ПЕРЕВОД</b>\\n\\n<b>{money(d['ta'])}</b>\\n{a['name']} → {b['name']}\\n\\n"
                         "Он не попал ни в расходы, ни в доходы.",parse_mode="HTML",reply_markup=main_menu())

@dp.message(TransferMoney.comment)
async def transfer_comment(message:Message,state:FSMContext):
    await transfer_finish(message,message.from_user.id,state,message.text.strip() if message.text else None)

@dp.callback_query(TransferMoney.comment,F.data=="tr_skip")
async def transfer_skip(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); await transfer_finish(callback.message,callback.from_user.id,state)

@dp.callback_query(F.data=="transfer_history")
async def transfer_history(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); await state.clear(); rows=get_transfers(callback.from_user.id,20)
    lines=["🔄 <b>ИСТОРИЯ ПЕРЕВОДОВ</b>",""]
    if rows:
        for r in rows:
            lines.append(f"• <b>{money(r['amount'])}</b> · {r['from_account_name']} → {r['to_account_name']}\\n  {r['description'] or 'Без комментария'} · {r['created_at'][:10]}")
    else: lines.append("Переводов пока нет.")
    await callback.message.answer("\\n".join(lines),parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Главная",callback_data="home")]]))


# =========================================================
# MONTHLY PLAN / SAFE TO SPEND
# =========================================================

def _goal_recommendations(goal, monthly_free=None):
    saved=float(goal["saved_amount"] or 0)
    remaining=max(0,float(goal["target_amount"] or 0)-saved)
    if remaining<=0: return 0,0,0
    if goal["target_date"]:
        try:
            target=datetime.strptime(goal["target_date"],"%Y-%m-%d").date()
            today=date.today()
            months=max(1,(target.year-today.year)*12+target.month-today.month+1)
            required=remaining/months
            return required*0.8,required,required*1.2
        except ValueError:
            pass

    free=max(0,float(monthly_free or 0))
    if free<=0: return 0,0,0

    # Адаптивный режим: при небольшом остатке Finly не душит накоплениями.
    if free < 10000:
        rates=(0.05,0.10,0.15)
    elif free < 30000:
        rates=(0.10,0.15,0.25)
    elif free < 60000:
        rates=(0.15,0.25,0.35)
    else:
        rates=(0.20,0.35,0.50)

    vals=[min(remaining,free*r) for r in rates]
    # Маленькие суммы округляем до понятных 100 ₽, но не выше остатка цели.
    vals=[min(remaining,round(v/100)*100) for v in vals]
    return tuple(vals)

def _goal_monthly_amount(goal, monthly_free=None):
    return _goal_recommendations(goal,monthly_free)[1]


def _calendar_events(uid):
    today=date.today(); last=date(today.year,today.month,monthrange(today.year,today.month)[1]); events=[]
    for s in get_income_sources(uid):
        if s["frequency"]=="monthly" and s["day_of_month"]:
            d=date(today.year,today.month,min(int(s["day_of_month"]),last.day))
            if d>=today: events.append((d,"income",float(s["amount"] or 0),s["name"]))
    for x in get_expected_incomes(uid,today.isoformat(),last.isoformat()):
        events.append((datetime.strptime(x["expected_date"],"%Y-%m-%d").date(),"income",float(x["amount"] or 0),x["name"]))
    for p in get_recurring_payments(uid):
        d=date(today.year,today.month,min(int(p["day_of_month"] or 1),last.day))
        if d>=today: events.append((d,"expense",float(p["amount"] or 0),p["name"]))
    for l in get_loans(uid):
        d=date(today.year,today.month,min(int(l["payment_day"] or 1),last.day))
        if d>=today: events.append((d,"expense",float(l["monthly_payment"] or 0),l["name"]))
    return sorted(events,key=lambda x:(x[0],0 if x[1]=="expense" else 1))

def build_money_calendar(uid):
    today=date.today(); accounts=get_accounts(uid)
    spendable=sum(float(a["balance"] or 0) for a in accounts if a["account_type"] not in ("savings","deposit"))
    events=_calendar_events(uid); running=spendable; minimum=running; shortage_date=None
    lines=[f"🗓 <b>КАЛЕНДАРЬ ДЕНЕГ · {today.strftime('%m.%Y')}</b>","",f"💵 Доступно сейчас: <b>{money(spendable)}</b>",""]
    if not events:
        lines.append("До конца месяца запланированных событий нет.")
    for d,kind,amount,name in events:
        running += amount if kind=="income" else -amount
        minimum=min(minimum,running)
        if running<0 and shortage_date is None:
            shortage_date=d
        lines.append(f"{'💰' if kind=='income' else '📤'} {d.strftime('%d.%m')} · {name}: <b>{money(amount)}</b>")
        lines.append(f"   прогноз: {money(running)}")
    lines += ["",f"📉 Минимальный прогнозный остаток: <b>{money(minimum)}</b>"]
    if minimum<0:
        lines.append(f"🚨 <b>Кассовый разрыв: {money(abs(minimum))}</b>")
        if shortage_date: lines.append(f"Деньги могут закончиться примерно <b>{shortage_date.strftime('%d.%m')}</b>.")
        lines.append("В такой ситуации Finly не требует пополнять накопления.")
    elif minimum<3000:
        lines.append("🟡 Запас небольшой. Лучше сохранить его на обязательные и ежедневные расходы.")
    else:
        lines.append("🟢 По запланированным событиям кассового разрыва не видно.")
    lines += ["","ℹ️ Ожидаемый доход не становится реальными деньгами, пока ты не отметишь фактическое поступление."]
    return "\n".join(lines)


@dp.callback_query(F.data=="money_calendar")
async def money_calendar(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.clear()
    await c.message.answer(build_money_calendar(c.from_user.id),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="＋ Ожидаемый доход",callback_data="expected_income_add")],
        [InlineKeyboardButton(text="📋 Ожидания",callback_data="expected_income_list")],
        [InlineKeyboardButton(text="← Главная",callback_data="home")]
    ]))

@dp.callback_query(F.data=="expected_income_add")
async def expected_income_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.clear()
    sources=[s for s in get_income_sources(c.from_user.id) if s["frequency"]!="monthly"]
    kb=[[InlineKeyboardButton(text=f"💰 {s['name']} · {money(s['amount'])}",callback_data=f"expectsrc:{s['id']}")] for s in sources]
    kb.append([InlineKeyboardButton(text="＋ Другой доход",callback_data="expectsrc:other")])
    await state.set_state(ExpectedIncomeFlow.source)
    await c.message.answer("Какой нерегулярный доход ожидаешь?",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(ExpectedIncomeFlow.source,F.data.startswith("expectsrc:"))
async def expected_income_source(c:CallbackQuery,state:FSMContext):
    await c.answer(); value=c.data.split(":")[1]
    if value=="other":
        await state.update_data(source_id=None); await state.set_state(ExpectedIncomeFlow.name); await c.message.answer("Как назвать доход?"); return
    src=get_income_source(int(value),c.from_user.id)
    if not src: await c.message.answer("Источник не найден."); return
    await state.update_data(source_id=src["id"],name=src["name"])
    await state.set_state(ExpectedIncomeFlow.amount); await c.message.answer(f"Сколько ожидаешь? Обычно {money(src['amount'])}")

@dp.message(ExpectedIncomeFlow.name)
async def expected_income_name(m:Message,state:FSMContext):
    name=(m.text or "").strip()
    if len(name)<2: await m.answer("Напиши название."); return
    await state.update_data(name=name); await state.set_state(ExpectedIncomeFlow.amount); await m.answer("Какую сумму ожидаешь?")

@dp.message(ExpectedIncomeFlow.amount)
async def expected_income_amount(m:Message,state:FSMContext):
    v=parse_money(m.text)
    if v is None or v<=0: await m.answer("Напиши сумму больше нуля."); return
    await state.update_data(amount=v); await state.set_state(ExpectedIncomeFlow.expected_date); await m.answer("Когда ожидаешь? ДД.ММ.ГГГГ")

@dp.message(ExpectedIncomeFlow.expected_date)
async def expected_income_date(m:Message,state:FSMContext):
    try:
        d=datetime.strptime((m.text or "").strip(),"%d.%m.%Y").date()
        if d<date.today(): raise ValueError
    except ValueError:
        await m.answer("Нужна сегодняшняя или будущая дата ДД.ММ.ГГГГ."); return
    x=await state.get_data(); add_expected_income(m.from_user.id,x["name"],x["amount"],d.isoformat(),x.get("source_id"))
    await state.clear(); await m.answer("✓ Добавлено в прогноз. Реальный баланс не изменён.",reply_markup=main_menu())

@dp.callback_query(F.data=="expected_income_list")
async def expected_income_list(c:CallbackQuery):
    await c.answer(); rows=get_expected_incomes(c.from_user.id,date.today().isoformat())
    lines=["📋 <b>ОЖИДАЕМЫЕ ДОХОДЫ</b>",""]; kb=[]
    for x in rows:
        lines.append(f"💰 {datetime.strptime(x['expected_date'],'%Y-%m-%d').strftime('%d.%m.%Y')} · <b>{x['name']}</b> · {money(x['amount'])}")
        kb.append([InlineKeyboardButton(text=f"⚙️ {x['name']}",callback_data=f"manageexpect:{x['id']}")])
    if not rows: lines.append("Нет ожидаемых нерегулярных доходов.")
    kb.append([InlineKeyboardButton(text="← Календарь",callback_data="money_calendar")])
    await c.message.answer("\\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("delexpect:"))
async def delete_expected(c:CallbackQuery):
    await c.answer(); delete_expected_income(int(c.data.split(":")[1]),c.from_user.id)
    await c.message.answer("✓ Ожидание удалено.",reply_markup=main_menu())


def get_cashflow_health(uid):
    """Оценивает деньги до ближайшего ожидаемого дохода без учёта накоплений как доступных денег."""
    today=date.today()
    accounts=get_accounts(uid)
    spendable=sum(float(a["balance"] or 0) for a in accounts if a["account_type"] not in ("savings","deposit"))

    events=_calendar_events(uid)
    next_income=None
    for event in events:
        if event[1]=="income":
            next_income=event
            break

    horizon=next_income[0] if next_income else date(today.year,today.month,monthrange(today.year,today.month)[1])
    obligations=0
    first_shortage_date=None
    running=spendable

    # Доход на horizon ещё не считаем деньгами, которыми можно жить ДО его поступления.
    for d,kind,amount,name in events:
        if d>horizon:
            break
        if kind=="expense":
            obligations+=amount
            running-=amount
            if running<0 and first_shortage_date is None:
                first_shortage_date=d
        elif kind=="income" and next_income and d<next_income[0]:
            running+=amount

    safe_until_income=max(0,spendable-obligations)
    days=budget_days({'horizon': horizon, 'next_income': next_income})
    daily=safe_until_income/days
    shortage=max(0,obligations-spendable)

    # Режим определяется не уровнем зарплаты, а запасом относительно обязательств.
    if shortage>0:
        mode="deficit"
    elif safe_until_income < max(3000, obligations*0.15):
        mode="tight"
    else:
        mode="normal"

    return {
        "mode":mode,
        "spendable":spendable,
        "obligations":obligations,
        "safe_until_income":safe_until_income,
        "daily_until_income":daily,
        "next_income":next_income,
        "horizon":horizon,
        "shortage":shortage,
        "first_shortage_date":first_shortage_date,
    }


def build_plan_text(uid):
    now=datetime.now(); today=now.date()
    accounts=get_accounts(uid)
    savings_accounts=[a for a in accounts if a["account_type"] in ("savings","deposit")]
    protected_savings=sum(float(a["balance"] or 0) for a in savings_accounts)
    balance=sum(float(a["balance"] or 0) for a in accounts)
    spendable_balance=balance-protected_savings
    spent=get_month_expense_total(uid,now.year,now.month)
    income=get_month_income_total(uid,now.year,now.month)
    settings=get_plan_settings(uid)
    reserve=float(settings["monthly_reserve"] or 0) if settings else 0
    payments=get_recurring_payments(uid); loans=get_loans(uid); goals=get_goals(uid)
    days_in_month=monthrange(now.year,now.month)[1]
    payment_due=sum(float(x["amount"] or 0) for x in payments if min(int(x["day_of_month"] or 1),days_in_month)>=today.day)
    loan_due=sum(float(x["monthly_payment"] or 0) for x in loans if min(int(x["payment_day"] or 1),days_in_month)>=today.day)

    health=get_cashflow_health(uid)
    base_free=max(0,spendable_balance-reserve-payment_due-loan_due)

    # Если до ближайшего дохода возникает кассовый разрыв, цель сейчас не давит на бюджет.
    goal_due=0
    if health["mode"]!="deficit":
        for g in goals:
            recommended=_goal_monthly_amount(g,base_free)
            if health["mode"]=="tight" and not g["target_date"]:
                recommended*=0.5
            already=0
            if g["account_id"]:
                already=get_month_incoming_transfers_to_account(uid,g["account_id"],now.year,now.month)
            goal_due+=max(0,recommended-already)

    commitments=payment_due+loan_due+goal_due
    available=max(0,spendable_balance-reserve-commitments)
    days_left=max(1,days_in_month-today.day+1)
    month_daily=available/days_left

    # Более безопасный лимит: не больше того, что можно тратить до ближайшего дохода.
    per_day=min(month_daily,health["daily_until_income"])

    status=""
    if health["mode"]=="deficit":
        when=health["first_shortage_date"].strftime("%d.%m") if health["first_shortage_date"] else "до следующего дохода"
        status=(
            f"\n🚨 <b>РЕЖИМ: ДЕНЕГ НЕ ХВАТАЕТ</b>\n"
            f"До {when} может не хватить <b>{money(health['shortage'])}</b>.\n"
            f"🎯 Взнос в накопления сейчас: <b>0 ₽</b>. Сначала закрываем обязательные расходы.\n"
        )
    elif health["mode"]=="tight":
        status=(
            f"\n🟡 <b>РЕЖИМ: ДЕНЬГИ ВПРИТЫК</b>\n"
            f"До ближайшего дохода после обязательств остаётся <b>{money(health['safe_until_income'])}</b>.\n"
            f"Finly снизил необязательные накопления, чтобы не загонять бюджет в минус.\n"
        )
    else:
        status="\n🟢 <b>Финансовый запас нормальный</b>\n"

    if health["next_income"]:
        d,_,amount,name=health["next_income"]
        next_income_text=f"💰 Следующий ожидаемый доход: <b>{money(amount)}</b> · {name} · {d.strftime('%d.%m')}\n"
    else:
        next_income_text="💰 Подтверждённого будущего дохода до конца месяца нет.\n"

    return (
        f"📊 <b>ПЛАН · {now.strftime('%m.%Y')}</b>\n\n"
        f"💳 Всего денег: <b>{money(balance)}</b>\n"
        f"🎯 В накоплениях: <b>{money(protected_savings)}</b>\n"
        f"💵 Для текущих расходов: <b>{money(spendable_balance)}</b>\n"
        f"{next_income_text}"
        f"{status}\n"
        f"📅 Будущие платежи: <b>{money(payment_due)}</b>\n"
        f"🏦 Кредиты: <b>{money(loan_due)}</b>\n"
        f"🎯 Ещё отложить на цели: <b>{money(goal_due)}</b>\n"
        f"🔒 Доп. резерв: <b>{money(reserve)}</b>\n\n"
        f"🟢 Свободно до конца месяца: <b>{money(available)}</b>\n"
        f"🔥 <b>Безопасно в день: {money(per_day)}</b>\n"
        f"<i>Лимит учитывает период до ближайшего ожидаемого дохода.</i>"
    )


@dp.callback_query(F.data == "plan")
async def plan_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        build_plan_text(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Изменить резерв", callback_data="plan_reserve")],
            [InlineKeyboardButton(text="🔄 Обновить расчёт", callback_data="plan")],
            [InlineKeyboardButton(text="← Главная", callback_data="home")]
        ])
    )


@dp.callback_query(F.data == "plan_reserve")
async def plan_reserve(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PlanSettings.reserve)
    await callback.message.answer(
        "🔒 <b>ЗАЩИЩЁННЫЙ РЕЗЕРВ</b>\n\n"
        "Сколько денег из текущего капитала нельзя тратить?\n"
        "Например: <code>128000</code>\n\n"
        "Чтобы убрать резерв, отправь <code>0</code>.",
        parse_mode="HTML"
    )


@dp.message(PlanSettings.reserve)
async def plan_reserve_save(message: Message, state: FSMContext):
    amount = parse_money(message.text)
    if amount is None or amount < 0:
        await message.answer("Напиши сумму 0 или больше.")
        return
    set_monthly_reserve(message.from_user.id, amount)
    await state.clear()
    await message.answer(
        "✓ Резерв сохранён.\n\n" + build_plan_text(message.from_user.id),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Главная", callback_data="home")]
        ])
    )




def _edit_field_keyboard(prefix,item_id,fields,back):
    rows=[[InlineKeyboardButton(text=label,callback_data=f"{prefix}:{item_id}:{field}")] for field,label in fields]
    rows.append([InlineKeyboardButton(text="← Назад",callback_data=back)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query(F.data.startswith("managepay:"))
async def manage_payment(c:CallbackQuery):
    await c.answer(); pid=int(c.data.split(":")[1]); row=next((x for x in get_recurring_payments(c.from_user.id) if x["id"]==pid),None)
    if not row:return
    kb=_edit_field_keyboard("editpay",pid,[("name","✏️ Название"),("amount","💰 Сумма"),("day","📅 День месяца")],"payments")
    kb.inline_keyboard.insert(-1,[InlineKeyboardButton(text="🗑 Удалить",callback_data=f"delpay:{pid}")])
    await c.message.answer(f"📅 <b>{row['name']}</b>\n{money(row['amount'])} · {row['day_of_month']}-го",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("manageloan:"))
async def manage_loan(c:CallbackQuery):
    await c.answer(); lid=int(c.data.split(":")[1]); row=next((x for x in get_loans(c.from_user.id) if x["id"]==lid),None)
    if not row:return
    kb=_edit_field_keyboard("editloan",lid,[("name","✏️ Название"),("remaining","💳 Остаток долга"),("monthly","💰 Платёж"),("day","📅 День платежа"),("rate","％ Ставка")],"loans")
    kb.inline_keyboard.insert(-1,[InlineKeyboardButton(text="🗑 Удалить",callback_data=f"delloan:{lid}")])
    await c.message.answer(f"🏦 <b>{row['name']}</b>\nОстаток {money(row['remaining_amount'])}\nПлатёж {money(row['monthly_payment'])} · {row['payment_day']}-го",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("managegoal:"))
async def manage_goal(c:CallbackQuery):
    await c.answer(); gid=int(c.data.split(":")[1]); row=next((x for x in get_goals(c.from_user.id) if x["id"]==gid),None)
    if not row:return
    kb=_edit_field_keyboard("editgoal",gid,[("name","✏️ Название"),("target","🎯 Сумма цели"),("date","📅 Срок"),("account","🏦 Накопительный счёт")],"goals")
    kb.inline_keyboard.insert(-1,[InlineKeyboardButton(text="🗑 Удалить",callback_data=f"delgoal:{gid}")])
    await c.message.answer(f"🎯 <b>{row['name']}</b>\n{money(row['saved_amount'])} / {money(row['target_amount'])}",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith("manageexpect:"))
async def manage_expect(c:CallbackQuery):
    await c.answer(); eid=int(c.data.split(":")[1]); row=next((x for x in get_expected_incomes(c.from_user.id) if x["id"]==eid),None)
    if not row:return
    kb=_edit_field_keyboard("editexpect",eid,[("name","✏️ Название"),("amount","💰 Сумма"),("date","📅 Дата")],"expected_income_list")
    kb.inline_keyboard.insert(-1,[InlineKeyboardButton(text="🗑 Удалить",callback_data=f"delexpect:{eid}")])
    await c.message.answer(f"💰 <b>{row['name']}</b>\n{money(row['amount'])} · {datetime.strptime(row['expected_date'],'%Y-%m-%d').strftime('%d.%m.%Y')}",parse_mode="HTML",reply_markup=kb)

@dp.callback_query(F.data.startswith(("editpay:","editloan:","editgoal:","editexpect:")))
async def edit_commitment_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); prefix,item_id,field=c.data.split(":")
    if prefix=="editgoal" and field=="account":
        kb=[[InlineKeyboardButton(text=f"🏦 {a['name']} · {money(a['balance'])}",callback_data=f"setgoalacc:{item_id}:{a['id']}")] for a in get_savings_accounts(c.from_user.id)]
        await c.message.answer("Выбери накопительный счёт:",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)); return
    await state.clear(); await state.update_data(edit_kind=prefix,edit_id=int(item_id),edit_field=field); await state.set_state(EditCommitment.value)
    prompts={"name":"Напиши новое название:","amount":"Напиши новую сумму:","day":"Напиши новое число месяца (1–31):",
             "remaining":"Новый остаток долга:","monthly":"Новый ежемесячный платёж:","rate":"Новая процентная ставка:",
             "target":"Новая сумма цели:","date":"Новая дата ДД.ММ.ГГГГ. Для цели можно написать «без срока»:"}
    await c.message.answer(prompts[field])

@dp.callback_query(F.data.startswith("setgoalacc:"))
async def set_goal_account(c:CallbackQuery):
    await c.answer(); _,gid,aid=c.data.split(":")
    update_goal_details(int(gid),c.from_user.id,account_marker=int(aid))
    await c.message.answer("✓ Счёт цели изменён.");

@dp.message(EditCommitment.value)
async def edit_commitment_finish(m:Message,state:FSMContext):
    x=await state.get_data(); kind=x["edit_kind"]; iid=x["edit_id"]; field=x["edit_field"]; raw=(m.text or "").strip()
    try:
        if field=="name":
            if len(raw)<2: raise ValueError
            value=raw
        elif field=="day":
            value=int(raw)
            if not 1<=value<=31: raise ValueError
        elif field=="date":
            if kind=="editgoal" and raw.lower() in ("без срока","нет","-"):
                value=None
            else:
                value=datetime.strptime(raw,"%d.%m.%Y").date()
                if value<date.today(): raise ValueError
                value=value.isoformat()
        else:
            value=parse_money(raw) if field!="rate" else float(raw.replace(",","."))
            if value is None or value<0 or (field in ("amount","monthly","target") and value<=0): raise ValueError
    except ValueError:
        await m.answer("Не получилось распознать значение. Проверь формат и попробуй ещё раз."); return

    if kind=="editpay":
        kw={field:value}; update_recurring_payment(iid,m.from_user.id,**kw)
    elif kind=="editloan":
        kw={field:value}; update_loan_details(iid,m.from_user.id,**kw)
    elif kind=="editgoal":
        if field=="date": update_goal_details(iid,m.from_user.id,target_date_marker=value)
        else: update_goal_details(iid,m.from_user.id,**{field:value})
    elif kind=="editexpect":
        if field=="date": update_expected_income(iid,m.from_user.id,expected_date=value)
        else: update_expected_income(iid,m.from_user.id,**{field:value})
    await state.clear(); await m.answer("✓ Изменение сохранено.",reply_markup=main_menu())




def build_insights_text(uid):
    today=date.today()
    cur_start=today-timedelta(days=6)
    prev_end=cur_start-timedelta(days=1)
    prev_start=prev_end-timedelta(days=6)

    cur=list(get_expense_insights_data(uid,cur_start.isoformat(),today.isoformat()))
    prev=list(get_expense_insights_data(uid,prev_start.isoformat(),prev_end.isoformat()))
    cur_total=sum(float(x["amount"] or 0) for x in cur)
    prev_total=sum(float(x["amount"] or 0) for x in prev)

    lines=["🧠 <b>ИНСАЙТЫ FINLY</b>","",
           f"📆 Последние 7 дней: <b>{money(cur_total)}</b>",
           f"🧾 Операций: <b>{len(cur)}</b>"]

    if len(cur)<3:
        lines += ["","💡 Пока данных мало.","Добавь хотя бы несколько расходов — тогда Finly сможет нормально сравнивать твой темп и категории."]
        return "\n".join(lines)

    if prev_total>0 and len(prev)>=2:
        change=(cur_total-prev_total)/prev_total*100
        if abs(change)<5:
            lines.append("➡️ Темп почти такой же, как за предыдущие 7 дней.")
        elif change>0:
            lines.append(f"📈 Это на <b>{abs(change):.0f}% больше</b>, чем за предыдущие 7 дней.")
        else:
            lines.append(f"📉 Это на <b>{abs(change):.0f}% меньше</b>, чем за предыдущие 7 дней.")
    else:
        lines.append("ℹ️ Для честного сравнения с прошлой неделей данных пока недостаточно.")

    cats={}
    for x in cur:
        cats[x["category_name"]]=cats.get(x["category_name"],0)+float(x["amount"] or 0)
    top=sorted(cats.items(),key=lambda z:z[1],reverse=True)[:3]
    if top:
        lines += ["","<b>Куда ушло больше всего:</b>"]
        for i,(name,amount) in enumerate(top,1):
            share=(amount/cur_total*100) if cur_total else 0
            lines.append(f"{i}. {name}: <b>{money(amount)}</b> · {share:.0f}%")

    avg=cur_total/7
    health=get_cashflow_health(uid)
    if health["next_income"]:
        d,_,income_amount,income_name=health["next_income"]
        days=max(0,(d-today).days)
        projected_spend=avg*days
        after=max(0,health["safe_until_income"]-projected_spend)
        lines += ["",f"🔥 Средний темп: <b>{money(avg)}/день</b>",
                  f"💰 До {income_name} ({d.strftime('%d.%m')}) осталось: <b>{days} дн.</b>"]
        if projected_spend>health["safe_until_income"]:
            gap=projected_spend-health["safe_until_income"]
            lines.append(f"⚠️ При таком темпе до дохода может не хватить примерно <b>{money(gap)}</b>.")
        else:
            lines.append(f"🟢 Если темп сохранится, перед ожидаемым доходом останется около <b>{money(after)}</b>.")
    else:
        dim=monthrange(today.year,today.month)[1]
        days=max(0,dim-today.day)
        projected=avg*days
        lines += ["",f"🔥 Средний темп: <b>{money(avg)}/день</b>",
                  f"📊 При таком темпе до конца месяца ещё уйдёт около <b>{money(projected)}</b>."]

    # One actionable category observation, only with enough previous data.
    if prev_total>0 and len(prev)>=2 and top:
        prev_cats={}
        for x in prev:
            prev_cats[x["category_name"]]=prev_cats.get(x["category_name"],0)+float(x["amount"] or 0)
        name,amount=top[0]; old=prev_cats.get(name,0)
        if old>0 and amount>old*1.25:
            delta=(amount-old)/old*100
            lines += ["",f"🔎 <b>{name}</b> выросли примерно на {delta:.0f}% относительно прошлых 7 дней."]
        elif old==0 and amount>=cur_total*0.35:
            lines += ["",f"🔎 <b>{name}</b> — новая крупная статья этой недели: {money(amount)}."]

    lines += ["","<i>Finly анализирует только записанные фактические расходы. Переводы между своими счетами сюда не входят.</i>"]
    return "\n".join(lines)



def build_monthly_report(uid):
    today=date.today()
    first=today.replace(day=1)
    current=get_monthly_expense_stats(uid,first.isoformat(),today.isoformat())
    current_total=sum(float(r["total"]) for r in current)
    current_count=sum(int(r["n"]) for r in current)
    prior=[]
    for back in range(1,4):
        year=first.year
        month=first.month-back
        while month<=0:
            month+=12; year-=1
        last_day=monthrange(year,month)[1]
        comparable_day=min(today.day,last_day)
        begin=date(year,month,1)
        end=date(year,month,comparable_day)
        rows=get_monthly_expense_stats(uid,begin.isoformat(),end.isoformat())
        total=sum(float(r["total"]) for r in rows)
        n=sum(int(r["n"]) for r in rows)
        if n>=3:
            prior.append((total,n,year,month,comparable_day))
    lines=["📊 <b>МЕСЯЧНЫЙ ОТЧЁТ FINLY</b>","",
           f"📅 {today.strftime('%m.%Y')} · по {today.day}-е число",
           f"💸 Потрачено: <b>{money(current_total)}</b>",
           f"🧾 Операций: <b>{current_count}</b>"]
    if current_count<3:
        lines+=["","Пока слишком мало расходов для надёжного сравнения."]
        return "\\n".join(lines).replace("\\n","\n")
    if prior:
        baseline=sum(v[0] for v in prior)/len(prior)
        delta=current_total-baseline
        lines+=["",f"📈 Обычный расход к этому числу: <b>{money(baseline)}</b>",
                f"📚 Сравнение по {len(prior)} прошлым месяцам"]
        if baseline>0:
            pct=abs(delta)/baseline*100
            if delta>0: lines.append(f"🟠 Сейчас на <b>{money(delta)} ({pct:.0f}%)</b> больше обычного.")
            elif delta<0: lines.append(f"🟢 Сейчас на <b>{money(-delta)} ({pct:.0f}%)</b> меньше обычного.")
            else: lines.append("🟢 Расходы соответствуют обычному уровню.")
    else:
        lines+=["","ℹ️ Для персональной нормы нужны хотя бы 3 операции в одном из предыдущих трёх месяцев."]
    remaining=monthrange(today.year,today.month)[1]-today.day
    avg=current_total/max(1,today.day)
    lines+=["",f"🔥 Темп за месяц: <b>{money(avg)}/день</b>",
            f"🔮 При таком темпе за полный месяц: <b>{money(current_total+avg*remaining)}</b>",
            "<i>Прогноз ориентировочный: учитываются только записанные расходы, а не переводы.</i>"]
    return "\n".join(lines)

@dp.callback_query(F.data=="monthly_report")
async def monthly_report_callback(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.clear()
    await c.message.answer(build_monthly_report(c.from_user.id),parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить",callback_data="monthly_report")],
            [InlineKeyboardButton(text="🧠 Инсайты",callback_data="insights")],
            [InlineKeyboardButton(text="← Главная",callback_data="home")]
        ]))

@dp.callback_query(F.data=="insights")
async def insights_callback(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.clear()
    await c.message.answer(
        build_insights_text(c.from_user.id),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить",callback_data="insights")],
            [InlineKeyboardButton(text="📊 Месячный отчёт",callback_data="monthly_report")],
            [InlineKeyboardButton(text="📊 Все расходы",callback_data="expenses")],
            [InlineKeyboardButton(text="← Главная",callback_data="home")]
        ])
    )



# =========================================================
# PAYMENTS
# =========================================================
@dp.callback_query(F.data=="payments")
async def payments_menu(callback:CallbackQuery,state:FSMContext):
    await callback.answer(); await state.clear(); rows=get_recurring_payments(callback.from_user.id)
    lines=["📅 <b>ОБЯЗАТЕЛЬНЫЕ ПЛАТЕЖИ</b>",""]
    kb=[]
    total=0
    for x in rows:
        total+=float(x["amount"] or 0); lines.append(f"• {x['name']} · <b>{money(x['amount'])}</b> · {x['day_of_month']}-го")
        kb.append([InlineKeyboardButton(text=f"⚙️ {x['name']}",callback_data=f"managepay:{x['id']}")])
    if not rows: lines.append("Пока ничего нет.")
    else: lines += ["",f"Всего в месяц: <b>{money(total)}</b>"]
    kb += [[InlineKeyboardButton(text="＋ Добавить платёж",callback_data="add_payment")],[InlineKeyboardButton(text="← Главная",callback_data="home")]]
    await callback.message.answer("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data=="add_payment")
async def add_payment_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.set_state(AddPayment.name); await c.message.answer("📅 Название платежа? Например: аренда, интернет, подписка")
@dp.message(AddPayment.name)
async def add_payment_name(m:Message,state:FSMContext):
    await state.update_data(name=m.text.strip()); await state.set_state(AddPayment.amount); await m.answer("Сумма платежа?")
@dp.message(AddPayment.amount)
async def add_payment_amount(m:Message,state:FSMContext):
    v=parse_money(m.text)
    if v is None or v<=0: await m.answer("Напиши сумму больше нуля."); return
    await state.update_data(amount=v); await state.set_state(AddPayment.day); await m.answer("Какого числа каждого месяца? От 1 до 31.")
@dp.message(AddPayment.day)
async def add_payment_day(m:Message,state:FSMContext):
    try: day=int(m.text.strip())
    except: day=0
    if not 1<=day<=31: await m.answer("Нужно число от 1 до 31."); return
    d=await state.get_data(); add_recurring_payment(m.from_user.id,d['name'],d['amount'],day); await state.clear(); await m.answer("✓ Платёж добавлен.",reply_markup=main_menu())
@dp.callback_query(F.data.startswith("delpay:"))
async def del_payment(c:CallbackQuery):
    await c.answer(); delete_recurring_payment(int(c.data.split(':')[1]),c.from_user.id); await c.message.answer("✓ Платёж удалён.",reply_markup=main_menu())

# =========================================================
# LOANS
# =========================================================
@dp.callback_query(F.data=="loans")
async def loans_menu(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.clear(); rows=get_loans(c.from_user.id); lines=["🏦 <b>КРЕДИТЫ</b>",""]; kb=[]
    for x in rows:
        lines.append(f"• {x['name']}\n  Остаток: <b>{money(x['remaining_amount'])}</b> · платёж {money(x['monthly_payment'])} · {x['payment_day']}-го · {x['interest_rate'] or 0:g}%")
        kb.append([InlineKeyboardButton(text=f"⚙️ {x['name']}",callback_data=f"manageloan:{x['id']}")])
    if not rows: lines.append("Активных кредитов пока нет.")
    kb += [[InlineKeyboardButton(text="＋ Добавить кредит",callback_data="add_loan")],[InlineKeyboardButton(text="← Главная",callback_data="home")]]
    await c.message.answer("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
@dp.callback_query(F.data=="add_loan")
async def loan_start(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.set_state(AddLoanFlow.name); await c.message.answer("🏦 Название кредита?")
@dp.message(AddLoanFlow.name)
async def loan_name(m:Message,state:FSMContext):
    await state.update_data(name=m.text.strip()); await state.set_state(AddLoanFlow.remaining); await m.answer("Сколько осталось выплатить?")
@dp.message(AddLoanFlow.remaining)
async def loan_remaining(m:Message,state:FSMContext):
    v=parse_money(m.text)
    if v is None or v<0: await m.answer("Напиши корректную сумму."); return
    await state.update_data(remaining=v); await state.set_state(AddLoanFlow.monthly); await m.answer("Ежемесячный платёж?")
@dp.message(AddLoanFlow.monthly)
async def loan_monthly(m:Message,state:FSMContext):
    v=parse_money(m.text)
    if v is None or v<=0: await m.answer("Напиши сумму больше нуля."); return
    await state.update_data(monthly=v); await state.set_state(AddLoanFlow.day); await m.answer("Какого числа платёж? 1–31")
@dp.message(AddLoanFlow.day)
async def loan_day(m:Message,state:FSMContext):
    try: day=int(m.text.strip())
    except: day=0
    if not 1<=day<=31: await m.answer("Нужно число от 1 до 31."); return
    await state.update_data(day=day); await state.set_state(AddLoanFlow.rate); await m.answer("Процентная ставка? Например 19.9. Если не знаешь, отправь 0.")
@dp.message(AddLoanFlow.rate)
async def loan_rate(m:Message,state:FSMContext):
    try: rate=float(m.text.replace(',','.').strip())
    except: rate=-1
    if rate<0: await m.answer("Напиши ставку или 0."); return
    d=await state.get_data(); add_loan(m.from_user.id,d['name'],d['remaining'],d['monthly'],d['day'],rate); await state.clear(); await m.answer("✓ Кредит добавлен и теперь учитывается в плане.",reply_markup=main_menu())
@dp.callback_query(F.data.startswith("delloan:"))
async def del_loan_cb(c:CallbackQuery):
    await c.answer(); delete_loan(int(c.data.split(':')[1]),c.from_user.id); await c.message.answer("✓ Кредит удалён.",reply_markup=main_menu())

# =========================================================
# GOALS
# =========================================================
@dp.callback_query(F.data=="goals")
async def goals_menu(c:CallbackQuery,state:FSMContext):
    await c.answer(); await state.clear()
    rows=get_goals(c.from_user.id); savings=get_savings_accounts(c.from_user.id); now=datetime.now()
    accounts=get_accounts(c.from_user.id)
    protected=sum(float(a["balance"] or 0) for a in accounts if a["account_type"] in ("savings","deposit"))
    spendable=sum(float(a["balance"] or 0) for a in accounts)-protected
    settings=get_plan_settings(c.from_user.id)
    reserve=float(settings["monthly_reserve"] or 0) if settings else 0
    dim=monthrange(now.year,now.month)[1]
    payments=get_recurring_payments(c.from_user.id); loans=get_loans(c.from_user.id)
    payment_due=sum(float(x["amount"] or 0) for x in payments if min(int(x["day_of_month"] or 1),dim)>=now.day)
    loan_due=sum(float(x["monthly_payment"] or 0) for x in loans if min(int(x["payment_day"] or 1),dim)>=now.day)
    monthly_free=max(0,spendable-reserve-payment_due-loan_due)
    lines=["🎯 <b>НАКОПЛЕНИЯ</b>",""]; kb=[]
    if savings:
        lines.append("<b>Накопительные счета:</b>")
        for a in savings:
            bank=f"{a['bank_name']} · " if a["bank_name"] else ""
            lines.append(f"🏦 {bank}<b>{a['name']}</b>: {money(a['balance'])}")
        lines.append("")
    for g in rows:
        saved=float(g["saved_amount"] or 0); target=float(g["target_amount"] or 0)
        left=max(0,target-saved); pct=min(100,saved/target*100) if target else 0
        comfortable,recommended,accelerated=_goal_recommendations(g,monthly_free)
        lines.append(f"• <b>{g['name']}</b>\n  🏦 {g['account_name'] or 'счёт не привязан'}\n  {money(saved)} / {money(target)} · {pct:.0f}%\n  Осталось: {money(left)}")
        if left>0 and g["target_date"]:
            lines.append(f"  📅 Нужно к сроку: <b>{money(recommended)}/мес</b>")
        elif left>0 and recommended>0:
            months=max(1,int((left/recommended)+0.999))
            lines.append(f"  💡 Комфортно: {money(comfortable)}/мес\n  ⭐ Рекомендуется: <b>{money(recommended)}/мес</b>\n  🚀 Ускоренно: {money(accelerated)}/мес\n  При рекомендации: ≈ {months} мес.")
        elif left>0:
            lines.append("  💡 Пока нет свободного бюджета для безопасной рекомендации.")
        if g["account_id"] and left>0:
            already=get_month_incoming_transfers_to_account(c.from_user.id,g["account_id"],now.year,now.month)
            lines.append(f"  ✓ Уже переведено в этом месяце: {money(already)}\n  → Ещё желательно: <b>{money(max(0,recommended-already))}</b>")
        if not g["account_id"]:
            kb.append([InlineKeyboardButton(text=f"🔗 Привязать счёт · {g['name']}",callback_data=f"linkgoal:{g['id']}")])
        kb.append([InlineKeyboardButton(text=f"⚙️ {g['name']}",callback_data=f"managegoal:{g['id']}")])
    if not rows: lines.append("Целей пока нет.")
    kb += [[InlineKeyboardButton(text="＋ Добавить цель",callback_data="add_goal")],[InlineKeyboardButton(text="← Главная",callback_data="home")]]
    await c.message.answer("\n".join(lines),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data=="add_goal")
async def goal_start(c:CallbackQuery,state:FSMContext):
    await c.answer()
    await state.clear()
    savings=get_savings_accounts(c.from_user.id)
    if not savings:
        await c.message.answer(
            "Сначала создай накопительный счёт: ⚙️ Управление → 💳 Счета → ＋ Добавить счёт → 🏦 Накопительный счёт.",
            reply_markup=main_menu()
        )
        return
    await state.set_state(AddGoalFlow.name)
    await c.message.answer("🎯 Название цели? Например: отпуск, машина, подушка")


@dp.message(AddGoalFlow.name)
async def goal_name(m:Message,state:FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(AddGoalFlow.target)
    await m.answer("Сколько нужно накопить всего?")


@dp.message(AddGoalFlow.target)
async def goal_target(m:Message,state:FSMContext):
    v=parse_money(m.text)
    if v is None or v<=0:
        await m.answer("Напиши сумму больше нуля.")
        return
    await state.update_data(target=v)
    savings=get_savings_accounts(m.from_user.id)
    await state.set_state(AddGoalFlow.account)
    kb=[[InlineKeyboardButton(
        text=f"🏦 {a['name']} · {money(a['balance'])}",
        callback_data=f"goalaccount:{a['id']}"
    )] for a in savings]
    await m.answer(
        "К какому накопительному счёту привязать цель?\n\n"
        "Текущий баланс этого счёта будет считаться суммой «накоплено».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@dp.callback_query(AddGoalFlow.account,F.data.startswith("goalaccount:"))
async def goal_account(c:CallbackQuery,state:FSMContext):
    await c.answer()
    aid=int(c.data.split(":")[1])
    savings=get_savings_accounts(c.from_user.id)
    if not any(a["id"]==aid for a in savings):
        await c.message.answer("Накопительный счёт не найден.")
        return
    await state.update_data(account_id=aid)
    await state.set_state(AddGoalFlow.target_date)
    await c.message.answer("К какой дате хочешь накопить? Формат ДД.ММ.ГГГГ. Если срока нет, отправь 0.")


@dp.message(AddGoalFlow.target_date)
async def goal_date(m:Message,state:FSMContext):
    raw=m.text.strip()
    iso=None
    if raw!="0":
        try:
            dt=datetime.strptime(raw,"%d.%m.%Y").date()
            if dt<date.today():
                raise ValueError
            iso=dt.isoformat()
        except:
            await m.answer("Дата должна быть будущей в формате ДД.ММ.ГГГГ, либо 0.")
            return
    d=await state.get_data()
    add_goal(m.from_user.id,d["name"],d["target"],0,iso,d["account_id"])
    await state.clear()
    await m.answer("✓ Цель добавлена. Сумма накоплений берётся из баланса выбранного счёта.",reply_markup=main_menu())


@dp.callback_query(F.data.startswith("linkgoal:"))
async def link_old_goal(c:CallbackQuery):
    await c.answer()
    gid=int(c.data.split(":")[1])
    savings=get_savings_accounts(c.from_user.id)
    if not savings:
        await c.message.answer("Сначала создай накопительный счёт.")
        return
    kb=[[InlineKeyboardButton(
        text=f"🏦 {a['name']} · {money(a['balance'])}",
        callback_data=f"linkgoalaccount:{gid}:{a['id']}"
    )] for a in savings]
    await c.message.answer("Выбери счёт, баланс которого будет использовать эта цель:",reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@dp.callback_query(F.data.startswith("linkgoalaccount:"))
async def link_old_goal_account(c:CallbackQuery):
    await c.answer()
    _,gid,aid=c.data.split(":")
    ok=link_goal_to_account(int(gid),c.from_user.id,int(aid))
    await c.message.answer("✓ Цель привязана к реальному накопительному счёту." if ok else "Не удалось привязать счёт.",reply_markup=main_menu())


@dp.callback_query(F.data.startswith("delgoal:"))
async def del_goal_cb(c:CallbackQuery):
    await c.answer()
    delete_goal(int(c.data.split(":")[1]),c.from_user.id)
    await c.message.answer("✓ Цель удалена. Сам накопительный счёт и деньги на нём не удалены.",reply_markup=main_menu())



# =========================================================
# PLACEHOLDERS
# =========================================================

@dp.callback_query(
    F.data.in_({"__unused_placeholder__"})
)
async def placeholder(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🚧 <b>Раздел уже готовим</b>\n\n"
        "Расходы уже работают. Следом подключим доходы, переводы, платежи, цели и план.",
        parse_mode="HTML"
    )


# =========================================================
# BOT START
# =========================================================

async def main():

    create_database()

    me = await bot.get_me()

    print()
    print("================================")
    print("          FINLY ONLINE")
    print(f"          @{me.username}")
    print("================================")
    print()

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
