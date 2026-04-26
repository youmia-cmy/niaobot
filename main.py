import logging
import os
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请设置 TELEGRAM_BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "user_data.json"

# ================== 等级经验表 ==================
LEVEL_EXP = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 999999]

user_data = {}

def load_data():
    global user_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
    except:
        pass

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存失败: {e}")

def get_user_data(user_id: int):
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {
            "gold": 5000, "feed": 50, "birds": 2, "nests": 4,
            "level": 1, "exp": 0, "last_active": 0
        }
    return user_data[uid]

def add_exp(user_id: int, amount: int):
    user = get_user_data(user_id)
    user["exp"] += amount
    old_level = user["level"]
    
    while user["level"] < 9 and user["exp"] >= LEVEL_EXP[user["level"]]:
        user["level"] += 1
        user["gold"] += 200
    return user["level"] > old_level

# ================== 键盘 & 面板 ==================
def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥚 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮鹦鹉", callback_data="buy_bird")],
    ])

async def send_panel(update: Update, edit: bool = False):
    user = get_user_data(update.effective_user.id)
    text = (
        f"🦜 **飞鸟牧场**（{user['level']}级）\n"
        f"💰 金币：{user['gold']}  |  🌾 鸟粮：{user['feed']}\n"
        f"🦜 鹦鹉：{user['birds']}只  |  🏠 鸟窝：{user['nests']}/4\n"
        f"⭐ 经验：{user['exp']}/{LEVEL_EXP[user['level']]}"
    )
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"面板错误: {e}")

# ================== 群内活跃经验 ==================
async def group_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    now = datetime.now().timestamp()
    user = get_user_data(user_id)
    
    if now - user.get("last_active", 0) < 8:
        return
    
    user["last_active"] = now
    
    if random.random() < 0.65:
        exp_gain = random.randint(8, 20)
        if add_exp(user_id, exp_gain):
            await update.message.reply_text(
                f"🎉 恭喜升级！飞鸟牧场升到 **{user['level']}级**！\n+200 金币奖励",
                parse_mode='Markdown'
            )
        save_data()

# ================== 按钮处理器 ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_data(update.effective_user.id)
    data = query.data
    await query.answer("✅ 操作成功！")

    try:
        if data == "pick_egg":
            reward = 80 + user['birds'] * 25 + user['level'] * 15
            user['gold'] += reward
            await query.message.reply_text(f"✅ 捡蛋成功！获得 {reward} 金币")

        elif data == "rush_produce":
            user['feed'] = min(user['feed'] + 20, 300)
            await query.message.reply_text("✅ 赶产成功！鸟粮 +20")

        elif data == "clean_dung":
            add_exp(update.effective_user.id, 30)
            await query.message.reply_text("✅ 清扫成功！+30 经验")

        elif data == "sell_all":
            earnings = user['birds'] * (120 + user['level'] * 20)
            user['gold'] += earnings
            await query.message.reply_text(f"✅ 出售成功！获得 {earnings} 金币")

        elif data == "buy_bird":
            cost = max(600, 800 - user['level'] * 30)
            if user['gold'] >= cost and user['birds'] < user['nests']:
                user['gold'] -= cost
                user['birds'] += 1
                await query.message.reply_text("✅ 购买成功！")
            else:
                await query.message.reply_text("❌ 金币不足或鸟窝已满")

        save_data()
        await send_panel(update, edit=True)

    except Exception as e:
        logger.error(f"按钮错误: {e}")

# ================== 独立命令处理器（修复 SyntaxError） ==================
async def cmd_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id)
    reward = 80 + user['birds'] * 25 + user['level'] * 15
    user['gold'] += reward
    save_data()
    await update.message.reply_text(f"✅ 捡蛋成功！获得 {reward} 金币")

async def cmd_rush(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id)
    user['feed'] = min(user['feed'] + 20, 300)
    save_data()
    await update.message.reply_text("✅ 赶产成功！鸟粮 +20")

async def cmd_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_exp(update.effective_user.id, 30)
    save_data()
    await update.message.reply_text("✅ 清扫成功！+30 经验")

async def cmd_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id)
    earnings = user['birds'] * (120 + user['level'] * 20)
    user['gold'] += earnings
    save_data()
    await update.message.reply_text(f"✅ 出售成功！获得 {earnings} 金币")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id)
    cost = max(600, 800 - user['level'] * 30)
    if user['gold'] >= cost and user['birds'] < user['nests']:
        user['gold'] -= cost
        user['birds'] += 1
        save_data()
        await update.message.reply_text("✅ 购买成功！")
    else:
        await update.message.reply_text("❌ 金币不足或鸟窝已满")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！\n在群里聊天可获得经验升级哦～")
    await send_panel(update)

async def open_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['gold'], reverse=True)[:10]
    text = "🏆 **飞鸟牧场全球排行榜** 🏆\n\n"
    for i, (uid, d) in enumerate(sorted_users, 1):
        text += f"{i}. 用户{uid[-4:]} — 💰 {d['gold']}金币（{d.get('level',1)}级）\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id)
    user['feed'] += 25
    save_data()
    await update.message.reply_text("📅 签到成功！获得 25 鸟粮")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("使用 /start 或 /open 打开面板\n/rank 查看排行榜")

# ================== 错误处理 ==================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"全局错误: {context.error}", exc_info=True)

# ================== 初始化 ==================
async def post_init(application: Application):
    commands = [
        BotCommand("start", "启动飞鸟牧场"),
        BotCommand("open", "打开我的鸟场"),
        BotCommand("pick", "捡蛋"),
        BotCommand("rush", "赶产"),
        BotCommand("clean", "清扫鸟粪"),
        BotCommand("sell", "出售全部"),
        BotCommand("buy", "购买虎皮鹦鹉"),
        BotCommand("rank", "查看排行榜"),
        BotCommand("checkin", "签到"),
        BotCommand("help", "帮助"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ 命令菜单更新完成")

def main():
    load_data()
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # 命令处理器
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_farm))
    app.add_handler(CommandHandler("pick", cmd_pick))
    app.add_handler(CommandHandler("rush", cmd_rush))
    app.add_handler(CommandHandler("clean", cmd_clean))
    app.add_handler(CommandHandler("sell", cmd_sell))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("checkin", checkin))
    app.add_handler(CommandHandler("help", help_cmd))

    # 按钮
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # 群内活跃经验
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP), group_activity))

    app.add_error_handler(error_handler)

    logger.info("🚀 飞鸟牧场机器人启动成功！")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
