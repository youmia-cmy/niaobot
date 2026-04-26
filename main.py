import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError, BadRequest

# ================== 配置 ==================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # 改成 DEBUG 方便看详细错误
)

# ================== 键盘 ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ================== 安全发送面板（关键修复） ==================
async def send_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    text = (
        "🐦 *飞鸟牧场*（4级）\n"
        "💰 金币：9600  |  🌾 鸟粮：72\n"
        "🏠 鸟窝：4/4\n\n"
        "点击下方按钮进行操作～"
    )
    markup = build_keyboard()

    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=markup, parse_mode='Markdown'
            )
        else:
            message = update.effective_message
            if message:
                await message.reply_text(
                    text, reply_markup=markup, parse_mode='Markdown'
                )
    except BadRequest as e:
        logging.warning(f"Markdown 错误: {e}. 尝试使用纯文本...")
        # 降级为纯文本
        safe_text = text.replace('*', '')
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(safe_text, reply_markup=markup)
        elif update.effective_message:
            await update.effective_message.reply_text(safe_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"send_panel 错误: {e}")


# ================== 按钮处理器 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    await query.answer("✅ 操作成功！")

    try:
        if data == "pick_egg":
            await query.message.reply_text("✅ 捡蛋成功！金币 +100")
        elif data == "rush_produce":
            await query.message.reply_text("✅ 赶产成功！鸟蛋产量提升")
        elif data == "clean_dung":
            await query.message.reply_text("✅ 清扫鸟粪成功！")
        elif data == "sell_all":
            await query.message.reply_text("✅ 所有物品已出售！")
        elif data == "buy_bird":
            await query.message.reply_text("✅ 购买虎皮鹦鹉成功！")
        else:
            await query.message.reply_text("未知操作")

        await send_panel(update, context, edit=True)

    except Exception as e:
        logging.error(f"按钮 {data} 处理异常: {e}")
        await query.answer("❌ 操作失败，请重试", show_alert=True)


# ================== 命令处理器（简化 + 安全） ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！")
    await send_panel(update, context)


async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update, context)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /start 或 /open 打开面板")


# 其他命令保持简单
async def simple_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str):
    await update.message.reply_text(msg)


# ================== 全局错误处理器（防止坠毁） ==================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"❌ 全局异常: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ 机器人遇到错误，请稍后再试～")
    except:
        pass


# ================== 初始化 ==================
async def post_init(application: Application):
    commands = [
        BotCommand("start", "启动飞鸟牧场"),
        BotCommand("open", "打开鸟场"),
        BotCommand("help", "帮助"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ 命令菜单已设置")


def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # 命令
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", open_farm))
    application.add_handler(CommandHandler("help", help_cmd))
    
    # 按钮
    application.add_handler(CallbackQueryHandler(button_handler))

    # 全局错误处理（最重要）
    application.add_error_handler(error_handler)

    print("🚀 飞鸟牧场机器人启动成功...")
    application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
