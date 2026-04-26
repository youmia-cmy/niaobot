import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================== Inline 键盘（飞鸟牧场操作面板） ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🥚 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird"),
         InlineKeyboardButton("🔄 刷新牧场", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_farm_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    text = (
        "🐦 **你的飞鸟牧场**（4级）\n"
        "💰 金币：9600 | 🌾 鸟粮：72\n"
        "🏠 鸟窝：4/4\n\n"
        "▫️ 麻雀×2：✅ 可立即捡蛋\n"
        "▫️ 鸽子×1：✅ 可立即捡蛋\n"
        "▫️ 珍珠鸟×1：4小时后\n\n"
        "点击下方按钮进行操作～"
    )
    markup = build_keyboard()
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ 操作成功！（演示版）", show_alert=True)
    await send_farm_panel(update, context, edit=True)

# ================== 命令处理 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 欢迎来到【飞鸟饲养】！\n点击下方按钮开始养鸟～")
    await send_farm_panel(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /open 或点击左下角 Menu 按钮打开牧场面板。")

# ================== 设置命令菜单（重点更新） ==================
async def post_init(application: Application):
    commands = [
        BotCommand("start", "🚀 启动飞鸟牧场"),
        BotCommand("open", "🐦 打开我的鸟场"),
        BotCommand("help", "❓ 帮助说明"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ 飞鸟牧场命令菜单已更新！")

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 飞鸟牧场机器人启动中...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
