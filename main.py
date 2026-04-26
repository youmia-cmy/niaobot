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

# ================== 等级经验表（1~9级） ==================
LEVEL_EXP = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 999999]

# ================== 用户数据 ==================
user_data = {}

def load_data():
    global user_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            logger.info(f"已加载 {len(user_data)} 名玩家")
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
    
    # 升级判断
    while user["level"] < 9 and user["exp"] >= LEVEL_EXP[user["level"]]:
        user["level"] += 1
        user["gold"] += 200  # 升级奖励
    
    if user["level"] > old_level:
        return True  # 升级了
    return False

# ================== 键盘 ==================
def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥚 捡蛋", callback_data="pick_egg"),
         InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🧹 清扫鸟粪", callback_data="clean_dung"),
         InlineKeyboardButton("💰 出售全部", callback_data="sell_all")],
        [InlineKeyboardButton("🛒 购买虎皮🦜", callback_data="buy_bird")],
    ])

# ================== 面板 ==================
async def send_panel(update: Update, edit: bool = False):
    user = get_user_data(update.effective_user.id)
    text = (
        f"🐦 **飞鸟牧场**（{user['level']}级）\n"
        f"💰 金币：{user['gold']}  |  🌾 鸟粮：{user['feed']}\n"
        f"🐦 鹦鹉：{user['birds']}只  |  🏠 鸟窝：{user['nests']}/4\n"
        f"⭐ 经验：{user['exp']}/{LEVEL_EXP[user['level']]}"
    )
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except:
        pass

# ================== 群内活跃经验系统 ==================
async def group_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    now = datetime.now().timestamp()
    user = get_user_data(user_id)
    
    # 每人每 8 秒最多获得一次经验（防止刷屏）
    if now - user.get("last_active", 0) < 8:
        return
    
    user["last_active"] = now
    
    # 随机获得经验
    if random.random() < 0.65:  # 65% 概率获得经验
        exp_gain = random.randint(8, 20)
        leveled_up = add_exp(user_id, exp_gain)
        
        if leveled_up:
            await update.message.reply_text(
                f"🎉 恭喜！你在群内活跃升级了！\n"
                f"飞鸟牧场升到 **{user['level']}级**！\n+200 金币奖励",
                parse_mode='Markdown'
            )
        save_data()

# ================== 按钮 & 命令（已适配等级加成） ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user_data(user_id)
    data = query.data
    await query.answer("✅ 操作成功！")

    try:
        if data == "pick_egg":
            reward = 80 + user['birds'] * 25 + user['level'] * 10   # 等级加成
            user['gold'] += reward
            await query.message.reply_text(f"✅ 捡蛋成功！获得 {reward} 金币")

        elif data == "rush_produce":
            user['feed'] = min(user['feed'] + 18, 300)
            await query.message.reply_text("✅ 赶产成功！鸟粮 +18")

        elif data == "clean_dung":
            add_exp(user_id, 25)
            await query.message.reply_text("✅ 清扫成功！获得 25 经验")

        elif data == "sell_all":
            earnings = user['birds'] * (110 + user['level'] * 15)
            user['gold'] += earnings
            await query.message.reply_text(f"✅ 出售成功！获得 {earnings} 金币")

        elif data == "buy_bird":
            cost = 700 - user['level'] * 20
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

# 其他命令...
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！在群里多聊天就能获得经验升级哦～")
    await send_panel(update)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['gold'], reverse=True)[:10]
    text = "🏆 **飞鸟牧场全球排行榜** 🏆\n\n"
    for i, (uid, d) in enumerate(sorted_users, 1):
        text += f"{i}. 用户{uid[-4:]} — 💰 {d['gold']}金币（{d['level']}级）\n"
    await update.message.reply_text(text, parse_mode='Markdown')

# ================== 初始化 ==================
async def post_init(application: Application):
    commands = [BotCommand(cmd, desc) for cmd, desc in [
        ("start", "启动飞鸟牧场"), ("open", "打开我的鸟场"), ("pick", "捡蛋"),
        ("rush", "赶产"), ("clean", "清扫鸟粪"), ("sell", "出售全部"),
        ("buy", "购买虎皮鹦鹉"), ("rank", "查看排行榜"),
        ("checkin", "签到"), ("help", "帮助")
    ]]
    await application.bot.set_my_commands(commands)

def main():
    load_data()
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # 命令
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", lambda u,c: send_panel(u)))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("checkin", lambda u,c: (get_user_data(u.effective_user.id)['feed']+=25, save_data(), u.message.reply_text("签到成功！+25鸟粮"))[2]))
    
    # 按钮
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # 群内活跃经验（关键！）
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP), group_activity))

    app.add_error_handler(lambda u,c: logger.error(f"Error: {c.error}"))
    
    logger.info("🚀 飞鸟牧场（带群活跃系统）启动成功！")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
