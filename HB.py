import os
import math
import time
import logging
from datetime import datetime
from pytube import YouTube, Playlist
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext
)
from telegram.error import BadRequest
from aiohttp import web

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('youtube_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration from environment variables
CONFIG = {
    'token': os.getenv('BOT_TOKEN'),
    'admin_ids': [int(admin_id) for admin_id in os.getenv('ADMIN_IDS', '').split(',') if admin_id],
    'required_channels': os.getenv('REQUIRED_CHANNELS', 'Megahubbots').split(','),
    'channel_links': os.getenv('CHANNEL_LINKS', 'https://t.me/megahubbots').split(',')
}

# Webhook configuration
PORT = int(os.getenv('PORT', 10000))
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '12345')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://youtube-bot-fdcc.onrender.com') + WEBHOOK_PATH

# Global variables to store YouTube data
youtube_data = {}

# Text messages
START_TEXT = """
HI {}, 
I AM AN ADVANCED YOUTUBE DOWNLOADER BOT
I CAN DOWNLOAD YOUTUBE VIDEOS, THUMBNAILS
AND PLAYLIST VIDEOS....
ONE OF THE FASTEST YOUTUBE BOTS 
I CAN DOWNLOAD 911MB VIDEOS
IN 1 MINUTE
MADE BY @TELSABOTS
"""

HELP_TEXT = """
YOUTUBE VIDEO
SEND ANY URL.......
THEN SELECT AVAILABLE QUALITY

PLAYLIST
SEND ANY URL.....
THEN WAIT BOT WILL SEND
VIDEOS IN HIGH QUALITY...

MADE BY @TELSABOTS
"""

ABOUT_TEXT = """
🤖 <b>BOT: YOUTUBE DOWNLOADER</b>

🧑🏼‍💻 DEV: @ALLUADDICT

📢 <b>CHANNEL:</b> @TELSABOTS

📝 <b>Language:</b> <a href='https://python.org/'>Python3</a>

🧰 <b>Frame Work:</b> <a href='https://pyrogram.org/'>Pyrogram</a>

🤩 <b>SOURCE:</b> <a href='https://youtu.be/xyW5fe0AkXo'>CLICK HERE</a>
"""

SOURCE_TEXT = "<b>PRESS SOURCE BUTTON \nWATCH MY VIDEO AND\nCHECK DESCRIPTION FOR SOURCE CODE</b>"
RESULT_TEXT = "**JOIN @TELSABOTS**"

# Button layouts
def get_start_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📢CHANNEL📢', url='https://telegram.me/TELSABOTS'),
            InlineKeyboardButton('🧑🏼‍💻DEV🧑🏼‍💻', url='https://telegram.me/alluaddict')
        ],
        [
            InlineKeyboardButton('🆘HELP🆘', callback_data='help'),
            InlineKeyboardButton('🤗ABOUT🤗', callback_data='about'),
            InlineKeyboardButton('🔐CLOSE🔐', callback_data='close')
        ]
    ])

def get_help_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📢CHANNEL📢', url='https://telegram.me/TELSABOTS'),
            InlineKeyboardButton('🧑🏼‍💻DEV🧑🏼‍💻', url='https://telegram.me/alluaddict')
        ],
        [
            InlineKeyboardButton('🏡HOME🏡', callback_data='home'),
            InlineKeyboardButton('🤗ABOUT🤗', callback_data='about'),
            InlineKeyboardButton('🔐CLOSE🔐', callback_data='close')
        ]
    ])

def get_about_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📢CHANNEL📢', url='https://telegram.me/TELSABOTS'),
            InlineKeyboardButton('🧑🏼‍💻DEV🧑🏼‍💻', url='https://telegram.me/alluaddict')
        ],
        [
            InlineKeyboardButton('🏡HOME🏡', callback_data='home'),
            InlineKeyboardButton('🆘HELP🆘', callback_data='help'),
            InlineKeyboardButton('🔐CLOSE🔐', callback_data='close')
        ]
    ])

def get_source_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅SOURCE✅', url='https://youtu.be/xyW5fe0AkXo'),
            InlineKeyboardButton('🧑🏼‍💻DEV🧑🏼‍💻', url='https://telegram.me/alluaddict')
        ],
        [
            InlineKeyboardButton('🔐CLOSE🔐', callback_data='close')
        ]
    ])

def get_result_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📢CHANNEL📢', url='https://telegram.me/TELSABOTS'),
            InlineKeyboardButton('🧑🏼‍💻DEV🧑🏼‍💻', url='https://telegram.me/alluaddict')
        ],
        [
            InlineKeyboardButton('🔐CLOSE🔐', callback_data='close')
        ]
    ])

def get_quality_buttons(hd_size, low_size, audio_size):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f'🎬720P ⭕️ {hd_size}', callback_data='high'),
            InlineKeyboardButton(f'🎬360P ⭕️ {low_size}', callback_data='360p')
        ],
        [
            InlineKeyboardButton(f'🎧AUDIO ⭕️ {audio_size}', callback_data='audio')
        ],
        [
            InlineKeyboardButton('🖼THUMBNAIL🖼', callback_data='thumbnail')
        ]
    ])

# Utility functions
def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f}{power_labels[n]}B"

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f}{Dic_powerN[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((f"{days}d, ") if days else "") + \
          ((f"{hours}h, ") if hours else "") + \
          ((f"{minutes}m, ") if minutes else "") + \
          ((f"{seconds}s, ") if seconds else "") + \
          ((f"{milliseconds}ms, ") if milliseconds else "")
    return tmp[:-2]

async def progress_for_telegram(current, total, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \n<b>• Percentage :</b> {2}%\n".format(
            ''.join(["▰" for _ in range(math.floor(percentage / 10))]),
            ''.join(["▱" for _ in range(10 - math.floor(percentage / 10))]),
            round(percentage, 2))

        tmp = progress + "<b>✅ COMPLETED :</b> {0}\n<b>📂 SIZE :</b> {1}\n<b>⚡️ SPEED :</b> {2}/s\n<b>⏰ ETA :</b> {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        
        try:
            await message.edit_text(
                text=f"<b>Upload STARTED...</b>\n{tmp}"
            )
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

# Force join functionality
async def is_member_of_channels(user_id: int, context: CallbackContext) -> bool:
    """Check if the user is a member of all required channels."""
    if not CONFIG['required_channels']:
        return True
        
    for channel in CONFIG['required_channels']:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=f"@{channel}", user_id=user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        except BadRequest:
            return False
    return True

async def send_force_join_message(update: Update):
    """Send force join message with buttons for all channels."""
    if not CONFIG['channel_links']:
        return
        
    buttons = [
        [InlineKeyboardButton(f"Join {channel}", url=link)]
        for channel, link in zip(CONFIG['required_channels'], CONFIG['channel_links'])
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text(
        "🚨 You must join all required channels to use this bot.\n\n"
        "After joining, type /start again.",
        reply_markup=reply_markup
    )

# Command handlers
async def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    if not await is_member_of_channels(update.effective_user.id, context):
        await send_force_join_message(update)
        return
    
    text = START_TEXT.format(update.effective_user.mention)
    reply_markup = get_start_buttons()
    await update.message.reply_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: CallbackContext):
    """Handle the /help command."""
    if not await is_member_of_channels(update.effective_user.id, context):
        await send_force_join_message(update)
        return
    
    await update.message.reply_text(
        text=HELP_TEXT,
        disable_web_page_preview=True,
        reply_markup=get_help_buttons()
    )

async def about_command(update: Update, context: CallbackContext):
    """Handle the /about command."""
    if not await is_member_of_channels(update.effective_user.id, context):
        await send_force_join_message(update)
        return
    
    await update.message.reply_text(
        text=ABOUT_TEXT,
        disable_web_page_preview=True,
        reply_markup=get_about_buttons()
    )

async def source_command(update: Update, context: CallbackContext):
    """Handle the /source command."""
    if not await is_member_of_channels(update.effective_user.id, context):
        await send_force_join_message(update)
        return
    
    await update.message.reply_text(
        text=SOURCE_TEXT,
        disable_web_page_preview=True,
        reply_markup=get_source_buttons()
    )

# YouTube video handlers
async def handle_youtube_url(update: Update, context: CallbackContext):
    """Handle YouTube URLs."""
    if not await is_member_of_channels(update.effective_user.id, context):
        await send_force_join_message(update)
        return
    
    url = update.message.text
    try:
        yt = YouTube(url)
        chat_id = update.message.chat.id
        
        # Get different quality streams
        yt_hd = yt.streams.get_highest_resolution()
        yt_low = yt.streams.get_by_resolution(resolution='360p')
        yt_audio = yt.streams.filter(only_audio=True).first()
        
        # Store data for callback handling
        youtube_data[chat_id] = {
            'yt': yt,
            'ythd': yt_hd,
            'ytlow': yt_low,
            'ytaudio': yt_audio,
            'thumb': yt.thumbnail_url
        }
        
        # Prepare quality buttons
        hd_size = format_bytes(yt_hd.filesize) if yt_hd else "N/A"
        low_size = format_bytes(yt_low.filesize) if yt_low else "N/A"
        audio_size = format_bytes(yt_audio.filesize) if yt_audio else "N/A"
        
        await update.message.reply_photo(
            photo=yt.thumbnail_url,
            caption=f"🎬 TITLE: {yt.title}\n\n📤 UPLOADED: {yt.author}\n\n📢 CHANNEL LINK: https://www.youtube.com/channel/{yt.channel_id}",
            reply_markup=get_quality_buttons(hd_size, low_size, audio_size),
            quote=True
        )
    except Exception as e:
        logger.error(f"Error processing YouTube URL: {e}")
        await update.message.reply_text("❌ Error processing YouTube URL. Please try again.")

async def handle_playlist(update: Update, context: CallbackContext):
    """Handle YouTube playlist URLs."""
    if not await is_member_of_channels(update.effective_user.id, context):
        await send_force_join_message(update)
        return
    
    url = update.message.text
    try:
        playlist = Playlist(url)
        await update.message.reply_text(f"⏳ Processing playlist: {playlist.title} with {len(playlist.videos)} videos...")
        
        for video in playlist.videos:
            try:
                video_stream = video.streams.get_highest_resolution()
                if video_stream:
                    start_time = time.time()
                    file_path = video_stream.download()
                    
                    await update.message.reply_video(
                        video=open(file_path, 'rb'),
                        caption=f"⭕️ PLAYLIST: {playlist.title}\n📥 DOWNLOADED\n✅ JOIN @TELSABOTS",
                        supports_streaming=True,
                        progress=progress_for_telegram,
                        progress_args=(update.message, start_time)
                    )
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error processing video {video.title}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error processing playlist: {e}")
        await update.message.reply_text("❌ Error processing playlist. Please try again.")

# Callback query handler
async def callback_handler(update: Update, context: CallbackContext):
    """Handle callback queries."""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    data = query.data
    
    if chat_id not in youtube_data:
        await query.message.reply_text("❌ Session expired. Please send the YouTube URL again.")
        return
    
    yt_data = youtube_data[chat_id]
    start_time = time.time()
    
    try:
        if data == 'high':
            if yt_data['ythd']:
                file_path = yt_data['ythd'].download()
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=open(file_path, 'rb'),
                    caption=RESULT_TEXT,
                    reply_markup=get_result_buttons(),
                    supports_streaming=True,
                    progress=progress_for_telegram,
                    progress_args=(query.message, start_time)
                )
                os.remove(file_path)
                await query.message.delete()
            else:
                await query.message.reply_text("❌ 1080P quality not available. Choose another quality.")
                
        elif data == '360p':
            if yt_data['ytlow']:
                file_path = yt_data['ytlow'].download()
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=open(file_path, 'rb'),
                    caption=RESULT_TEXT,
                    reply_markup=get_result_buttons(),
                    supports_streaming=True,
                    progress=progress_for_telegram,
                    progress_args=(query.message, start_time)
                )
                os.remove(file_path)
                await query.message.delete()
            else:
                await query.message.reply_text("❌ 360P quality not available. Choose another quality.")
                
        elif data == 'audio':
            file_path = yt_data['ytaudio'].download(filename=f"{yt_data['yt'].title}.mp3")
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=open(file_path, 'rb'),
                caption=RESULT_TEXT,
                duration=yt_data['yt'].length,
                reply_markup=get_result_buttons(),
                progress=progress_for_telegram,
                progress_args=(query.message, start_time)
            )
            os.remove(file_path)
            await query.message.delete()
            
        elif data == 'thumbnail':
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=yt_data['thumb'],
                caption=RESULT_TEXT
            )
            await query.message.delete()
            
        elif data == 'home':
            await query.message.edit_text(
                text=START_TEXT.format(query.from_user.mention),
                disable_web_page_preview=True,
                reply_markup=get_start_buttons()
            )
            
        elif data == 'help':
            await query.message.edit_text(
                text=HELP_TEXT,
                disable_web_page_preview=True,
                reply_markup=get_help_buttons()
            )
            
        elif data == 'about':
            await query.message.edit_text(
                text=ABOUT_TEXT,
                disable_web_page_preview=True,
                reply_markup=get_about_buttons()
            )
            
        elif data == 'close':
            await query.message.delete()
            
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await query.message.reply_text("❌ An error occurred. Please try again.")

# Webhook handlers
async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK")

async def telegram_webhook(request):
    """Handle incoming webhook requests"""
    update = Update.de_json(await request.json(), application.bot)
    await application.update_queue.put(update)
    return web.Response(text="OK")

def main():
    """Run the bot"""
    global application
    application = Application.builder().token(CONFIG['token']).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("source", source_command))
    
    # Add URL handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'(.*)youtube.com/(.*)[&|?]v=(?P<video>[^&]*)(.*)'), 
        handle_youtube_url
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'(.*)youtube.com/(.*)[&|?]list=(?P<playlist>[^&]*)(.*)'), 
        handle_playlist
    ))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Start the bot with webhook if running on Render
    if os.getenv('RENDER'):
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
