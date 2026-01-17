import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from scrappers.argenprop import scrape_argenprop
from scrappers.zonaprop import scrape_zonaprop
from scrappers.mercadolibre import scrape_mercadolibre
from scrappers.inmobusqueda import scrape_inmobusqueda
from scrappers.browser_manager import close_browser
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
        "Te notificaré cuando encuentre departamentos en alquiler en La Plata "
        "que coincidan con tus criterios.\n\n"
        f"<b>Tu configuración actual:</b>\n"
        f"💲 Precio: ${config.get('min_price', 0):,} - ${config['max_price']:,}\n"
        f"🛏 Ambientes: {config['min_rooms']} - {config.get('max_rooms', 'sin límite')}\n"
        f"🧾 Expensas máximas: ${config['max_expensas']:,}\n\n"
        "<b>Comandos disponibles:</b>\n"
        "/config - Modificar tus filtros de búsqueda\n"
        "/run - Buscar departamentos ahora (1 por fuente)\n"
        "/start - Ver este mensaje de ayuda\n\n"
        "📬 Recibirás notificaciones automáticas cada hora (máx. 4 mensajes).",
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


async def run_manual_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /run command - manually search and send 1 NEW listing per source (max 4)."""
    user_id = update.effective_user.id
    config = get_user_config(user_id)

    await update.message.reply_text(
        "🔍 Buscando departamentos nuevos...\nEsto puede tardar unos segundos."
    )

    try:
        # Load previously seen apartments
        sent = load_sent()

        # Scrape all sources (1 page each, sorted by most recent)
        sources = {
            "argenprop": scrape_argenprop(),
            "zonaprop": scrape_zonaprop(),
            "mercadolibre": scrape_mercadolibre(),
        }

        # Close browser after Playwright-based scraping
        close_browser()

        # Add Inmobusqueda (uses requests, not Playwright)
        sources["inmobusqueda"] = scrape_inmobusqueda()

        # Get first NEW matching listing from each source
        results = []

        for source_name, listings in sources.items():
            for ap in listings:
                if ap["id"] in sent:
                    continue  # Skip already seen apartments
                if matches(ap, config):
                    results.append(ap)
                    sent.add(ap["id"])  # Mark as seen
                    break  # Only 1 per source

        if not results:
            await update.message.reply_text(
                "😕 No encontré departamentos <b>nuevos</b> que coincidan con tus filtros.\n\n"
                f"<b>Tus filtros actuales:</b>\n"
                f"💲 Precio máximo: ${config['max_price']:,}\n"
                f"🛏 Ambientes mínimos: {config['min_rooms']}\n"
                f"🧾 Expensas máximas: ${config['max_expensas']:,}\n\n"
                "Los departamentos ya vistos no se muestran de nuevo.",
                parse_mode="HTML"
            )
            return

        await update.message.reply_text(
            f"✅ Encontré {len(results)} departamento(s) nuevo(s). Te muestro uno de cada fuente:"
        )

        for ap in results:
            await send_telegram_message(context.bot, user_id, ap)

        # Save the updated sent set
        save_sent(sent)

    except Exception as e:
        logger.error(f"Error in run_manual_search: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ocurrió un error al buscar. Intenta de nuevo más tarde."
        )


# Maximum listings to send per source per cycle (2 per source = max 8 messages/hour)
MAX_LISTINGS_PER_SOURCE = 2

# Quiet hours - don't send notifications between these hours (0-23)
QUIET_HOURS_START = 0   # midnight
QUIET_HOURS_END = 8     # 8 AM


def is_quiet_hours():
    """Check if current time is within quiet hours (00:00 - 06:00)."""
    current_hour = datetime.now().hour
    return QUIET_HOURS_START <= current_hour < QUIET_HOURS_END


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job to check for new apartments and notify users."""
    try:
        logger.info("=" * 50)
        logger.info(f"Starting apartment check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Check quiet hours
        if is_quiet_hours():
            logger.info("Quiet hours (00:00-06:00) - skipping notifications")
            logger.info("=" * 50)
            return

        sent = load_sent()
        logger.info(f"Loaded {len(sent)} previously sent listings")

        # Scrape all sources and keep them separate for per-source limiting
        sources = {}

        # Scrape all sources (1 page each by default, sorted by most recent)
        logger.info("Scraping ArgenProp...")
        sources["argenprop"] = scrape_argenprop()

        logger.info("Scraping ZonaProp...")
        sources["zonaprop"] = scrape_zonaprop()

        logger.info("Scraping MercadoLibre...")
        sources["mercadolibre"] = scrape_mercadolibre()

        # Close browser after Playwright-based scraping to free memory
        close_browser()

        logger.info("Scraping Inmobusqueda...")
        sources["inmobusqueda"] = scrape_inmobusqueda()

        total = sum(len(v) for v in sources.values())
        logger.info(f"Found {total} total listings from all sources")

        # Get all registered users
        user_ids = get_all_user_ids()
        logger.info(f"Checking for {len(user_ids)} registered users")

        # First, mark ALL scraped apartments as seen (to prevent re-checking non-matching ones)
        new_apartments = []
        for source_name, listings in sources.items():
            for ap in listings:
                if ap["id"] not in sent:
                    sent.add(ap["id"])
                    new_apartments.append(ap)

        logger.info(f"Found {len(new_apartments)} new apartments (not seen before)")

        # Now process only new apartments for each user
        for user_id in user_ids:
            config = get_user_config(user_id)
            if not config.get("active", True):
                continue

            # Group new apartments by source and apply per-source limit
            source_counts = {}
            for ap in new_apartments:
                source_name = ap.get("source", "unknown")
                if source_counts.get(source_name, 0) >= MAX_LISTINGS_PER_SOURCE:
                    continue

                if matches(ap, config):
                    logger.info(f"Sending to user {user_id} from {source_name}: {ap['url']}")
                    try:
                        await send_telegram_message(context.bot, user_id, ap)
                        source_counts[source_name] = source_counts.get(source_name, 0) + 1
                    except Exception as e:
                        logger.error(f"Failed to send to user {user_id}: {e}")

        save_sent(sent)
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error in check_and_notify: {e}", exc_info=True)


def format_number(value):
    """Format number with thousands separator (dot for Argentina)."""
    if value is None or value == 'N/A':
        return 'N/A'
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)


async def send_telegram_message(bot, chat_id, ap):
    """Send apartment notification via bot."""
    price = format_number(ap.get('price'))
    expensas = format_number(ap.get('expensas'))
    rooms = ap.get('rooms', 'N/A')

    text = (
        f"🏠 <b>Nuevo depto en alquiler (La Plata)</b>\n\n"
        f"💲 Alquiler: ${price}\n"
        f"🧾 Expensas: ${expensas}\n"
        f"🛏 {rooms} ambientes\n\n"
        f"🔗 {ap.get('url', '#')}"
    )
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


def main():
    """Main function to run the bot."""
    logger.info("Telegram Apartment Bot Starting...")

    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    # application.add_handler(CommandHandler("run", run_manual_search))  # Disabled - only hourly notifications

    # Configuration conversation handler (disabled - filter modification via Telegram turned off)
    # config_handler = ConversationHandler(
    #     entry_points=[CommandHandler("config", config_start)],
    #     states={
    #         CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
    #         SET_MAX_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_max_price)],
    #         SET_MIN_ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_min_rooms)],
    #         SET_MAX_EXPENSAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_max_expensas)],
    #     },
    #     fallbacks=[CommandHandler("cancel", cancel)],
    # )
    # application.add_handler(config_handler)

    # Schedule periodic apartment checks (every 1 hour to save resources)
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_notify, interval=3600, first=10)

    logger.info("Bot is running. Press Ctrl+C to stop.")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Cleanup browser on shutdown
        logger.info("Shutting down, cleaning up browser...")
        close_browser()


if __name__ == "__main__":
    main()
