import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway 设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# ================== 键盘 ==================
def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 买鸟", callback_data="buy_bird")]
    ])


# ================== 安全面板 ==================
async def send_panel(update: Update, edit: bool = False):
    text = "🐦 飞鸟牧场（4级）\n💰 金币：9600 | 🌾 鸟粮：72\n🏠 鸟窝：4/4\n\n点击按钮操作～"
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=markup)
    except Exception as e:
        logger.error(f"发送面板失败: {e}")


# ================== 按钮 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ 操作成功")
    try:
        await query.message.reply_text("✅ 已执行！")
        await send_panel(update, edit=True)
    except Exception as e:
        logger.error(f"按钮错误: {e}")


# ================== 命令 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！")
    await send_panel(update)


async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /start 或 /open 打开面板")


# ================== 全局错误处理器 ==================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"全局异常: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ 机器人出错了，请稍后重试")
    except:
        pass


# ================== 启动初始化（增加保护） ==================
async def post_init(application: Application):
    try:
        await application.bot.set_my_commands([
            BotCommand("start", "启动牧场"),
            BotCommand("open", "打开面板"),
            BotCommand("help", "帮助"),
        ])
        logger.info("✅ 命令菜单设置成功")
    except Exception as e:
        logger.warning(f"设置命令菜单失败（不影响运行）: {e}")


def main():
    try:
        app = Application.builder().token(TOKEN).post_init(post_init).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("open", open_farm))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CallbackQueryHandler(button_handler))

        app.add_error_handler(error_handler)

        logger.info("🚀 机器人正在启动...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.critical(f"启动失败: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
