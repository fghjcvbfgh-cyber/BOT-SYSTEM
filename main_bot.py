import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
from config import *

# ══════════════════════════════════════════
#   🪶 RAVEN — بوت القوانين والترحيب والرولات
#   Coded by RAVEN
# ══════════════════════════════════════════

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


# ─── زر القوانين ─────────────────────────
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        btn = Button(
            label="✅  قبلت القوانين | I Accept",
            style=discord.ButtonStyle.danger,
            custom_id="raven_accept_rules"
        )
        btn.callback = self.accept_callback
        self.add_item(btn)

    async def accept_callback(self, interaction: discord.Interaction):
        guild  = interaction.guild
        member = interaction.user
        role   = guild.get_role(MEMBER_ROLE_ID)

        if role and role not in member.roles:
            await member.add_roles(role)
            msg = (
                f"✅ تم قبول القوانين!\n"
                f"مرحباً بك في **{SERVER_NAME}** 🪶\n\n"
                f"✅ Rules accepted! Welcome to **{SERVER_NAME}**"
            )
        else:
            msg = f"لديك الرول بالفعل! | You already have the role."

        await interaction.response.send_message(msg, ephemeral=True)


# ─── إرسال القوانين ──────────────────────
async def send_rules_embed(channel):
    embed = discord.Embed(
        title=f"🪶  {SERVER_NAME} — القوانين | Rules",
        description=(
            f"**جميع القوانين التابعة لـ {SERVER_NAME}**\n"
            f"*All rules of {SERVER_NAME}*\n\n"
            f"{RULES}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"نرجوا منك إتباع جميع القوانين لكي لا يتم محاسبتك.\n"
            f"*Please follow all rules to avoid punishment.*\n\n"
            f"— {SERVER_NAME} Team"
        ),
        color=0x1a1a2e,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text=CODED_BY)
    await channel.send(embed=embed, view=RulesView())


# ─── ترحيب بالأعضاء الجدد ────────────────
@bot.event
async def on_member_join(member: discord.Member):
    # رسالة الترحيب
    welcome_ch = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_ch:
        embed = discord.Embed(
            title=f"🪶  أهلاً بك في {SERVER_NAME}!",
            description=(
                f"مرحباً {member.mention}!\n"
                f"Welcome to **{SERVER_NAME}** 🎉\n\n"
                f"📋 اذهب إلى قناة القوانين واقبلها للحصول على صلاحية الدخول.\n"
                f"*Go to the rules channel and accept them to get access.*"
            ),
            color=0x1a1a2e,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=CODED_BY)
        await welcome_ch.send(embed=embed)

    # لوق الانضمام
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        account_age = (datetime.datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
        warning = "⚠️ حساب جديد مشبوه!" if account_age < NEW_ACCOUNT_DAYS else "✅"
        log_embed = discord.Embed(
            title="📥  عضو جديد انضم | Member Joined",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.add_field(name="العضو | Member", value=f"{member} ({member.id})")
        log_embed.add_field(name="عمر الحساب | Account Age", value=f"{account_age} يوم | days {warning}")
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.set_footer(text=CODED_BY)
        await log_ch.send(embed=log_embed)


# ─── لوق مغادرة الأعضاء ─────────────────
@bot.event
async def on_member_remove(member: discord.Member):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if log_ch:
        embed = discord.Embed(
            title="📤  عضو غادر | Member Left",
            color=0xe74c3c,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="العضو | Member", value=f"{member} ({member.id})")
        embed.set_footer(text=CODED_BY)
        await log_ch.send(embed=embed)


# ─── أوامر الأدمن ────────────────────────
@bot.command(name="rules")
@commands.has_permissions(administrator=True)
async def cmd_rules(ctx):
    """أرسل رسالة القوانين يدوياً"""
    ch = bot.get_channel(RULES_CHANNEL_ID)
    if ch:
        await send_rules_embed(ch)
        await ctx.message.delete()

@bot.command(name="welcome_test")
@commands.has_permissions(administrator=True)
async def cmd_welcome_test(ctx):
    """اختبار رسالة الترحيب"""
    await on_member_join(ctx.author)
    await ctx.message.delete()


@bot.event
async def on_ready():
    print(f"✅  [{SERVER_NAME}] Main Bot شغّال: {bot.user}")
    bot.add_view(RulesView())

import os

# صح ✅
bot.run(os.getenv('DISCORD_TOKEN'))
