import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# ================== 键盘 ==================
def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 买鸟", callback_data="buy_bird")]
    ])


# ================== 安全发面板 ==================
async def send_panel(update: Update, edit=False):
    text = "🐦 飞鸟牧场（4级）\n💰 金币：9600 | 🌾 鸟粮：72\n🏠 鸟窝：4/4\n\n点击按钮操作"
    markup = build_keyboard()
    
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=markup)
    except Exception as e:
        logging.error(f"面板发送失败: {e}")


# ================== 按钮处理 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ 操作成功")

    try:
        await query.message.reply_text("✅ 操作已执行！")
        await send_panel(update, edit=True)
    except Exception as e:
        logging.error(f"按钮异常: {e}")
        await query.answer("❌ 失败", show_alert=True)


# ================== 命令 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！")
    await send_panel(update)


async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /start 或 /open 打开面板")


# ================== 全局错误处理器（关键） ==================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"全局错误: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ 机器人出错了，请重试")
    except:
        pass


async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "启动牧场"),
        BotCommand("open", "打开面板"),
        BotCommand("help", "帮助"),
    ])
    print("✅ 命令菜单已更新")


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_farm))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_error_handler(error_handler)

    print("🚀 机器人启动中...")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
