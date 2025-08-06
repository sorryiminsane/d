import logging
import os
import time
import asyncio
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Replace this with your actual Telegram bot token
TOKEN = '7325454393:AAHUZ4ZnNsRn1B4c6yZvK-_9lwipj7tudmU'

# Replace this with your actual Telegram group chat ID
GROUP_CHAT_ID = '-4522538800'  # Keep the '-' in the ID

# Correct log file path (using raw string to avoid backslash issues)
log_file_path = r"C:\Users\pc\Desktop\axd\bot_logs.log"

# Telegram Bot instance
bot = Bot(token=TOKEN)

# Set up logging for debugging purposes
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Add this function to get the group chat ID
async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns the group chat ID."""
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text(f"This group's chat ID is: {chat_id}")
    else:
        await update.message.reply_text("This command only works in a group or supergroup.")


def create_bot_app():
    """Creates the bot application."""
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('get_group_id', get_group_id))
    return application


async def poll_log_file(log_file_path, interval=2):
    """Periodically polls the log file for new content."""
    logging.debug("Starting log file polling...")
    log_size = os.path.getsize(log_file_path)
    logging.debug(f"Initial log file size: {log_size}")

    while True:
        await asyncio.sleep(interval)  # Wait for the interval (e.g., 2 seconds)

        current_size = os.path.getsize(log_file_path)
        if current_size > log_size:
            logging.debug(f"Log file {log_file_path} has new data")
            with open(log_file_path, 'r', encoding='utf-8') as log_file:
                log_file.seek(log_size)  # Move to the last known position
                new_lines = log_file.readlines()  # Read any new lines

                if new_lines:
                    logging.debug(f"New lines detected: {new_lines}")
                    for line in new_lines:
                        # Send each new line to the Telegram group asynchronously
                        try:
                            logging.debug(f"Sending line to group {GROUP_CHAT_ID}: {line}")
                            await bot.send_message(chat_id=GROUP_CHAT_ID, text=line)
                        except Exception as e:
                            logging.error(f"Error sending message: {e}")
                else:
                    logging.debug("No new lines found.")

            # Update the log file size to the new end of the file
            log_size = current_size
            logging.debug(f"Updated log file size: {log_size}")
        else:
            logging.debug("No change in log file size.")


async def run_bot_and_log_monitor():
    """Runs the Telegram bot and log monitoring concurrently."""
    bot_app = create_bot_app()

    # Create a task for monitoring log files with polling (check for changes every 2 seconds)
    log_monitor_task = asyncio.create_task(poll_log_file(log_file_path, interval=2))

    # Start the bot and ensure proper initialization/shutdown
    await bot_app.initialize()
    bot_polling_task = asyncio.create_task(bot_app.start())
    await asyncio.gather(log_monitor_task, bot_polling_task)
    await bot_app.shutdown()


if __name__ == '__main__':
    try:
        asyncio.run(run_bot_and_log_monitor())
    except RuntimeError as e:
        if "This event loop is already running" in str(e):
            asyncio.create_task(run_bot_and_log_monitor())
