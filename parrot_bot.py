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
    raise ValueError("请在 Railway 的 Variables 中设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DB_FILE = "database.db"

# ================== 数据库 ==================
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 4,
                coins INTEGER DEFAULT 9600,
                bird_slots INTEGER DEFAULT 4,
                bird_food INTEGER DEFAULT 72,
                experience INTEGER DEFAULT 0,
                birds TEXT DEFAULT '[{"type":"麻雀","num":2,"remain":6},{"type":"鸽子","num":1,"remain":0},{"type":"珍珠鸟","num":1,"remain":4}]'
            )
        ''')
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "level": row[1], "coins": row[2], "bird_slots": row[3],
                    "bird_food": row[4], "experience": row[5],
                    "birds": eval(row[6]) if row[6] else []
                }
            else:
                default_birds = [{"type":"麻雀","num":2,"remain":6}, {"type":"鸽子","num":1,"remain":0}, {"type":"珍珠鸟","num":1,"remain":4}]
                await db.execute("INSERT INTO users (user_id, birds) VALUES (?, ?)", (user_id, str(default_birds)))
                await db.commit()
                return {"level":4, "coins":9600, "bird_slots":4, "bird_food":72, "experience":0, "birds":default_birds}

async def save_user_data(user_id: int, data: dict):
    birds_str = str(data["birds"])
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            UPDATE users SET level=?, coins=?, bird_slots=?, bird_food=?, experience=?, birds=?
            WHERE user_id=?
        ''', (data.get("level",4), data["coins"], data["bird_slots"], data["bird_food"],
              data.get("experience",0), birds_str, user_id))
        await db.commit()

# ================== Inline 键盘 ==================
def build_keyboard():
    keyboard = [
        [InlineKeyboardButton("🐦 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell")],
        [InlineKeyboardButton("🛒 买虎皮鹦鹉", callback_data="buy"),
         InlineKeyboardButton("🔄 刷新", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(keyboard)

def format_farm(data):
    birds_info = [f"▫️ {b['type']}×{b['num']}：{'✅ 可捡' if b.get('remain',0)==0 else f'{b.get(\"remain\",0)}小时后'}" for b in data["birds"]]
    return (
        f"🐦 **你的飞鸟牧场**（{data['level']}级）\n"
        f"💰 金币：{data['coins']} | 🌾 鸟粮：{data['bird_food']}\n"
        f"🏠 鸟窝：{data['bird_slots']}/4\n\n" +
        "\n".join(birds_info) +
        f"\n\n📊 经验：{data.get('experience', 0)}"
    )

async def send_panel(update, context, edit=False):
    user_id = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    data = await get_user_data(user_id)
    text = format_farm(data)
    markup = build_keyboard()
    
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await (update.message or update.callback_query.message).reply_text(text, reply_markup=markup, parse_mode='Markdown')

# ================== 按钮处理 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id
    data = await get_user_data(user_id)

    if action == "pick_egg":
        if data["bird_food"] >= 5:
            data["coins"] += random.randint(80, 150)
            data["bird_food"] -= 5
            await query.answer("✅ 捡蛋成功！金币增加", show_alert=True)
        else:
            await query.answer("鸟粮不足！", show_alert=True)
    elif action == "rush":
        if data["coins"] >= 10:
            data["coins"] += 5
            data["bird_food"] = min(200, data["bird_food"] + 15)
            await query.answer("✅ 赶产成功！", show_alert=True)
        else:
            await query.answer("金币不足！", show_alert=True)
    elif action == "clean":
        coins = random.randint(24, 56)
        data["coins"] += coins
        await query.answer(f"✅ 清扫成功！+{coins}金币", show_alert=True)
    elif action == "sell":
        income = random.randint(180, 350)
        data["coins"] += income
        data["experience"] = data.get("experience", 0) + 15
        await query.answer(f"✅ 出售完成！+{income}金币", show_alert=True)
    elif action == "buy":
        if data["bird_slots"] < 4 and data["coins"] >= 700:
            data["coins"] -= 700
            data["bird_slots"] += 1
            data["birds"].append({"type":"虎皮鹦鹉","num":1,"remain":1})
            await query.answer("✅ 购买成功！", show_alert=True)
        else:
            await query.answer("鸟窝已满或金币不足！", show_alert=True)
    elif action == "refresh":
        await query.answer("🔄 已刷新")

    await save_user_data(user_id, data)
    await send_panel(update, context, edit=True)

# ================== 命令菜单 ==================
def post_init(application: Application):
    commands = [
        BotCommand("start", "🚀 启动飞鸟牧场"),
        BotCommand("open", "🐦 打开我的鸟场"),
        BotCommand("help", "❓ 帮助"),
    ]
    asyncio.create_task(application.bot.set_my_commands(commands))
    print("✅ 命令菜单已设置！")

# ================== 命令处理 ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎来到飞鸟牧场！点击下方按钮开始养鸟～")
    await send_panel(update, context)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update, context)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /open 打开面板，或点击左下角 Menu 按钮操作。")

# ================== 主函数 ==================
def main():
    asyncio.run(init_db())
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("open", open_farm))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 飞鸟牧场机器人启动中...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
