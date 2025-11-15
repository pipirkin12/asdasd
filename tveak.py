import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties


# ===================== НАСТРОЙКИ =====================
TOKEN = "8534564349:AAEFCXWCqRrAk3ZlSptG2OIwcB_FjdUE3HY"
OWNER_ID = 6411412302

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

pending_replies: dict[int, int] = {}

# ===================== БАЗА ДАННЫХ =====================
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS blocked_users (
    user_id INTEGER PRIMARY KEY
)
""")

conn.commit()


# ---------- функции работы с БД ----------
def save_message(user_id, username, content, msg_type):
    date_str = datetime.now().strftime("%m.%d.%y %H:%M")
    cursor.execute(
        "INSERT INTO messages (user_id, username, content, type, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, content, msg_type, date_str)
    )
    conn.commit()


def block_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
    conn.commit()


def unblock_user(user_id: int):
    cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
    conn.commit()


def is_blocked(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None


# ===================== /block =====================
@dp.message(F.text & F.from_user.id == OWNER_ID & F.reply_to_message)
async def block_command(msg: Message):
    if msg.text.strip() != "/block":
        return

    target = msg.reply_to_message.from_user.id
    block_user(target)

    await msg.answer(f"🚫 Пользователь {target} заблокирован.")
    await bot.send_message(target, "🚫 Вы заблокированы в этом ботe.")


# ===================== /unblock =====================
@dp.message(F.text & F.from_user.id == OWNER_ID & F.reply_to_message)
async def unblock_command(msg: Message):
    if msg.text.strip() != "/unblock":
        return

    target = msg.reply_to_message.from_user.id
    unblock_user(target)

    await msg.answer(f"♻️ Пользователь {target} разблокирован.")
    await bot.send_message(target, "♻️ Вы были разблокированы.")


# ===================== /banlist =====================
@dp.message(F.text & (F.from_user.id == OWNER_ID))
async def banlist(msg: Message):
    if msg.text.strip() != "/banlist":
        return

    cursor.execute("SELECT user_id FROM blocked_users")
    rows = cursor.fetchall()

    if not rows:
        return await msg.answer("🟢 Список заблокированных пуст.")

    text = "🚫 <b>Заблокированные пользователи:</b>\n\n"
    for (uid,) in rows:
        text += f"• <code>{uid}</code>\n"

    await msg.answer(text)


# ===================== ОТВЕТ ВЛАДЕЛЬЦА =====================
@dp.message(F.text & (F.from_user.id == OWNER_ID))
async def owner_reply(msg: Message):
    if OWNER_ID not in pending_replies:
        return await msg.answer("❗ Нет активного диалога.")

    target = pending_replies.pop(OWNER_ID)
    quoted = f"<blockquote>{msg.text}</blockquote>"

    text = (
        f"💬 <b>Ответ от владельца:</b>\n"
        f"{quoted}"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="Ответить", callback_data=f"reply:{target}:0")

    await bot.send_message(target, text, reply_markup=kb.as_markup())
    await msg.answer("✔️ Отправлено.")

    save_message(OWNER_ID, "OWNER", msg.text, "owner_reply")


# ===================== /start =====================
@dp.message(CommandStart())
async def start_cmd(msg: Message):
    if is_blocked(msg.from_user.id):
        return await msg.answer("🚫 Вы заблокированы в этом боте.")

    await msg.answer(
        "💜 Привет! Напиши своё сообщение — я передам его владельцу.\n"
        "Ответ придёт сюда."
    )


# ===================== ОБРАБОТКА ЛЮБОГО СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ =====================
@dp.message(F)
async def user_message(msg: Message):
    if msg.from_user.id == OWNER_ID:
        return

    if is_blocked(msg.from_user.id):
        return await msg.answer("🚫 Вы заблокированы в этом боте.")

    uid = msg.from_user.id
    uname = msg.from_user.username or "Без_юзера"
    date = datetime.now().strftime("%m.%d.%y %H:%M")

    kb = InlineKeyboardBuilder()
    kb.button(text="Ответить", callback_data=f"reply:{uid}:{msg.message_id}")

    # --- TEXT ---
    if msg.text:
        quoted = f"<blockquote>{msg.text}</blockquote>"

        formatted = (
            f"{quoted}\n\n"
            f"ℹ️ От: @{uname}\n"
            f"📅 {date}"
        )

        await bot.send_message(OWNER_ID, formatted, reply_markup=kb.as_markup())
        await bot.send_message(uid, "💜 Ваше сообщение отправлено! Ответ придёт сюда.")

        save_message(uid, uname, msg.text, "text")
        return

    # --- PHOTO ---
    if msg.photo:
        caption = msg.caption or "<Фото без подписи>"

        await bot.send_photo(
            OWNER_ID,
            msg.photo[-1].file_id,
            caption=f"<blockquote>{caption}</blockquote>\n\nℹ️ От: @{uname}\n📅 {date}",
            reply_markup=kb.as_markup()
        )
        await bot.send_message(uid, "💜 Фото отправлено.")

        save_message(uid, uname, caption, "photo")
        return

    # --- DOCUMENT ---
    if msg.document:
        caption = msg.caption or "<Документ>"

        await bot.send_document(
            OWNER_ID,
            msg.document.file_id,
            caption=f"<blockquote>{caption}</blockquote>\n\nℹ️ От: @{uname}\n📅 {date}",
            reply_markup=kb.as_markup()
        )
        await bot.send_message(uid, "💜 Документ отправлен.")

        save_message(uid, uname, caption, "document")
        return

    # --- VOICE ---
    if msg.voice:
        await bot.send_voice(
            OWNER_ID,
            msg.voice.file_id,
            caption=f"<blockquote>Голосовое сообщение</blockquote>\n\nℹ️ От: @{uname}\n📅 {date}",
            reply_markup=kb.as_markup()
        )
        await bot.send_message(uid, "💜 Голосовое отправлено.")

        save_message(uid, uname, "[voice]", "voice")
        return


# ===================== CALLBACK: Ответить =====================
@dp.callback_query(F.data.startswith("reply:"))
async def reply_click(cb: CallbackQuery):
    _, uid, _ = cb.data.split(":")
    uid = int(uid)

    pending_replies[OWNER_ID] = uid

    await cb.message.answer(f"✏️ Напиши сообщение — я отправлю его пользователю <code>{uid}</code>.")
    await cb.answer("Жду текст…")


# ===================== RUN =====================
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
