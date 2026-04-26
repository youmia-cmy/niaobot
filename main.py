import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN 未设置")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== Inline 键盘 ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell")],
        [InlineKeyboardButton("🛒 买虎皮鹦鹉", callback_data="buy"),
         InlineKeyboardButton("🔄 刷新", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    text = "🐦 **飞鸟牧场演示版**\n\n点击下方按钮操作～"
    markup = build_keyboard()
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ 操作成功！", show_alert=True)
    await send_panel(update, context, edit=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"收到 /start from user {update.effective_user.id}")
    await update.message.reply_text("✅ 机器人已收到 /start！\n欢迎来到飞鸟牧场\n点击下方按钮开始～")
    await send_panel(update, context)

async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or "无文本消息"
    logger.info(f"收到消息: {text} | from {update.effective_user.id}")
    await update.message.reply_text(f"收到消息: {text}\n请使用 /start 或点击按钮")

# ================== 命令菜单 ==================
async def post_init(application: Application):
    commands = [
        BotCommand("start", "🚀 启动飞鸟牧场"),
        BotCommand("open", "🐦 打开我的鸟场"),
        BotCommand("help", "❓ 帮助"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ 命令菜单已更新")

def main():
    logger.info("🚀 机器人启动中...")
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # 重要：处理所有文字消息（包括带 @ 的群组消息）
    application.add_handler(MessageHandler(filters.TEXT, any_message))

    logger.info("开始运行...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
