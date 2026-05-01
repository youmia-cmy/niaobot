import logging
import os
import json
import random
from datetime import date, time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ChatMemberHandler, MessageHandler, filters
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# ====================== 配置 ======================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ 请设置 TELEGRAM_BOT_TOKEN")

DATA_FILE = "user_data.json"
GROUP_FILE = "groups.json"

user_data = {}
group_ids = set()

# ====================== 数据函数 ======================
def load_data():
    global user_data, group_ids
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
        if os.path.exists(GROUP_FILE):
            with open(GROUP_FILE, "r", encoding="utf-8") as f:
                group_ids = set(json.load(f))
    except Exception as e:
        logger.error(f"加载数据失败: {e}")

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        with open(GROUP_FILE, "w", encoding="utf-8") as f:
            json.dump(list(group_ids), f)
    except Exception as e:
        logger.error(f"保存数据失败: {e}")

def get_user_data(user_id: int, effective_user=None):
    uid = str(user_id)
    today = str(date.today())
    if uid not in user_data:
        user_data[uid] = {
            "feed": 50, "birds": 1, "nests": 4,
            "level": 1, "exp": 0, "last_active": 0,
            "combat": 100, "stamina": 0, "strength": 0,
            "intelligence": 0, "agility": 0,
            "feed_count_today": 0, "pick_egg_today": 0,
            "rush_today": 0, "clean_today": 0,
            "chat_exp_today": 0, "last_date": today,
            "last_checkin": "", "nickname": ""
        }
    if user_data[uid].get("last_date") != today:
        user_data[uid].update({
            "feed_count_today": 0, "pick_egg_today": 0,
            "rush_today": 0, "clean_today": 0,
            "chat_exp_today": 0, "last_date": today
        })
    if effective_user:
        user_data[uid]["nickname"] = effective_user.full_name or effective_user.first_name or f"用户{uid[-4:]}"
    return user_data[uid]

def get_title(level: int) -> str:
    """获取等级称号"""
    if 1 <= level <= 9:
        return "菜鸟"
    elif 10 <= level <= 30:
        return "银鸟"
    elif 31 <= level <= 40:
        return "金鸟"
    elif 41 <= level <= 50:
        return "钛合金鸟"
    elif 51 <= level <= 60:
        return "乌金鸟"
    elif 61 <= level <= 70:
        return "鸟王"
    elif 71 <= level <= 80:
        return "鸟神"
    elif 81 <= level <= 90:
        return "鸟帝"
    else:
        return "至尊鸟帝"

def add_exp(user_id: int, amount: int):
    """增加经验并处理升级"""
    user = get_user_data(user_id)
    user["exp"] += amount
    old_level = user["level"]
    
    def get_exp_required(lv: int) -> int:
        return 500 * lv * (lv + 1) // 2
    
    while user["level"] < 99 and user["exp"] >= get_exp_required(user["level"]):
        user["level"] += 1
        user["combat"] *= 2
        user["stamina"] += 25
        user["strength"] += 15
        user["intelligence"] += 15
        user["agility"] += 15
    
    return user["level"] > old_level

def deduct_exp(user_id: int, amount: int):
    """扣除经验并处理降级（最低1级）"""
    user = get_user_data(user_id)
    user["exp"] = max(0, int(user["exp"] - amount))
    old_level = user["level"]
    
    def get_exp_required(lv: int) -> int:
        return 500 * lv * (lv + 1) // 2

    while user["level"] > 1 and user["exp"] < get_exp_required(user["level"] - 1):
        user["level"] -= 1
        user["combat"] = max(100, int(user["combat"] / 2))
        user["stamina"] = max(0, user["stamina"] - 25)
        user["strength"] = max(0, user["strength"] - 15)
        user["intelligence"] = max(0, user["intelligence"] - 15)
        user["agility"] = max(0, user["agility"] - 15)

    return user["level"] < old_level

def calculate_combat(user):
    if user["birds"] == 0:
        return 0
    per = {"stamina": 25, "strength": 18, "intelligence": 20, "agility": 15}
    base = user["combat"] + (per["strength"] * user["birds"]) * 1.2 + (per["agility"] * user["birds"]) * 0.8
    return int(base * (1 + (per["intelligence"] * user["birds"]) / 200))

def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥚 捡蛋", callback_data="pick_egg"), InlineKeyboardButton("⚡ 赶产", callback_data="rush_produce")],
        [InlineKeyboardButton("🌾 喂养", callback_data="feed_birds"), InlineKeyboardButton("🧹 清扫", callback_data="clean_dung")],
        [InlineKeyboardButton("⚔️ PK", callback_data="pk_menu")],
        [InlineKeyboardButton("🦜 官网", callback_data="official_web")],
    ])

def pk_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 随机匹配", callback_data="pk_random")],
        [InlineKeyboardButton("👤 指定挑战", callback_data="pk_target")],
        [InlineKeyboardButton("← 返回", callback_data="back_to_main")]
    ])

async def send_panel(update: Update, edit: bool = False):
    user = get_user_data(update.effective_user.id, update.effective_user)
    combat = calculate_combat(user)
    title = get_title(user['level'])
    
    text = f"🦜 **飞鸟牧场**（{user['level']}级 {title}）\n🌾 鸟粮：{user['feed']}\n🦜 鹦鹉：{user['birds']} 只  |  ⚔️ 战斗力：{combat}\n⭐ 经验：{user['exp']}"
    
    markup = build_keyboard()
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"面板错误: {e}")

# ====================== 自动删除消息 ======================
async def delete_later(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(context.job.data['chat_id'], context.job.data['message_id'])
    except:
        pass

# ====================== 群聊经验 ======================
async def group_chat_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    user = get_user_data(update.effective_user.id)
    if user.get("chat_exp_today", 0) >= 30:
        return
    exp_gain = random.randint(1, 3)
    user["chat_exp_today"] += exp_gain
    if add_exp(update.effective_user.id, exp_gain):
        msg = await update.message.reply_text(f"🎉 升级了！当前 {user['level']} 级 {get_title(user['level'])}", quote=True)
        context.job_queue.run_once(delete_later, 2, data={'chat_id': msg.chat_id, 'message_id': msg.message_id})
    save_data()

# ====================== 排行榜 ======================
async def show_rank(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    if not user_data:
        await (update.callback_query.message.reply_text if update.callback_query else update.message.reply_text)("🏆 目前还没有玩家")
        return

    sorted_users = sorted(user_data.items(), key=lambda x: calculate_combat(x[1]), reverse=True)
    total = len(sorted_users)
    per_page = 10
    total_pages = (total + per_page - 1) // per_page

    start = page * per_page
    end = start + per_page
    page_users = sorted_users[start:end]

    text = f"🏆 **飞鸟牧场战斗力排行榜**（第{page+1}/{total_pages}页）\n\n"
    for i, (uid, d) in enumerate(page_users, start + 1):
        nickname = d.get("nickname", f"用户{uid[-4:]}")
        combat = calculate_combat(d)
        title = get_title(d.get('level', 1))
        text += f"`{i:2d}.` **{nickname}** — {d.get('level',1)}级{title} ⚔️ {combat}\n"

    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"rank_page_{page-1}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"rank_page_{page+1}"))
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("← 返回牧场", callback_data="back_to_main")])

    markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

# ====================== PK功能 ======================
async def pk_random_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user, query=None):
    my_id = str(update.effective_user.id)
    my_power = calculate_combat(user)

    other_players = [uid for uid in user_data.keys() if uid != my_id]
    if not other_players:
        text = "⚔️ **随机PK**\n\n😔 目前没有其他玩家可以匹配～"
        if query:
            await query.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
        return

    opponent_id = random.choice(other_players)
    opponent = get_user_data(int(opponent_id))
    opponent_power = calculate_combat(opponent)
    opponent_name = opponent.get("nickname", f"玩家{opponent_id[-4:]}")

    if my_power > opponent_power:
        exp_plunder = int(opponent["exp"] * 0.05)
        combat_plunder = int(opponent_power * 0.05)

        leveled_up = add_exp(update.effective_user.id, exp_plunder)
        user["combat"] += combat_plunder

        leveled_down = deduct_exp(int(opponent_id), exp_plunder)
        opponent["combat"] = max(100, int(opponent["combat"] - combat_plunder))

        result_text = f"🎉 **胜利！** 你击败了 **{opponent_name}**！\n掠夺了 {exp_plunder} 经验和 {combat_plunder} 战斗力"
        if leveled_up:
            result_text += f"\n🎉 你升级到了 {user['level']} 级 {get_title(user['level'])}！"
    else:
        result_text = f"😔 **失败...** 对手 **{opponent_name}** 战力更高"

    text = f"⚔️ **随机PK**\n\n{result_text}\n\n你的战力：**{my_power}** | 对手战力：**{opponent_power}**"
    
    if query:
        await query.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    save_data()

async def pk_target_fight(update: Update, user, target_id: int):
    if target_id == update.effective_user.id:
        await update.message.reply_text("❌ 不能挑战自己")
        return
    target = get_user_data(target_id)
    my_power = calculate_combat(user)
    target_power = calculate_combat(target)
    target_name = target.get("nickname", f"玩家{str(target_id)[-4:]}")

    if my_power > target_power:
        exp_plunder = int(target["exp"] * 0.05)
        combat_plunder = int(target_power * 0.05)

        leveled_up = add_exp(update.effective_user.id, exp_plunder)
        user["combat"] += combat_plunder

        leveled_down = deduct_exp(target_id, exp_plunder)
        target["combat"] = max(100, int(target["combat"] - combat_plunder))

        result = f"🎉 胜利！你掠夺了 {exp_plunder} 经验和 {combat_plunder} 战斗力"
        if leveled_up:
            result += f"\n🎉 你升级到了 {user['level']} 级 {get_title(user['level'])}！"
    else:
        result = "😔 失败，对手战力更高"

    await update.message.reply_text(
        f"⚔️ **指定挑战**\n对手：**{target_name}**\n你的战力：{my_power} | 对手战力：{target_power}\n\n{result}",
        parse_mode='Markdown'
    )
    save_data()

# ====================== 按钮处理器 ======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_data(update.effective_user.id, update.effective_user)
    data = query.data
    await query.answer("✅ 操作成功！")

    if data.startswith("rank_page_"):
        page = int(data.split("_")[-1])
        await show_rank(update, context, page)
        return

    elif data == "pk_menu":
        await query.edit_message_text("⚔️ **请选择PK模式**", reply_markup=pk_keyboard(), parse_mode='Markdown')
        return

    elif data == "pk_random":
        await pk_random_handler(update, context, user, query=query)
        await send_panel(update, edit=True)
        return

    elif data == "pk_target":
        await query.edit_message_text(
            "👤 **指定挑战**\n\n请使用以下命令挑战其他玩家：\n"
            "`/pk <玩家ID>`\n\n"
            "例如：`/pk 123456789`\n\n"
            "可在排行榜中复制玩家ID",
            parse_mode='Markdown'
        )
        return

    elif data == "back_to_main":
        await send_panel(update, edit=True)
        return

    reply = None
    upgrade_msg = None

    if data == "pick_egg":
        if user.get("pick_egg_today", 0) >= 10:
            reply = await query.message.reply_text("❌ 今日捡蛋已达上限（10次）")
        else:
            user["pick_egg_today"] = user.get("pick_egg_today", 0) + 1
            reward = 60 + user['birds'] * 30 + user['level'] * 10
            leveled = add_exp(update.effective_user.id, reward)
            reply = await query.message.reply_text(f"✅ 捡蛋成功！+{reward}经验（今日{user['pick_egg_today']}/10）")
            if leveled:
                upgrade_msg = await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级 {get_title(user['level'])}")

    elif data == "rush_produce":
        if user.get("rush_today", 0) >= 10:
            reply = await query.message.reply_text("❌ 今日赶产已达上限（10次）")
        else:
            user["rush_today"] = user.get("rush_today", 0) + 1
            user['feed'] = min(user['feed'] + 20, 300)
            reply = await query.message.reply_text(f"✅ 赶产成功！+20鸟粮（今日{user['rush_today']}/10）")

    elif data == "feed_birds":
        if user.get("feed_count_today", 0) >= 15:
            reply = await query.message.reply_text("❌ 今日喂养已达上限（15次）")
        elif user['feed'] >= 10:
            user['feed'] -= 10
            user["feed_count_today"] += 1
            exp_gain = random.randint(45, 65)
            leveled = add_exp(update.effective_user.id, exp_gain)
            reply = await query.message.reply_text(f"🌾 喂养成功！+{exp_gain}经验（今日{user['feed_count_today']}/15）")
            if leveled:
                upgrade_msg = await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级 {get_title(user['level'])}")
        else:
            reply = await query.message.reply_text("❌ 鸟粮不足")

    elif data == "clean_dung":
        if user.get("clean_today", 0) >= 15:
            reply = await query.message.reply_text("❌ 今日清扫已达上限（15次）")
        else:
            user["clean_today"] = user.get("clean_today", 0) + 1
            leveled = add_exp(update.effective_user.id, 30)
            reply = await query.message.reply_text(f"✅ 清扫成功！+30经验（今日{user['clean_today']}/15）")
            if leveled:
                upgrade_msg = await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级 {get_title(user['level'])}")

    elif data == "official_web":
        # 官网消息永久保留，不删除
        await query.message.reply_text("🐦 **NIAO官网**\nhttps://www.niaocoin.xyz/", parse_mode='Markdown')

    elif data == "daily_checkin":
        today_str = str(date.today())
        if user.get("last_checkin") == today_str:
            reply = await query.message.reply_text("❌ 你今天已经签到过了")
        else:
            user["last_checkin"] = today_str
            leveled = add_exp(update.effective_user.id, 50)
            reply = await query.message.reply_text("✅ 签到成功！\n+50 经验")
            if leveled:
                upgrade_msg = await query.message.reply_text(f"🎉 升级了！当前 {user['level']} 级 {get_title(user['level'])}")

    # 删除普通操作消息
    if reply:
        context.job_queue.run_once(delete_later, 2, data={'chat_id': reply.chat_id, 'message_id': reply.message_id})
    
    # 删除升级消息
    if upgrade_msg:
        context.job_queue.run_once(delete_later, 2, data={'chat_id': upgrade_msg.chat_id, 'message_id': upgrade_msg.message_id})

    save_data()
    if data not in ["pk_menu", "pk_random", "pk_target", "daily_checkin", "back_to_main"] and not data.startswith("rank_page_"):
        await send_panel(update, edit=True)

# ====================== 命令 ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user_data(update.effective_user.id, update.effective_user)
    await update.message.reply_text("🎉 欢迎来到飞鸟牧场！")
    await send_panel(update)

async def back_to_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_panel(update)

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_rank(update, context, page=0)

async def checkin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_data(update.effective_user.id, update.effective_user)
    today = str(date.today())
    if user.get("last_checkin") == today:
        await update.message.reply_text("❌ 你今天已经签到过了")
        return
    user["last_checkin"] = today
    leveled = add_exp(update.effective_user.id, 50)
    await update.message.reply_text("✅ 签到成功！\n+50 经验")
    if leveled:
        msg = await update.message.reply_text(f"🎉 升级了！当前 {user['level']} 级 {get_title(user['level'])}")
        context.job_queue.run_once(delete_later, 2, data={'chat_id': msg.chat_id, 'message_id': msg.message_id})
    save_data()

async def pk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：`/pk <玩家ID>`\n例如：`/pk 123456789`", parse_mode='Markdown')
        return
    try:
        target_id = int(context.args[0])
        user = get_user_data(update.effective_user.id, update.effective_user)
        await pk_target_fight(update, user, target_id)
    except:
        await update.message.reply_text("❌ 请输入正确的玩家ID")

# ====================== 主函数 ======================
def main():
    load_data()
    app = Application.builder().token(TOKEN).build()

    try:
        app.job_queue.run_daily(daily_checkin_notice, time=time(0, 0, 0))
    except:
        pass

    app.add_handler(ChatMemberHandler(track_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, group_chat_exp), group=1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", send_panel))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("checkin", checkin_cmd))
    app.add_handler(CommandHandler("pk", pk_command))
    app.add_handler(CommandHandler("back", back_to_farm))

    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 飞鸟牧场 Bot 启动成功！（官网消息永久保留 + 升级消息2秒自动删除）")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
