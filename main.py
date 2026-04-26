import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== 键盘 ==================
def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird")],
    ])

# ================== 面板 ==================
async def send_panel(update: Update, edit: bool = False):
    text = "🐦 **飞鸟牧场**（4级）\n💰 金币：9600 | 🌾 鸟粮：72\n🏠 鸟窝：4/4\n\n点击按钮操作～"
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"面板发送失败: {e}")

# ================== 按钮处理器 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer("✅ 操作成功！")

    try:
        if data == "pick_egg":
            await query.message.reply_text("✅ 捡蛋成功！金币 +100")
        elif data == "rush_produce":
            await query.message.reply_text("✅ 赶产成功！")
        elif data == "clean_dung":
            await query.message.reply_text("✅ 清扫鸟粪成功！")
        elif data == "sell_all":
            await query.message.reply_text("✅ 出售全部完成！")
        elif data == "buy_bird":
            await query.message.reply_text("✅ 购买虎皮鹦鹉成功！")
        await send_panel(update, edit=True)
    except Exception as e:
        logger.error(f"按钮错误: {e}")

# ================== 命令处理器 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！")
    await send_panel(update)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)

async def pick_egg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 捡蛋成功！金币 +100")

async def rush_produce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 赶产成功！")

async def clean_dung(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 清扫鸟粪成功！")

async def sell_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 出售全部完成！")

async def buy_bird(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ 购买虎皮鹦鹉成功！")

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 排行榜功能开发中...")

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📅 签到成功！领取鸟粮 +10")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /start 或 /open 打开面板")

# ================== 全局错误处理 ==================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"全局异常: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ 操作出错，请重试")
    except:
        pass

# ================== 初始化命令菜单 ==================
async def post_init(application: Application):
    commands = [
        BotCommand("start", "启动飞鸟牧场"),
        BotCommand("open", "打开我的鸟场"),
        BotCommand("pick", "捡蛋"),
        BotCommand("rush", "赶产"),
        BotCommand("rank", "查看排行榜"),
        BotCommand("help", "帮助"),
        BotCommand("checkin", "签到领取饲料"),
        BotCommand("clean", "清扫鸟粪"),
        BotCommand("sell", "出售全部"),
        BotCommand("buy", "购买虎皮鹦鹉"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ 命令菜单已更新")

# ================== 主函数 ==================
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # 命令
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_farm))
    app.add_handler(CommandHandler("pick", pick_egg))
    app.add_handler(CommandHandler("rush", rush_produce))
    app.add_handler(CommandHandler("clean", clean_dung))
    app.add_handler(CommandHandler("sell", sell_all))
    app.add_handler(CommandHandler("buy", buy_bird))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("help", help_cmd))

    # 按钮
    app.add_handler(CallbackQueryHandler(button_handler))

    # 错误处理
    app.add_error_handler(error_handler)

    logger.info("🚀 飞鸟牧场机器人启动中...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
