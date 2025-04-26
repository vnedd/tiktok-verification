import imaplib
import email
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")
IMAP_SERVER = "imap.gmail.com"

CHOOSE_SOURCE, ENTER_EMAIL = range(2)

# --- Common OTP Fetch Function --- #
def get_latest_code(from_email, target_email):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, APP_PASSWORD)
        mail.select("inbox")

        date_since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(FROM "{from_email}" SINCE {date_since})')

        messages = messages[0].split()[::-1]  # Latest first
        for num in messages:
            typ, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Check subject or 'To' contains target email
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

# --- Conversation Handlers --- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📲 Bạn muốn lấy mã xác minh từ nguồn nào?\n"
        "Nhập một trong hai:\n"
        "`tiktok` hoặc `microsoft`"
    )
    return CHOOSE_SOURCE

async def choose_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.message.text.strip().lower()
    if source not in ("tiktok", "microsoft"):
        await update.message.reply_text("⚠️ Vui lòng chỉ nhập `tiktok` hoặc `microsoft`.")
        return CHOOSE_SOURCE

    context.user_data["source"] = source
    await update.message.reply_text("📧 Nhập địa chỉ email bạn muốn kiểm tra:")
    return ENTER_EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = update.message.text.strip()
    source = context.user_data.get("source")
    await update.message.reply_text("🔍 Đang kiểm tra hộp thư...")

    if source == "tiktok":
        sender = "register@account.tiktok.com"
    else:
        sender = "account-security-noreply@accountprotection.microsoft.com"

    code = get_latest_code(sender, email_input)
    await update.message.reply_text(f"📨 Mã {source.title()} gần nhất: {code}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy thao tác.")
    return ConversationHandler.END

# --- MAIN --- #
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_source)],
            ENTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("🤖 Bot đang chạy...")
    app.run_polling()
