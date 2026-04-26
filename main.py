import logging
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================== Inline 键盘（游戏面板） ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy"),
         InlineKeyboardButton("🔄 刷新", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(keyboard)

def format_status():
    return (
        "🐦 **你的飞鸟牧场**（4级）\n"
        "💰 金币：9600 | 🌾 鸟粮：72\n"
        "🏠 鸟窝：4/4\n\n"
        "▫️ 麻雀×2：✅ 可立即捡蛋\n"
        "▫️ 鸽子×1：✅ 可立即捡蛋\n"
        "▫️ 珍珠鸟×1：4小时后\n\n"
        "点击下方按钮操作～\n\n"
        "（当前为演示版，数据暂不保存）"
    )

async def send_panel(update, context, edit=False):
    text = format_status()
    markup = build_keyboard()
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await (update.message or update.callback_query.message).reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    responses = {
        "pick": "✅ 捡蛋成功！获得鸟蛋，金币增加",
        "rush": "✅ 赶产成功！鸟更快产蛋",
        "clean": "✅ 清扫鸟粪成功！获得金币",
        "sell": "✅ 出售全部完成！金币增加",
        "buy": "✅ 虎皮鹦鹉购买成功！（演示版）",
        "refresh": "🔄 牧场已刷新"
    }
    await query.answer(responses.get(action, "操作成功"), show_alert=True)
    await send_panel(update, context, edit=True)

def post_init(application):
    commands = [
        BotCommand("start", "🚀 启动飞鸟牧场"),
        BotCommand("open", "🐦 打开我的鸟场"),
        BotCommand("help", "❓ 帮助"),
    ]
    asyncio.create_task(application.bot.set_my_commands(commands))
    print("✅ 命令菜单已设置成功！")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎来到【QQ牧场·飞鸟饲养】！\n点击按钮开始养鸟、捡蛋、偷蛋～")
    await send_panel(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("输入 /open 打开操作面板，或点击左下角 Menu 按钮。")

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 飞鸟牧场机器人正在启动...")
    application.run_polling()

if __name__ == '__main__':
    main()
