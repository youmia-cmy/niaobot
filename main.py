import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

# ================== 配置 ==================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请在 Railway Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ================== 键盘 ==================
def build_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
            InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")
        ],
        [
            InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
            InlineKeyboardButton("💰 出售全部", callback_data="sell_all")
        ],
        [
            InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ================== 主面板 ==================
async def send_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    text = (
        "🐦 **飞鸟牧场**（4级）\n"
        "💰 金币：9600  |  🌾 鸟粮：72\n"
        "🏠 鸟窝：4/4\n\n"
        "点击下方按钮进行操作～"
    )
    markup = build_keyboard()

    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(
                text, 
                reply_markup=markup, 
                parse_mode='MarkdownV2'
            )
        else:
            # 普通消息或兜底
            message = update.effective_message or (update.callback_query.message if update.callback_query else None)
            if message:
                await message.reply_text(
                    text, 
                    reply_markup=markup, 
                    parse_mode='MarkdownV2'
                )
    except TelegramError as e:
        logging.error(f"发送面板失败: {e}")
    except Exception as e:
        logging.error(f"send_panel 未知错误: {e}")


# ================== 按钮处理器（核心修复） ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    await query.answer("✅ 操作成功！", show_alert=False)

    try:
        if data == "pick_egg":
            await query.message.reply_text("✅ 捡蛋成功！金币 +100")
        elif data == "rush_produce":
            await query.message.reply_text("✅ 赶产成功！鸟蛋产量提升")
        elif data == "clean_dung":
            await query.message.reply_text("✅ 清扫鸟粪成功！鸟窝清洁度 +1")
        elif data == "sell_all":
            await query.message.reply_text("✅ 所有鸟蛋已出售！金币 +450")
        elif data == "buy_bird":
            await query.message.reply_text("✅ 购买虎皮鹦鹉成功！鸟窝 -1")
        else:
            await query.message.reply_text("未知操作")

        # 操作完成后刷新面板
        await send_panel(update, context, edit=True)

    except Exception as e:
        logging.error(f"按钮 {data} 处理出错: {e}")
        await query.answer("❌ 操作失败，请重试", show_alert=True)


# ================== 命令处理器 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到 **飞鸟牧场**！\n使用下方按钮或菜单开始经营～")
    await send_panel(update, context)


async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update, context)


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


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 可用命令：\n"
        "/start - 启动牧场\n"
        "/open - 打开鸟场面板\n"
        "/pick - 捡蛋\n"
        "/rush - 赶产\n"
        "/clean - 清扫鸟粪\n"
        "/sell - 出售全部\n"
        "/buy - 购买鸟\n"
        "/help - 帮助"
    )


# ================== 全局错误处理器（防止崩溃） ==================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"❌ 更新处理异常: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ 机器人遇到错误，请稍后再试～")
    except:
        pass


# ================== 初始化命令菜单 ==================
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
    print("✅ 机器人命令菜单已更新")


# ================== 主函数 ==================
def main():
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # 命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", open_farm))
    application.add_handler(CommandHandler("pick", pick_egg))
    application.add_handler(CommandHandler("rush", rush_produce))
    application.add_handler(CommandHandler("clean", clean_dung))
    application.add_handler(CommandHandler("sell", sell_all))
    application.add_handler(CommandHandler("buy", buy_bird))
    application.add_handler(CommandHandler("help", help_cmd))

    # 按钮处理器
    application.add_handler(CallbackQueryHandler(button_handler))

    # 全局错误处理（关键！防止崩溃）
    application.add_error_handler(error_handler)

    print("🚀 飞鸟牧场机器人启动中...")
    application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
