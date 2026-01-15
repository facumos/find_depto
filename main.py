import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from scrappers.argenprop import scrape_argenprop
from filters import matches
from notifier import send_message
from storage import load_sent, save_sent
from user_config import get_user_config, set_user_config, get_all_user_ids, DEFAULT_CONFIG
from dotenv import load_dotenv

load_dotenv()

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8515341054:AAGLbPYICYimfzknKl5MaC8QdmfwvevCaXs")

# Conversation states
CHOOSING, SET_MAX_PRICE, SET_MIN_ROOMS, SET_MAX_EXPENSAS = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show welcome and prompt configuration."""
    user_id = update.effective_user.id
    config = get_user_config(user_id)

    await update.message.reply_text(
        "🏠 <b>Bienvenido al Bot de Departamentos!</b>\n\n"
        "Te notificaré cuando encuentre departamentos que coincidan con tus criterios.\n\n"
        f"<b>Tu configuración actual:</b>\n"
        f"💲 Precio máximo: ${config['max_price']:,}\n"
        f"🛏 Ambientes mínimos: {config['min_rooms']}\n"
        f"🧾 Expensas máximas: ${config['max_expensas']:,}\n\n"
        "Usa /config para modificar tus filtros.",
        parse_mode="HTML"
    )

    # Register this user for notifications
    set_user_config(user_id, "active", True)


async def config_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /config command - start configuration conversation."""
    keyboard = [
        ["💲 Precio máximo", "🛏 Ambientes mínimos"],
        ["🧾 Expensas máximas", "✅ Listo"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    user_id = update.effective_user.id
    config = get_user_config(user_id)

    await update.message.reply_text(
        "<b>⚙️ Configuración</b>\n\n"
        f"<b>Valores actuales:</b>\n"
        f"💲 Precio máximo: ${config['max_price']:,}\n"
        f"🛏 Ambientes mínimos: {config['min_rooms']}\n"
        f"🧾 Expensas máximas: ${config['max_expensas']:,}\n\n"
        "¿Qué deseas modificar?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return CHOOSING


async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu choice."""
    text = update.message.text

    if "Precio máximo" in text:
        await update.message.reply_text(
            "💲 Ingresa el <b>precio máximo</b> de alquiler (solo números):\n"
            "Ejemplo: 500000",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        return SET_MAX_PRICE

    elif "Ambientes mínimos" in text:
        await update.message.reply_text(
            "🛏 Ingresa la cantidad <b>mínima de ambientes</b> (solo números):\n"
            "Ejemplo: 2",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        return SET_MIN_ROOMS

    elif "Expensas máximas" in text:
        await update.message.reply_text(
            "🧾 Ingresa el monto <b>máximo de expensas</b> (solo números):\n"
            "Ejemplo: 50000",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        return SET_MAX_EXPENSAS

    elif "Listo" in text:
        return await config_done(update, context)

    return CHOOSING


async def set_max_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set max_price value."""
    try:
        value = int(update.message.text.replace(".", "").replace(",", ""))
        if value <= 0:
            raise ValueError("Must be positive")

        user_id = update.effective_user.id
        set_user_config(user_id, "max_price", value)

        await update.message.reply_text(
            f"✅ Precio máximo actualizado a <b>${value:,}</b>",
            parse_mode="HTML"
        )
        return await show_config_menu(update, context)

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un número válido mayor a 0.\n"
            "Ejemplo: 500000"
        )
        return SET_MAX_PRICE


async def set_min_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set min_rooms value."""
    try:
        value = int(update.message.text)
        if value <= 0:
            raise ValueError("Must be positive")

        user_id = update.effective_user.id
        set_user_config(user_id, "min_rooms", value)

        await update.message.reply_text(
            f"✅ Ambientes mínimos actualizado a <b>{value}</b>",
            parse_mode="HTML"
        )
        return await show_config_menu(update, context)

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un número válido mayor a 0.\n"
            "Ejemplo: 2"
        )
        return SET_MIN_ROOMS


async def set_max_expensas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set max_expensas value."""
    try:
        value = int(update.message.text.replace(".", "").replace(",", ""))
        if value <= 0:
            raise ValueError("Must be positive")

        user_id = update.effective_user.id
        set_user_config(user_id, "max_expensas", value)

        await update.message.reply_text(
            f"✅ Expensas máximas actualizado a <b>${value:,}</b>",
            parse_mode="HTML"
        )
        return await show_config_menu(update, context)

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor ingresa un número válido mayor a 0.\n"
            "Ejemplo: 50000"
        )
        return SET_MAX_EXPENSAS


async def show_config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the configuration menu again."""
    keyboard = [
        ["💲 Precio máximo", "🛏 Ambientes mínimos"],
        ["🧾 Expensas máximas", "✅ Listo"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    user_id = update.effective_user.id
    config = get_user_config(user_id)

    await update.message.reply_text(
        f"<b>Valores actuales:</b>\n"
        f"💲 Precio máximo: ${config['max_price']:,}\n"
        f"🛏 Ambientes mínimos: {config['min_rooms']}\n"
        f"🧾 Expensas máximas: ${config['max_expensas']:,}\n\n"
        "¿Qué más deseas modificar?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return CHOOSING


async def config_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish configuration."""
    user_id = update.effective_user.id
    config = get_user_config(user_id)

    await update.message.reply_text(
        "✅ <b>Configuración guardada!</b>\n\n"
        f"<b>Tus filtros:</b>\n"
        f"💲 Precio máximo: ${config['max_price']:,}\n"
        f"🛏 Ambientes mínimos: {config['min_rooms']}\n"
        f"🧾 Expensas máximas: ${config['max_expensas']:,}\n\n"
        "Te notificaré cuando encuentre departamentos que coincidan.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel configuration."""
    await update.message.reply_text(
        "Configuración cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job to check for new apartments and notify users."""
    try:
        logger.info("=" * 50)
        logger.info(f"Starting apartment check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        sent = load_sent()
        logger.info(f"Loaded {len(sent)} previously sent listings")

        logger.info("Scraping ArgenProp...")
        listings = scrape_argenprop(max_pages=5)
        logger.info(f"Found {len(listings)} total listings")

        # Get all registered users
        user_ids = get_all_user_ids()
        logger.info(f"Checking for {len(user_ids)} registered users")

        for ap in listings:
            if ap["id"] in sent:
                continue

            # Check each user's criteria
            for user_id in user_ids:
                config = get_user_config(user_id)
                if not config.get("active", True):
                    continue

                if matches(ap, config):
                    logger.info(f"Sending to user {user_id}: {ap['url']}")
                    try:
                        await send_telegram_message(context.bot, user_id, ap)
                    except Exception as e:
                        logger.error(f"Failed to send to user {user_id}: {e}")

            sent.add(ap["id"])

        save_sent(sent)
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error in check_and_notify: {e}", exc_info=True)


async def send_telegram_message(bot, chat_id, ap):
    """Send apartment notification via bot."""
    text = (
        "🏠 <b>Nuevo depto en alquiler (La Plata)</b>\n\n"
        f"💲 Alquiler: ${ap.get('price', 'N/A'):,}\n"
        f"🧾 Expensas: ${ap.get('expensas', 'N/A'):,}\n"
        f"🛏 {ap.get('rooms', 'N/A')} ambientes\n\n"
        f"🔗 {ap.get('url', '#')}"
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


def main():
    """Main function to run the bot."""
    logger.info("🤖 Telegram Apartment Bot Starting...")

    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))

    # Configuration conversation handler
    config_handler = ConversationHandler(
        entry_points=[CommandHandler("config", config_start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
            SET_MAX_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_max_price)],
            SET_MIN_ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_min_rooms)],
            SET_MAX_EXPENSAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_max_expensas)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(config_handler)

    # Schedule periodic apartment checks (every 30 minutes)
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_notify, interval=1800, first=10)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
