import os
import discord
from discord.ext import commands
import datetime, asyncio, re
from collections import defaultdict
from config import *

# ══════════════════════════════════════════
#   🛡️ RAVEN — بوت الحماية والموديريشن
#   Coded by RAVEN
# ══════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── تتبع الأنشطة ────────────────────────
spam_tracker  = defaultdict(list)   # {user_id: [timestamps]}
raid_tracker  = []                  # [join_timestamps]
warn_db       = defaultdict(int)    # {user_id: warn_count}
URL_PATTERN   = re.compile(r"https?://|discord\.gg/", re.IGNORECASE)


# ─── دالة اللوق ──────────────────────────
async def log_action(guild, title, description, color=0xe74c3c):
    ch = guild.get_channel(MOD_LOG_CHANNEL_ID)
    if ch:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=CODED_BY)
        await ch.send(embed=embed)


# ══ حماية Anti-Spam ══════════════════════
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return await bot.process_commands(message)

    member = message.author
    now    = datetime.datetime.utcnow().timestamp()

    # Anti-Link للأعضاء الجدد
    if ANTI_LINK_ENABLED:
        member_role = message.guild.get_role(MEMBER_ROLE_ID)
        has_member  = member_role in member.roles if member_role else True
        if not has_member and URL_PATTERN.search(message.content):
            await message.delete()
            await message.channel.send(
                f"{member.mention} ❌ غير مسموح بالروابط | Links not allowed!",
                delete_after=5
            )
            await log_action(message.guild,
                "🔗 Anti-Link",
                f"**{member}** حاول إرسال رابط قبل قبول القوانين."
            )
            return

    # Anti-Spam
    spam_tracker[member.id] = [t for t in spam_tracker[member.id] if now - t < 5]
    spam_tracker[member.id].append(now)

    if len(spam_tracker[member.id]) >= ANTI_SPAM_LIMIT:
        mute_role = message.guild.get_role(MUTE_ROLE_ID)
        if mute_role and mute_role not in member.roles:
            await member.add_roles(mute_role)
            await message.channel.send(
                f"{member.mention} 🔇 تم كتمك بسبب السبام | Muted for spam!",
                delete_after=10
            )
            await log_action(message.guild,
                "🔇 Anti-Spam — كتم تلقائي",
                f"**{member}** ({member.id}) تم كتمه بسبب السبام.\nرسائل: {len(spam_tracker[member.id])} في 5 ثواني"
            )
            spam_tracker[member.id] = []
            await asyncio.sleep(3600)
            await member.remove_roles(mute_role)

    await bot.process_commands(message)


# ══ حماية Anti-Raid ══════════════════════
@bot.event
async def on_member_join(member: discord.Member):
    now = datetime.datetime.utcnow().timestamp()
    raid_tracker.append(now)

    # احسب الانضمامات في آخر دقيقة
    recent = [t for t in raid_tracker if now - t < 60]
    if len(recent) >= ANTI_RAID_JOINS:
        await log_action(member.guild,
            "🚨 Anti-Raid — تحذير!",
            f"تم رصد {len(recent)} انضمام في أقل من دقيقة!\nآخر انضمام: **{member}**\n⚠️ فعّل الـ Verification Level يدوياً إذا تأكدت من الريد.",
            color=0xff0000
        )

    # تحقق من عمر الحساب
    account_age = (datetime.datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
    if account_age < NEW_ACCOUNT_DAYS:
        await log_action(member.guild,
            "⚠️  حساب مشبوه | Suspicious Account",
            f"**{member}** ({member.id})\nعمر الحساب: **{account_age} يوم** فقط!\n*Account age: {account_age} days only!*",
            color=0xf39c12
        )


# ══ لوق حذف الرسائل ══════════════════════
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    await log_action(message.guild,
        "🗑️  رسالة محذوفة | Message Deleted",
        f"**الكاتب | Author:** {message.author} ({message.author.id})\n"
        f"**القناة | Channel:** {message.channel.mention}\n"
        f"**المحتوى | Content:** {message.content[:500] or '*فارغة | Empty*'}",
        color=0xe67e22
    )


# ══ لوق تعديل الرسائل ════════════════════
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    await log_action(before.guild,
        "✏️  رسالة معدّلة | Message Edited",
        f"**العضو | Member:** {before.author} ({before.author.id})\n"
        f"**القناة | Channel:** {before.channel.mention}\n"
        f"**قبل | Before:** {before.content[:300]}\n"
        f"**بعد | After:** {after.content[:300]}",
        color=0x3498db
    )


# ══ أوامر الموديريشن ══════════════════════

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def cmd_warn(ctx, member: discord.Member, *, reason="لا يوجد سبب | No reason"):
    warn_db[member.id] += 1
    count = warn_db[member.id]

    await ctx.send(
        f"⚠️ **{member}** تم تحذيره | warned.\n"
        f"السبب | Reason: {reason}\n"
        f"عدد التحذيرات | Warnings: **{count}/4**"
    )
    await log_action(ctx.guild,
        f"⚠️ تحذير | Warning #{count}",
        f"**العضو:** {member} ({member.id})\n**المشرف:** {ctx.author}\n**السبب:** {reason}"
    )

    mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
    if count == 2 and mute_role:
        await member.add_roles(mute_role)
        await ctx.send(f"🔇 **{member}** تم كتمه لساعة | Muted for 1 hour.")
        await asyncio.sleep(3600)
        await member.remove_roles(mute_role)
    elif count == 3:
        await member.kick(reason=f"3 تحذيرات | {reason}")
        await ctx.send(f"👟 **{member}** تم كيكه | Kicked.")
    elif count >= 4:
        await member.ban(reason=f"4 تحذيرات | {reason}")
        await ctx.send(f"🔨 **{member}** تم بانه | Banned.")


@bot.command(name="mute")
@commands.has_permissions(kick_members=True)
async def cmd_mute(ctx, member: discord.Member, minutes: int = 60, *, reason="لا يوجد سبب"):
    role = ctx.guild.get_role(MUTE_ROLE_ID)
    if not role:
        return await ctx.send("❌ رول الكتم غير موجود | Mute role not found.")
    await member.add_roles(role)
    await ctx.send(f"🔇 تم كتم **{member}** لـ {minutes} دقيقة | Muted for {minutes} min.")
    await log_action(ctx.guild, "🔇 كتم | Mute",
        f"**العضو:** {member}\n**المشرف:** {ctx.author}\n**المدة:** {minutes} دقيقة\n**السبب:** {reason}")
    await asyncio.sleep(minutes * 60)
    await member.remove_roles(role)


@bot.command(name="unmute")
@commands.has_permissions(kick_members=True)
async def cmd_unmute(ctx, member: discord.Member):
    role = ctx.guild.get_role(MUTE_ROLE_ID)
    if role:
        await member.remove_roles(role)
    await ctx.send(f"🔊 تم رفع الكتم عن **{member}** | Unmuted.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def cmd_kick(ctx, member: discord.Member, *, reason="لا يوجد سبب"):
    await member.kick(reason=reason)
    await ctx.send(f"👟 تم كيك **{member}** | Kicked.")
    await log_action(ctx.guild, "👟 كيك | Kick",
        f"**العضو:** {member}\n**المشرف:** {ctx.author}\n**السبب:** {reason}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def cmd_ban(ctx, member: discord.Member, *, reason="لا يوجد سبب"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 تم بان **{member}** | Banned.")
    await log_action(ctx.guild, "🔨 بان | Ban",
        f"**العضو:** {member}\n**المشرف:** {ctx.author}\n**السبب:** {reason}")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def cmd_unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ تم رفع البان عن **{user}** | Unbanned.")


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def cmd_clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 تم حذف {amount} رسالة | Deleted {amount} messages.", delete_after=5)


@bot.command(name="warns")
async def cmd_warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    count  = warn_db[member.id]
    await ctx.send(f"⚠️ **{member}** لديه {count} تحذير/ات | has {count} warning(s).")


@bot.event
async def on_ready():
    print(f"✅  [{SERVER_NAME}] Protection Bot شغّال: {bot.user}")

bot.run(os.getenv('DISCORD_TOKEN'))
