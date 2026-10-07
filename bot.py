import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_PATH = os.environ.get("DB_PATH", "bot.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        balance REAL NOT NULL DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'available'
    )""")
    conn.commit()
    return conn

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db().close()
    keyboard = [
        [InlineKeyboardButton("📦 GET NUMBER", callback_data="get")],
        [InlineKeyboardButton("🔎 SEARCH NUMBER", callback_data="search")],
        [InlineKeyboardButton("💰 BALANCE", callback_data="balance")],
        [InlineKeyboardButton("👥 REFER", callback_data="refer")],
        [InlineKeyboardButton("💵 WITHDRAWAL", callback_data="withdraw")],
        [InlineKeyboardButton("🆘 SUPPORT", callback_data="support")],
    ]
    await update.message.reply_text(
        "👋 Welcome!\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "balance":
        conn = db()
        row = conn.execute("SELECT balance FROM users WHERE user_id=?", (q.from_user.id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO users(user_id) VALUES(?)", (q.from_user.id,))
            conn.commit()
            balance = 0
        else:
            balance = row[0]
        conn.close()
        await q.message.reply_text(f"💰 Your balance: {balance:.2f}")
    elif q.data == "get":
        await q.message.reply_text(
            "📦 Number inventory is currently managed by the administrator.\n"
            "Only authorized numbers may be added."
        )
    elif q.data == "search":
        await q.message.reply_text("🔎 Send /search <label> to search the authorized inventory.")
    elif q.data == "refer":
        await q.message.reply_text("👥 Referral system can be configured by the administrator.")
    elif q.data == "withdraw":
        await q.message.reply_text("💵 Withdrawal requests are handled by the administrator.")
    elif q.data == "support":
        await q.message.reply_text("🆘 Please contact the administrator for support.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    term = " ".join(context.args).strip()
    if not term:
        await update.message.reply_text("Usage: /search <label>")
        return
    conn = db()
    rows = conn.execute(
        "SELECT label, status FROM inventory WHERE label LIKE ? LIMIT 10",
        (f"%{term}%",)
    ).fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("No matching authorized inventory found.")
        return
    text = "\n".join(f"• {label} — {status}" for label, status in rows)
    await update.message.reply_text(text)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    await update.message.reply_text(
        "🛠 Admin commands:\n"
        "/additem <label>\n"
        "/delitem <id>\n"
        "/setbalance <user_id> <amount>\n"
        "/listitems"
    )

async def additem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    label = " ".join(context.args).strip()
    if not label:
        await update.message.reply_text("Usage: /additem <authorized inventory label>")
        return
    conn = db()
    conn.execute("INSERT INTO inventory(label) VALUES(?)", (label,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Inventory item added.")

async def delitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /delitem <id>")
        return
    conn = db()
    conn.execute("DELETE FROM inventory WHERE id=?", (int(context.args[0]),))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Inventory item removed.")

async def setbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setbalance <user_id> <amount>")
        return
    user_id, amount = int(context.args[0]), float(context.args[1])
    conn = db()
    conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Balance updated.")

async def listitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    conn = db()
    rows = conn.execute("SELECT id, label, status FROM inventory ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Inventory is empty.")
        return
    await update.message.reply_text("\n".join(f"{i}. {label} — {status}" for i, label, status in rows))

def main():
    db().close()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("additem", additem))
    app.add_handler(CommandHandler("delitem", delitem))
    app.add_handler(CommandHandler("setbalance", setbalance))
    app.add_handler(CommandHandler("listitems", listitems))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
