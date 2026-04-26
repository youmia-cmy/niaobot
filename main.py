import logging
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway 的 Variables 中正确设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# ================== Inline 键盘面板 ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird"),
         InlineKeyboardButton("🔄 刷新牧场", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(keyboard)

def format_farm():
    return (
        "🐦 **你的飞鸟牧场**（4级）\n"
        "💰 金币：9600 | 🌾 鸟粮：72\n"
        "🏠 鸟窝：4/4\n\n"
        "▫️ 麻雀×2：✅ 可立即捡蛋\n"
        "▫️ 鸽子×1：✅ 可立即捡蛋\n"
        "▫️ 珍珠鸟×1：4小时后\n\n"
        "点击下方按钮操作（演示版，数据不持久保存）"
    )

async def send_farm_panel(update, context, edit=False):
    text = format_farm()
    markup = build_keyboard()
    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        except:
            pass
    else:
        await (update.message or update.callback_query.message).reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    
    messages = {
        "pick_egg": "✅ 捡蛋成功！收获鸟蛋，金币 +120",
        "rush_produce": "✅ 赶产成功！金币 +5，鸟粮增加",
        "clean_dung": "✅ 清扫鸟粪成功！金币 +32",
        "sell_all": "✅ 出售全部完成！金币 +250",
        "buy_bird": "✅ 虎皮鹦鹉购买成功！（鸟窝 +1）",
        "refresh": "🔄 牧场已刷新"
    }
    
    await query.answer(messages.get(action, "操作成功"), show_alert=True)
    await send_farm_panel(update, context, edit=True)

def post_init(application):
    commands = [
        BotCommand("start", "🚀 启动飞鸟牧场"),
        BotCommand("open", "🐦 打开我的鸟场"),
        BotCommand("help", "❓ 帮助说明"),
    ]
    asyncio.create_task(application.bot.set_my_commands(commands))
    print("✅ 命令菜单设置成功！")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "欢迎来到【QQ牧场·飞鸟饲养】纯文字群聊版！\n\n"
        "点击下方 Inline 按钮进行操作～\n"
        "左下角 Menu 按钮可快速选择命令。"
    )
    await send_farm_panel(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /open 打开牧场面板，或点击 Inline 按钮操作。")

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application
