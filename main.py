import logging
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================== Inline 键盘 ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    text = "🐦 **飞鸟牧场**（4级）\n💰 金币：9600 | 🌾 鸟粮：72\n🏠 鸟窝：4/4\n\n点击按钮操作～"
    markup = build_keyboard()
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ 操作成功！", show_alert=True)
    await send_panel(update, context, edit=True)

# ================== 命令功能 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 欢迎来到飞鸟牧场！")
    await send_panel(update, context)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update, context)

async def pick_egg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 捡蛋成功！")

async def rush_produce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 赶产成功！")

async def clean_dung(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 清扫鸟粪成功！")

async def sell_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 出售全部完成！")

async def buy_bird(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 购买虎皮鹦鹉成功！")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用菜单或按钮操作飞鸟牧场。")

async def post_init(application: Application):
    commands = [
        BotCommand("start", "启动飞鸟牧场"),
        BotCommand("open", "打开我的鸟场"),
        BotCommand("pick", "捡蛋"),
        BotCommand("rush", "赶产"),
        BotCommand("clean", "清扫鸟粪"),
        BotCommand("sell", "出售全部"),
        BotCommand("buy", "购买虎皮鹦鹉"),
        BotCommand("help", "帮助"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ 命令菜单已更新")

def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", open_farm))
    application.add_handler(CommandHandler("pick", pick_egg))
    application.add_handler(CommandHandler("rush", rush_produce))
    application.add_handler(CommandHandler("clean", clean_dung))
    application.add_handler(CommandHandler("sell", sell_all))
    application.add_handler(CommandHandler("buy", buy_bird))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
