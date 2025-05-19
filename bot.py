import imaplib
import email
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")
IMAP_SERVER = "imap.gmail.com"

CHOOSE_SOURCE, ENTER_EMAIL = range(2)

# --- OTP Fetch Function --- #
def get_latest_code(from_email, target_email):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, APP_PASSWORD)
        mail.select("inbox")

        date_since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(FROM "{from_email}" SINCE {date_since})')

        messages = messages[0].split()[::-1]
        for num in messages:
            typ, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            if target_email.lower() not in msg['To'].lower():
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode(errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            match = re.search(r"\b(\d{6})\b", body)
            if match:
                return match.group(1)
        return "❌ Không tìm thấy mã gần đây!"
    except Exception as e:
        return f"⚠️ Lỗi: {str(e)}"

# --- Inline Button Keyboard --- #
def get_source_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 TikTok", callback_data="tiktok")],
        [InlineKeyboardButton("🔁 Microsoft", callback_data="microsoft")]
    ])

# --- Handlers --- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📲 Chọn nguồn bạn muốn lấy mã:",
        reply_markup=get_source_keyboard()
    )
    return CHOOSE_SOURCE

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    source = query.data
    context.user_data["source"] = source
    await query.edit_message_text(f"📧 Nhập địa chỉ email để lấy mã {source.title()}:")
    return ENTER_EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = update.message.text.strip()
    source = context.user_data.get("source")

    await update.message.reply_text("🔍 Đang kiểm tra hộp thư...")

    sender = "register@account.tiktok.com" if source == "tiktok" else "account-security-noreply@accountprotection.microsoft.com"
    code = get_latest_code(sender, email_input)

    await update.message.reply_text(
        f"✅ Mã {source.title()} gần nhất: {code}",
        reply_markup=get_source_keyboard()
    )
    return CHOOSE_SOURCE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy thao tác.")
    return ConversationHandler.END

# --- Main --- #
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_SOURCE: [CallbackQueryHandler(button_handler)],
            ENTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True,
    )

    app.add_handler(conv_handler)
    print("🤖 Bot đang chạy...")
    app.run_polling()
