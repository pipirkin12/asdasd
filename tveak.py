import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# === ТВОИ ДАННЫЕ ===
TOKEN = "8534564349:AAEFCXWCqRrAk3ZlSptG2OIwcB_FjdUE3HY"
OWNER_ID = 6411412302

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

pending_replies: dict[int, int] = {}

# ============= БАЗА ДАННЫХ =============
conn = sqlite3.connect("messages.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    content TEXT,
    type TEXT,
    date TEXT
)
""")
conn.commit()


def save_message(user_id, username, content, msg_type):
    date_str = datetime.now().strftime("%m.%d.%y %H:%M")
    cursor.execute(
        "INSERT INTO messages (user_id, username, content, type, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, content, msg_type, date_str)
    )
    conn.commit()


# ===========================================================
# ============= ЛОГИКА ОТВЕТА ВЛАДЕЛЬЦА ======================
# ===========================================================

@dp.message(F.text & (F.from_user.id == OWNER_ID))
async def owner_reply(msg: Message):
    """Ответ владельца пользователю."""
    if OWNER_ID not in pending_replies:
        await msg.answer("❗ Нет активного диалога для ответа.")
        return

    target = pending_replies.pop(OWNER_ID)

    # формируем цитату
    quoted = f"<blockquote>{msg.text}</blockquote>"

    text_formatted = (
        f"💬 Сообщение от владельца"
        f"{quoted}\n\n"
    )

    # кнопка "Ответить"
    kb = InlineKeyboardBuilder()
    kb.button(text="Ответить", callback_data=f"reply:{target}:0")

    # отправляем пользователю
    await bot.send_message(
        target,
        text_formatted,
        reply_markup=kb.as_markup()
    )

    # подтверждение владельцу
    await msg.answer("✔️ Отправлено пользователю!")

    save_message(OWNER_ID, "OWNER", msg.text, "owner_reply")


# ===========================================================
# ============= START =======================================
# ===========================================================

@dp.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "Напиши сообщение, и оно сразу же передасться мне!"
    )


# ===========================================================
# ============= ОБРАБОТКА ВСЕХ ВХОДЯЩИХ =====================
# ===========================================================

@dp.message(F)
async def user_message(msg: Message):
    if msg.from_user.id == OWNER_ID:
        return  # владелец сам себе не пишет

    uid = msg.from_user.id
    uname = msg.from_user.username or "Без_юзера"
    date_str = datetime.now().strftime("%m.%d.%y %H:%M")

    kb = InlineKeyboardBuilder()
    kb.button(text="Ответить", callback_data=f"reply:{uid}:{msg.message_id}")

    # ============= TEXT =================
    if msg.text:
        quoted = f"<blockquote>{msg.text}</blockquote>"

        formatted = (
            f"{quoted}\n\n"
            f"ℹ️ Юз пользователя: @{uname}\n"
            f"📅 Дата: {date_str}"
        )

        await bot.send_message(OWNER_ID, formatted, reply_markup=kb.as_markup())
        await bot.send_message(uid, "💜 Ваше сообщение отправлено! Ответ придёт либо в бота, либо напрямую в личные сообщения")

        save_message(uid, uname, msg.text, "text")
        return

    # ============= PHOTO =================
    if msg.photo:
        caption = msg.caption or "<Без подписи>"

        await bot.send_photo(
            OWNER_ID,
            msg.photo[-1].file_id,
            caption=(
                f"<blockquote>{caption}</blockquote>\n\n"
                f"ℹ️ Юз пользователя: @{uname}\n"
                f"📅 Дата: {date_str}"
            ),
            reply_markup=kb.as_markup()
        )

        await bot.send_message(uid, "💜 Фото отправлено владельцу!")
        save_message(uid, uname, caption, "photo")
        return

    # ============= DOCUMENT =================
    if msg.document:
        caption = msg.caption or "<Документ>"

        await bot.send_document(
            OWNER_ID,
            msg.document.file_id,
            caption=(
                f"<blockquote>{caption}</blockquote>\n\n"
                f"ℹ️ Юз пользователя: @{uname}\n"
                f"📅 Дата: {date_str}"
            ),
            reply_markup=kb.as_markup()
        )

        await bot.send_message(uid, "💜 Документ отправлен владельцу!")
        save_message(uid, uname, caption, "document")
        return

    # ============= VOICE =================
    if msg.voice:
        await bot.send_voice(
            OWNER_ID,
            msg.voice.file_id,
            caption=(
                f"<blockquote>Голосовое сообщение</blockquote>\n\n"
                f"ℹ️ Юз пользователя: @{uname}\n"
                f"📅 Дата: {date_str}"
            ),
            reply_markup=kb.as_markup()
        )

        await bot.send_message(uid, "💜 Голосовое отправлено владельцу!")
        save_message(uid, uname, "[voice]", "voice")
        return


# ===========================================================
# ============= ОБРАБОТКА КНОПКИ "ОТВЕТИТЬ" =================
# ===========================================================

@dp.callback_query(F.data.startswith("reply:"))
async def reply_click(cb: CallbackQuery):
    _, uid, _ = cb.data.split(":")
    uid = int(uid)

    pending_replies[OWNER_ID] = uid
    await cb.message.answer(f"✏️ Напиши ответ, и я отправлю его!")

    await cb.answer("Ожидаю ваш ответ…")


# ===========================================================
# ============= RUN =========================================
# ===========================================================

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
