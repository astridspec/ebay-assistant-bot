import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

access_role = "Verified"

@bot.event
async def on_ready():
    print(f"Im ready to assist!, {bot.user.name}!")

@bot.event
async def on_member_join(member):
    print(f"{member} joined the server")  # debug check

    channel_id = 1488217897628340405  # replace this
    channel = bot.get_channel(channel_id)

    if channel is None:
        print("Channel not found")
        return

    embed = discord.Embed(
        title="📦 Welcome to Ebay Warehouse",
        description=f"Welcome to Ebay Warehouse Team, {member.mention}!\n\nYou are now part of the operations team.",
        color=discord.Color.blue()
    )

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    embed.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExdW1jd3piNXNxa3UwaWdhNGs4NzNpYzQxZDBtNTlyMGdtbWV6cWk3OSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3orieQHmkjxSiLGC08/giphy.gif")

    try:
        await channel.send(embed=embed)
        print("Welcome embed sent successfully")
    except Exception as e:
        print(f"Failed to send embed: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}, I am your Warehouse Assistant!")

@bot.command()
async def verify(ctx):
    role = discord.utils.get(ctx.guild.roles, name=access_role)

    if role:
        # check if user already has the role
        if role in ctx.author.roles:
            await ctx.send(f"{ctx.author.mention} You are already verified.")
            return

        await ctx.author.add_roles(role)

        # send confirmation
        msg = await ctx.send(f"{ctx.author.mention} You are now verified")

        # delete user's command message
        await ctx.message.delete()

        # optional: auto-delete bot message after 5 seconds
        await msg.delete(delay=1)

    else:
        await ctx.send("Role doesn't exist!")

@bot.command()
@commands.has_permissions(administrator=True)
async def post(ctx, channel: discord.TextChannel, *, content):

    parts = [part.strip() for part in content.split("|")]

    # REQUIRED
    if len(parts) < 2:
        await ctx.send("Use this format:\n`!post #channel title | message`\n(Optional: add `| image_link` or attach an image)")
        return

    title = parts[0]
    message = parts[1]

    # OPTIONAL image
    image_url = parts[2] if len(parts) >= 3 else None

    embed = discord.Embed(
        title=title,
        description=message,
        color=discord.Color.blue()
    )

    embed.set_footer(text="Ebay Warehouse")

    # 🔥 1. Check attachment first
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.content_type and attachment.content_type.startswith("image/"):
            embed.set_image(url=attachment.url)

    # 🔥 2. Check link (optional)
    elif image_url:
        if image_url.startswith("http"):
            embed.set_image(url=image_url)

    await channel.send(embed=embed)

    try:
        await ctx.message.delete()
    except:
        pass


import discord
from discord.ext import commands
from datetime import datetime, timezone

PING_CHANNEL_ID = 1488409847798956103

@bot.command()
@commands.has_permissions(administrator=True)
async def listing(
    ctx,
    channel: discord.TextChannel = None,
    number: int = None,
    user: discord.Member = None
):
    if channel is None or number is None or user is None:
        await ctx.send("Use this format: `!listing #channel 38 @user`")
        return

    # Use UTC and let Discord convert it for each viewer
    now = datetime.now(timezone.utc)
    unix_timestamp = int(now.timestamp())

    embed = discord.Embed(
        title="Listing Status",
        color=discord.Color.blue()
    )

    embed.add_field(name="Date & Time", value=f"<t:{unix_timestamp}:F>", inline=False)
    embed.add_field(name="No. of Listing", value=str(number), inline=False)

    try:
        sent_message = await channel.send(embed=embed)
        await sent_message.add_reaction("⏳")
        await sent_message.add_reaction("💸")
    except Exception as e:
        await ctx.send(f"⚠️ Failed to post listing in {channel.mention}: {e}")
        return

    ping_channel = bot.get_channel(PING_CHANNEL_ID)
    if ping_channel is None:
        try:
            ping_channel = await bot.fetch_channel(PING_CHANNEL_ID)
        except Exception as e:
            await ctx.send(f"⚠️ Ping channel not found or inaccessible: {e}")
            return

    try:
        await ping_channel.send(
            f"📦 **New Listing Products for you!**\n"
            f"👤 Staff: {user.mention}\n"
            f"📊 Listings: {number}\n"
            f"📅 Created: <t:{unix_timestamp}:F>"
        )
    except Exception as e:
        await ctx.send(f"⚠️ Failed to send ping message: {e}")
        return

    await ctx.send(f"✅ Listing posted in {channel.mention}")



import discord
from discord.ext import commands

WORKSPACE_COMMAND_CHANNEL_ID = 1488247610346045520  # workspace creation channel ID
WORKSPACE_CATEGORY_ID = 1488245643502686439         # category ID where workspaces are created
ALLOWED_ROLE_NAME = "Listing Staff"

@bot.command()
async def workspace(ctx):
    # Only allow command in the workspace creation channel
    if ctx.channel.id != WORKSPACE_COMMAND_CHANNEL_ID:
        await ctx.send("You can only use this command in the workspace creation channel.")
        return

    # Role check
    allowed_role = discord.utils.get(ctx.guild.roles, name=ALLOWED_ROLE_NAME)
    if allowed_role is None:
        await ctx.send("The required role was not found. Please check the role name.")
        return

    if allowed_role not in ctx.author.roles:
        await ctx.send("You cannot use this command. This is only for Listing Staff.")
        return

    guild = ctx.guild
    user = ctx.author

    # Get category
    category = guild.get_channel(WORKSPACE_CATEGORY_ID)
    if category is None or not isinstance(category, discord.CategoryChannel):
        await ctx.send("Workspace category not found. Check the category ID.")
        return

    # Prevent duplicate workspace
    for ch in category.text_channels:
        if ch.topic == f"workspace_owner:{user.id}":
            await ctx.send(f"You already have a workspace: {ch.mention}")
            return

    # Safe channel name
    safe_name = "".join(c.lower() for c in user.display_name if c.isalnum() or c == " ").replace(" ", "-")
    if not safe_name:
        safe_name = f"user-{user.id}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        guild.owner: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True
        )
    }

    channel = await guild.create_text_channel(
        name=f"ws-{safe_name}",
        category=category,
        overwrites=overwrites,
        topic=f"workspace_owner:{user.id}",
        reason=f"Workspace created for {user}"
    )

    await channel.send(
        f"Welcome {user.mention}!\n"
        "This is your private workspace.\n"
        "Only you, the owner, and the bot can access this channel."
    )

    msg = await ctx.send(f"✅ Your workspace has been created: {channel.mention}")

    try:
        await ctx.message.delete()
    except:
        pass

    await msg.delete(delay=1)

bot.run(token, log_handler=handler, log_level=logging.DEBUG)

