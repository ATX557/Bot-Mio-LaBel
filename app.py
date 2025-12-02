import os
import logging
import random
import textwrap
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# ----- Configuration -----
PREFIX = os.getenv("PREFIX", "!")
TOKEN = os.getenv("DISCORD_TOKEN")  # Set this in your environment or .env
WELCOME_CHANNEL = os.getenv("WELCOME_CHANNEL", "general")  # channel name used for welcomes
OWNER_ID = int(os.getenv("OWNER_ID", "0")) if os.getenv("OWNER_ID") else None

# ----- Logging -----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ----- Intents -----
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # required for member join events and member-related commands

# ----- Bot Setup -----
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    description="NekoNi2 - upgraded featureful Discord bot",
    help_command=None,  # we'll use a simple custom help
)


# ----- Events -----
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Guilds: {len(bot.guilds)}")
    # set presence
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help | {len(bot.guilds)} servers"))
    print(f"Ready! Logged in as: {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_member_join(member: discord.Member):
    # Try to send a welcome message to a channel with name WELCOME_CHANNEL
    guild = member.guild
    channel = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL)
    if channel and channel.permissions_for(guild.me).send_messages:
        await channel.send(f"Welcome {member.mention} to **{guild.name}**! Say hi 👋")
    else:
        logger.debug(f"Welcome channel '{WELCOME_CHANNEL}' not found or no permission in guild {guild.name}")


# ----- Error Handling -----
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    # Unwrap CommandInvokeError
    if isinstance(error, commands.CommandInvokeError) and error.original:
        error = error.original

    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("You do not have permission to run this command.", mention_author=False)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.reply("I don't have the required permissions to do that.", mention_author=False)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"Missing argument: {error.param.name}", mention_author=False)
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("Bad argument provided.", mention_author=False)
    elif isinstance(error, commands.CommandNotFound):
        # silently ignore unknown commands or optionally inform
        return
    else:
        logger.exception("Unhandled command error")
        await ctx.reply("An unexpected error occurred. The error has been logged.", mention_author=False)


# ----- Utilities -----
def format_timedelta(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


# ----- Basic Commands -----
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    """Show bot latency."""
    ws_latency = round(bot.latency * 1000)
    await ctx.reply(f"Pong! WebSocket latency: {ws_latency}ms", mention_author=False)


@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx: commands.Context, *, message: str):
    """Make the bot say something (requires Manage Messages)."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    await ctx.send(message)


@bot.command(name="avatar")
async def avatar(ctx: commands.Context, member: discord.Member = None):
    """Show a user's avatar."""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member}'s avatar")
    embed.set_image(url=member.display_avatar.url)
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="serverinfo")
async def serverinfo(ctx: commands.Context):
    """Show info about the server."""
    g = ctx.guild
    embed = discord.Embed(title=g.name, description=g.description or "", timestamp=datetime.utcnow())
    embed.set_thumbnail(url=g.icon.url if g.icon else discord.Embed.Empty)
    fields = {
        "Server ID": g.id,
        "Owner": str(g.owner),
        "Members": g.member_count,
        "Text Channels": len(g.text_channels),
        "Voice Channels": len(g.voice_channels),
        "Roles": len(g.roles),
        "Created at": format_timedelta(g.created_at),
    }
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=True)
    await ctx.reply(embed=embed, mention_author=False)


@bot.command(name="userinfo", aliases=["user"])
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    """Show info about a user."""
    member = member or ctx.author
    embed = discord.Embed(title=str(member), timestamp=datetime.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Bot", value=member.bot, inline=True)
    embed.add_field(name="Top role", value=member.top_role.mention if member.top_role else "None", inline=True)
    embed.add_field(name="Joined", value=format_timedelta(member.joined_at) if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Created", value=format_timedelta(member.created_at), inline=True)
    await ctx.reply(embed=embed, mention_author=False)


# ----- Moderation -----
@bot.command(name="clear", aliases=["purge", "clean"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx: commands.Context, amount: int = 10):
    """Delete messages (default 10)."""
    if amount < 1 or amount > 200:
        return await ctx.reply("Please provide a number between 1 and 200.", mention_author=False)
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to remove the command message too
    await ctx.channel.send(f"Deleted {len(deleted)-1} messages.", delete_after=5)


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member."""
    await member.kick(reason=reason)
    await ctx.reply(f"Kicked {member} - {reason}", mention_author=False)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member."""
    await member.ban(reason=reason)
    await ctx.reply(f"Banned {member} - {reason}", mention_author=False)


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx: commands.Context, user_id: int):
    """Unban by user ID."""
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.reply(f"Unbanned {user}.", mention_author=False)


@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx: commands.Context, member: discord.Member, role: discord.Role):
    """Add a role to a member."""
    await member.add_roles(role)
    await ctx.reply(f"Added role {role.name} to {member.mention}.", mention_author=False)


@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def removerole(ctx: commands.Context, member: discord.Member, role: discord.Role):
    """Remove a role from a member."""
    await member.remove_roles(role)
    await ctx.reply(f"Removed role {role.name} from {member.mention}.", mention_author=False)


# ----- Fun Commands -----
EIGHT_BALL_ANSWERS = [
    "It is certain.", "Without a doubt.", "You may rely on it.",
    "Ask again later.", "Better not tell you now.", "Very doubtful.",
    "My sources say no.", "Signs point to yes.", "Absolutely!", "No way."
]


@bot.command(name="8ball", aliases=["eightball"])
async def eightball(ctx: commands.Context, *, question: str):
    """Magic 8-ball."""
    answer = random.choice(EIGHT_BALL_ANSWERS)
    await ctx.reply(f"🎱 Question: {question}\nAnswer: **{answer}**", mention_author=False)


@bot.command(name="coin")
async def coin(ctx: commands.Context):
    """Flip a coin."""
    await ctx.reply(random.choice(["Heads 🪙", "Tails 🪙"]), mention_author=False)


@bot.command(name="roll")
async def roll(ctx: commands.Context, sides: int = 6):
    """Roll a dice. Use roll 20 for d20."""
    if sides < 2 or sides > 1000000:
        return await ctx.reply("Please choose a number between 2 and 1,000,000.", mention_author=False)
    result = random.randint(1, sides)
    await ctx.reply(f"🎲 d{sides} -> **{result}**", mention_author=False)


# ----- Simple Help Command -----
@bot.command(name="help")
async def help_command(ctx: commands.Context):
    """Show help information."""
    p = PREFIX
    help_text = textwrap.dedent(
        f"""
        NekoNi2 - commands
        Prefix: {p}

        Moderation:
          {p}clear <amount>       - Delete messages (requires Manage Messages)
          {p}kick <member> [reason]
          {p}ban <member> [reason]
          {p}unban <user_id>

        Utility:
          {p}ping
          {p}say <message>        - (requires Manage Messages)
          {p}avatar [member]
          {p}userinfo [member]
          {p}serverinfo

        Fun:
          {p}8ball <question>
          {p}coin
          {p}roll [sides]

        Advanced:
          {p}addrole <member> <role>      - requires Manage Roles
          {p}removerole <member> <role>

        Use @{bot.user} as a mention or the prefix to run commands.
        """
    )
    await ctx.reply(help_text, mention_author=False)


# ----- Run Bot -----
if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN is not set. Please set the DISCORD_TOKEN environment variable or create a .env file.")
        print("DISCORD_TOKEN is not set. Please set the DISCORD_TOKEN environment variable or create a .env file.")
    else:
        bot.run(TOKEN)
