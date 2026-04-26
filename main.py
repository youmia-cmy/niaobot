import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请确认 Railway Variables 中 TELEGRAM_BOT_TOKEN 已正确设置")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
    text = "🐦 **飞鸟牧场**（演示版）\n\n💰 金币：9600 | 🌾 鸟粮：72\n点击下方按钮操作～"
    markup = build_keyboard()
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ 操作成功！（演示版）", show_alert=True)
    await send_panel(update, context, edit=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 机器人已通过 Webhook 在线！\n欢迎来到飞鸟牧场～")
    await send_panel(update, context)

def post_init(application):
    commands = [
        BotCommand("start", "启动飞鸟牧场"),
        BotCommand("open", "打开我的鸟场"),
    ]
    application.bot.set_my_commands(commands)   # 同步调用更稳
    print("✅ 命令菜单设置完成")

def main():
    print("🚀 启动 Webhook 模式（Railway 推荐）...")
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Webhook 配置（Railway 会自动提供域名）
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        url_path=TOKEN.split(':')[1][-10:],   # 使用 Token 后10位作为路径
        webhook_url=None   # Railway 会自动处理
    )

if __name__ == '__main__':
    main()
