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

# welcome chat

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

WORKSPACE_COMMAND_CHANNEL_ID = 1488247610346045520
WORKSPACE_CATEGORY_ID = 1488245643502686439
ALLOWED_ROLE_NAME = "Listing Staff"


@bot.command()
async def workspace(ctx):

    # 🔥 Only allow command in workspace channel
    if ctx.channel.id != WORKSPACE_COMMAND_CHANNEL_ID:

        msg = await ctx.send(
            "You can only use this command in the workspace creation channel."
        )

        await msg.delete(delay=3)

        try:
            await ctx.message.delete()
        except:
            pass

        return

    # 🔥 Role check
    allowed_role = discord.utils.get(
        ctx.guild.roles,
        name=ALLOWED_ROLE_NAME
    )

    if allowed_role is None:

        msg = await ctx.send(
            "The required role was not found."
        )

        await msg.delete(delay=3)

        try:
            await ctx.message.delete()
        except:
            pass

        return

    # 🔥 User doesn't have role
    if allowed_role not in ctx.author.roles:

        msg = await ctx.send(
            "You cannot use this command. This is only for Listing Staff."
        )

        await msg.delete(delay=3)

        try:
            await ctx.message.delete()
        except:
            pass

        return

    guild = ctx.guild
    user = ctx.author

    # 🔥 Get category
    category = guild.get_channel(
        WORKSPACE_CATEGORY_ID
    )

    if category is None or not isinstance(
        category,
        discord.CategoryChannel
    ):

        msg = await ctx.send(
            "Workspace category not found."
        )

        await msg.delete(delay=3)

        try:
            await ctx.message.delete()
        except:
            pass

        return

    # 🔥 Prevent duplicate workspace
    for ch in category.text_channels:

        if ch.topic == f"workspace_owner:{user.id}":

            msg = await ctx.send(
                f"You already have a workspace: {ch.mention}"
            )

            await msg.delete(delay=3)

            try:
                await ctx.message.delete()
            except:
                pass

            return

    # 🔥 Safe channel name
    safe_name = "".join(
        c.lower()
        for c in user.display_name
        if c.isalnum() or c == " "
    ).replace(" ", "-")

    if not safe_name:
        safe_name = f"user-{user.id}"

    # 🔥 Channel permissions
    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

        guild.owner:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
    }

    # 🔥 Create workspace
    channel = await guild.create_text_channel(

        name=f"ws-{safe_name}",

        category=category,

        overwrites=overwrites,

        topic=f"workspace_owner:{user.id}",

        reason=f"Workspace created for {user}"
    )

    # 🔥 Welcome message inside workspace
    await channel.send(
        f"Welcome {user.mention}!\n"
        "This is your private workspace.\n"
        "Only you, the owner, and the bot can access this channel."
    )

    # 🔥 Success message
    msg = await ctx.send(
        f"✅ Your workspace has been created: {channel.mention}"
    )

    # 🔥 Delete BOTH messages
    try:
        await ctx.message.delete()
    except:
        pass

    await msg.delete(delay=1)

from datetime import datetime
from discord.ext import commands
from discord.ui import View, Button
import discord

# 🔥 CONFIG
LISTING_BOARD_CHANNEL_ID = 1488409847798956103
PAYMENT_CHANNEL_ID = 1501548519469879416
LISTING_STAFF_ROLE = "Listing Staff"

# 🔥 STORAGE
listing_storage = {}

# 🔥 ACTIVE CLAIM TRACKER
user_claims = {}

# 🔥 MAX ACTIVE CLAIMS
MAX_ACTIVE_CLAIMS = 2

# 🔥 SKU COUNTER
sku_counter = 1000


# 🔥 COUNT REMAINING LISTINGS
def get_remaining_listings():
    return sum(
        1 for listing in listing_storage.values()
        if not listing["claimed"]
    )


# 🔥 PAYMENT STATUS BUTTON
class PaymentStatusView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Paid",
        style=discord.ButtonStyle.green,
        emoji="💸"
    )
    async def paid_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        embed = interaction.message.embeds[0]

        updated_embed = discord.Embed(
            title=embed.title,
            color=discord.Color.green()
        )

        # 🔥 Keep existing fields
        for field in embed.fields:

            if field.name == "Status":

                updated_embed.add_field(
                    name="Status",
                    value="💸 Paid",
                    inline=False
                )

            else:

                updated_embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=False
                )

        updated_embed.set_footer(
            text="Ebay Warehouse Payment System"
        )

        # 🔥 Remove button after paid
        await interaction.message.edit(
            embed=updated_embed,
            view=None
        )

        await interaction.response.send_message(
            "✅ Marked as paid.",
            ephemeral=True
        )


# 🔥 COMPLETE BUTTON
class CompleteListingView(View):

    def __init__(self, listing_message_id):
        super().__init__(timeout=None)
        self.listing_message_id = listing_message_id

    @discord.ui.button(
        label="Done",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def complete_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        listing_data = listing_storage.get(
            self.listing_message_id
        )

        if listing_data is None:
            await interaction.response.send_message(
                "Listing not found.",
                ephemeral=True
            )
            return

        # 🔒 Only claimer can complete
        if listing_data["claimer"] != interaction.user.id:
            await interaction.response.send_message(
                "You cannot complete this listing.",
                ephemeral=True
            )
            return

        # 🔒 Already completed
        if listing_data["completed"]:
            await interaction.response.send_message(
                "Listing already completed.",
                ephemeral=True
            )
            return

        # 🔥 Mark completed
        listing_data["completed"] = True

        # 🔥 Free claim slot
        user_claims[interaction.user.id] -= 1

        # 🔥 PAYMENT CHANNEL
        payment_channel = bot.get_channel(
            PAYMENT_CHANNEL_ID
        )

        if payment_channel:

            payment_embed = discord.Embed(
                title="📦 Listing Payment Status",
                color=discord.Color.orange()
            )

            payment_embed.add_field(
                name="SKU",
                value=str(listing_data["sku"]),
                inline=False
            )

            payment_embed.add_field(
                name="Claimed By",
                value=interaction.user.mention,
                inline=False
            )

            payment_embed.add_field(
                name="Status",
                value="⏳ Unpaid",
                inline=False
            )

            payment_embed.set_footer(
                text="Ebay Warehouse Payment System"
            )

            payment_view = PaymentStatusView()

            await payment_channel.send(
                embed=payment_embed,
                view=payment_view
            )

        # 🔥 COMPLETED EMBED
        completed_embed = discord.Embed(
            title="✅ Listing Completed",
            description=(
                f"SKU: {listing_data['sku']}\n"
                f"Completed by {interaction.user.mention}"
            ),
            color=discord.Color.green()
        )

        completed_embed.set_footer(
            text="Ebay Warehouse Listing System"
        )

        await interaction.message.edit(
            embed=completed_embed,
            view=None
        )

        await interaction.response.send_message(
            "✅ Listing marked as completed.",
            ephemeral=True
        )


# 🔥 NEW LISTING COMMAND
@bot.command()
@commands.has_permissions(administrator=True)
async def newlisting(ctx, link):

    global sku_counter

    channel = bot.get_channel(
        LISTING_BOARD_CHANNEL_ID
    )

    if channel is None:
        await ctx.send(
            "Listing board channel not found."
        )
        return

    role = discord.utils.get(
        ctx.guild.roles,
        name=LISTING_STAFF_ROLE
    )

    if role is None:
        await ctx.send(
            "Listing Staff role not found."
        )
        return

    remaining = get_remaining_listings() + 1

    embed = discord.Embed(
        title="📦 New Listing Available",
        description=(
            "React with ✅ to claim this listing job.\n\n"
            f"📊 Remaining Listings: {remaining}"
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="SKU",
        value=str(sku_counter),
        inline=False
    )

    embed.set_footer(
        text="Ebay Warehouse Listing System"
    )

    message = await channel.send(
        content=f"{role.mention}",
        embed=embed
    )

    await message.add_reaction("✅")

    # 🔥 STORE DATA
    listing_storage[message.id] = {
        "sku": sku_counter,
        "link": link,
        "claimed": False,
        "completed": False
    }

    sku_counter += 1

    try:
        await ctx.message.delete()
    except:
        pass


# 🔥 CLAIM SYSTEM
@bot.event
async def on_reaction_add(reaction, user):

    if user.bot:
        return

    if str(reaction.emoji) != "✅":
        return

    message = reaction.message

    if message.id not in listing_storage:
        return

    listing_data = listing_storage[message.id]

    if listing_data["claimed"]:
        return

    guild = message.guild

    role = discord.utils.get(
        guild.roles,
        name=LISTING_STAFF_ROLE
    )

    if role not in user.roles:
        return

    # 🔥 CLAIM LIMIT
    current_claims = user_claims.get(
        user.id,
        0
    )

    if current_claims >= MAX_ACTIVE_CLAIMS:

        await message.channel.send(
            f"{user.mention} You already have the maximum of {MAX_ACTIVE_CLAIMS} active listings."
        )

        return

    # 🔥 MARK CLAIMED
    listing_data["claimed"] = True
    listing_data["claimer"] = user.id

    # 🔥 INCREASE CLAIM COUNT
    user_claims[user.id] = current_claims + 1

    # 🔥 FIND WORKSPACE
    workspace_channel = None

    for channel in guild.text_channels:

        if channel.topic == f"workspace_owner:{user.id}":
            workspace_channel = channel
            break

    if workspace_channel is None:

        await message.channel.send(
            f"{user.mention} You do not have a workspace."
        )

        return

    # 🔥 WORKSPACE EMBED
    workspace_embed = discord.Embed(
        title="📦 New Claimed Listing",
        color=discord.Color.blue()
    )

    workspace_embed.add_field(
        name="SKU",
        value=str(listing_data["sku"]),
        inline=False
    )

    workspace_embed.add_field(
        name="Drive Folder",
        value=listing_data["link"],
        inline=False
    )

    workspace_embed.set_footer(
        text="Ebay Warehouse Listing System"
    )

    await workspace_channel.send(
        embed=workspace_embed,
        view=CompleteListingView(message.id)
    )

    # 🔥 REMAINING COUNTER
    remaining = get_remaining_listings()

    claimed_embed = discord.Embed(
        title="📦 Listing Claimed",
        description=(
            f"Claimed by {user.mention}\n\n"
            f"📊 Remaining Listings: {remaining}"
        ),
        color=discord.Color.green()
    )

    claimed_embed.add_field(
        name="SKU",
        value=str(listing_data["sku"]),
        inline=False
    )

    claimed_embed.set_footer(
        text="Ebay Warehouse Listing System"
    )

    await message.edit(
        embed=claimed_embed
    )

    try:
        await message.clear_reactions()
    except:
        pass

bot.run(token, log_handler=handler, log_level=logging.DEBUG)

