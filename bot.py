import imaplib
import email
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")
# --- CONFIG EMAIL --- #

IMAP_SERVER = "imap.gmail.com"

# --- FUNCTION TO GET OTP --- #
def get_latest_tiktok_code(target_email):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, APP_PASSWORD)
        mail.select("inbox")

        # Only fetch from TikTok and recent (2 days)
        date_since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(FROM "register@account.tiktok.com" SINCE {date_since})')

        messages = messages[0].split()[::-1]  # Latest first
        for num in messages:
            typ, data = mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Check subject contains the target email
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
        return "Không tìm thấy mã TikTok gần đây!"
    except Exception as e:
        return f"Lỗi: {str(e)}"

# --- TELEGRAM BOT --- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập địa chỉ email bạn muốn lấy mã TikTok:")

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = update.message.text.strip()
    await update.message.reply_text("Đang tìm mã xác minh...")
    code = get_latest_tiktok_code(email_input)
    await update.message.reply_text(f"Mã TikTok gần nhất: {code}")

# --- MAIN --- #
if __name__ == "__main__":

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_email))

    print("Bot đang chạy...")
    app.run_polling()
