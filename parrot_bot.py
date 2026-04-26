import logging
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("请在 Railway / Render 的环境变量中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DB_FILE = "database.db"

# ================== 数据库初始化 ==================
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                level INTEGER DEFAULT 4,
                coins INTEGER DEFAULT 9600,
                bird_slots INTEGER DEFAULT 4,
                bird_food INTEGER DEFAULT 72,
                experience INTEGER DEFAULT 0,
                birds TEXT DEFAULT '[{"type":"麻雀","num":2,"remain":6},{"type":"鸽子","num":1,"remain":0},{"type":"珍珠鸟","num":1,"remain":4}]',
                last_active TEXT
            )
        ''')
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "level": row[2], "coins": row[3], "bird_slots": row[4],
                    "bird_food": row[5], "experience": row[6],
                    "birds": eval(row[7]) if row[7] else []
                }
            else:
                default_birds = [{"type":"麻雀","num":2,"remain":6}, {"type":"鸽子","num":1,"remain":0}, {"type":"珍珠鸟","num":1,"remain":4}]
                await db.execute("INSERT INTO users (user_id, username, birds) VALUES (?, ?, ?)", (user_id, None, str(default_birds)))
                await db.commit()
                return {"level":4, "coins":9600, "bird_slots":4, "bird_food":72, "experience":0, "birds":default_birds}

async def save_user_data(user_id: int, data: dict):
    birds_str = str(data["birds"])
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            UPDATE users SET level=?, coins=?, bird_slots=?, bird_food=?, experience=?, birds=?, last_active=?
            WHERE user_id=?
        ''', (data.get("level",4), data["coins"], data["bird_slots"], data["bird_food"],
              data.get("experience",0), birds_str, datetime.now().isoformat(), user_id))
        await db.commit()

# ================== Inline 键盘（游戏操作面板）==================
def build_farm_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird"),
         InlineKeyboardButton("🔄 刷新牧场", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(keyboard)

def format_farm(user_data):
    birds_info = []
    for b in user_data["birds"]:
        remain = b.get("remain", 0)
        status = f"{remain}小时后" if remain > 0 else "✅ 可立即捡蛋"
        birds_info.append(f"▫️ {b['type']}×{b['num']}：{status}")
    
    return (
        f"🐦 **你的飞鸟牧场**（{user_data['level']}级）\n"
        f"💰 金币：{user_data['coins']} | 🌾 鸟粮：{user_data['bird_food']}\n"
        f"🏠 鸟窝：{user_data['bird_slots']}/4\n\n" +
        "\n".join(birds_info) +
        f"\n\n📊 经验：{user_data.get('experience', 0)}"
    )

# ================== 发送牧场面板 ===================
async def send_farm_panel(update, context, edit=False):
    user_id = update.effective_user.id if hasattr(update, 'effective_user') and update.effective_user else update.callback_query.from_user.id
    data = await get_user_data(user_id)
    text = format_farm(data)
    markup = build_farm_keyboard()
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await (update.message if hasattr(update, 'message') else update.callback_query.message).reply_text(
            text, reply_markup=markup, parse_mode='Markdown'
        )

# ================== 按钮回调处理 ===================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id
    user_data = await get_user_data(user_id)

    # 简化演示操作（你可以在这里补充完整金币、鸟粮等逻辑）
    result_msg = {
        "pick_egg": "✅ 捡蛋成功！金币增加",
        "rush_produce": "✅ 赶产成功！",
        "clean_dung": "✅ 清扫鸟粪成功！金币+32",
        "sell_all": "✅ 出售全部完成！",
        "buy_bird": "✅ 虎皮鹦鹉购买成功！",
        "refresh": "🔄 牧场已刷新"
    }

    await query.answer(result_msg.get(action, "操作成功"), show_alert=True)

    # 操作后刷新面板
    await send_farm_panel(update, context, edit=True)

# ================== 命令菜单设置（重点部分）==================
async def post_init(application: Application):
    """机器人启动时自动设置命令菜单（左下角 Menu 按钮）"""
    commands = [
        BotCommand("start", "🚀 启动飞鸟牧场"),
        BotCommand("open", "🐦 打开我的鸟场（带操作面板）"),
        BotCommand("status", "📊 查看牧场状态"),
        BotCommand("help", "❓ 帮助与规则"),
        BotCommand("rules", "📜 游戏规则说明"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ 机器人命令菜单（Menu面板）已成功设置！")

# ================== 命令处理函数 ===================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎来到【QQ牧场·飞鸟饲养】纯文字版！\n点击左下角 **Menu** 按钮或输入 /open 开始养鸟～")
    await send_farm_panel(update, context)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_farm_panel(update, context)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_farm_panel(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐦 **飞鸟牧场帮助**\n\n"
        "命令菜单（点击左下角 Menu）：\n"
        "/start - 启动机器人\n"
        "/open - 打开带按钮的操作面板\n"
        "/status - 查看当前牧场状态\n"
        "/help - 显示帮助\n"
        "/rules - 游戏规则\n\n"
        "操作提示：\n直接点击面板上的 Inline 按钮即可进行捡蛋、赶产、清扫、出售等操作。"
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 **游戏规则**\n\n"
        "• 每日偷蛋、帮喂上限 30 次\n"
        "• 鸟粪每坨可卖 8 金币\n"
        "• 鸟窝满 4 位后需升级才能继续购买新鸟\n"
        "• 各类鸟蛋可直接出售或存仓库\n"
        "• 好友之间可以互相偷蛋和补鸟粮\n\n"
        "祝你玩得开心！🐦"
    )

# ================== 文字消息兼容 ===================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if any(k in text for k in ["打开我的鸟场", "我的鸟场", "打开鸟场"]):
        await send_farm_panel(update, context)
    else:
        await update.message.reply_text("请使用左下角 Menu 按钮或输入 /open 打开牧场面板")

# ================== 主函数 ===================
def main():
    asyncio.run(init_db())

    application = Application.builder() \
        .token(TOKEN) \
        .post_init(post_init) \   # ← 命令菜单在这里自动设置
        .build()

    # 命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", open_farm))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("rules", rules))

    # Inline 按钮处理器
    application.add_handler(CallbackQueryHandler(button_handler))

    # 普通文字消息
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 飞鸟牧场机器人（带命令菜单 + Inline键盘）启动成功！")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
