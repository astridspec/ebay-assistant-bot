import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==============================
# GOOGLE SHEETS CONFIG
# ==============================

GOOGLE_CREDENTIALS_FILE = "google_credentials.json"
GOOGLE_SHEET_ID = "1_EKLhJhmbGvmPYbhPHsd9b6HjMendAV8w5pVVrurr_E"
GOOGLE_WORKSHEET_NAME = "Listings"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

google_credentials = Credentials.from_service_account_file(
    GOOGLE_CREDENTIALS_FILE,
    scopes=GOOGLE_SCOPES,
)

google_client = gspread.authorize(google_credentials)
spreadsheet = google_client.open_by_key(GOOGLE_SHEET_ID)
worksheet = spreadsheet.worksheet(GOOGLE_WORKSHEET_NAME)


async def add_listing_to_sheet(sku, link):
    """Add a newly-created listing to Google Sheets."""
    def _add():
        worksheet.append_row(
            [str(sku), link, "", "", "", "", "Available", ""],
            value_input_option="USER_ENTERED",
        )

    try:
        await asyncio.to_thread(_add)
        print(f"✅ Google Sheets: SKU {sku} added.")
    except Exception as e:
        print(f"❌ Google Sheets: failed to add SKU {sku}: {e}")


async def update_listing_sheet(
    sku,
    employee=None,
    claimed_at=None,
    submitted_at=None,
    reviewed_by=None,
    status=None,
    paid=None,
):
    """Find a listing by SKU and update only the supplied columns."""
    def _update():
        cell = worksheet.find(str(sku), in_column=1)
        if cell is None:
            raise ValueError(f"SKU {sku} was not found in Google Sheets.")

        row = cell.row
        updates = []

        if employee is not None:
            updates.append((row, 3, str(employee)))

        if claimed_at is not None:
            updates.append((row, 4, str(claimed_at)))

        if submitted_at is not None:
            updates.append((row, 5, str(submitted_at)))

        if reviewed_by is not None:
            updates.append((row, 6, str(reviewed_by)))

        if status is not None:
            updates.append((row, 7, str(status)))

        if paid is not None:
            updates.append((row, 8, str(paid)))

        for target_row, target_col, value in updates:
            worksheet.update_cell(target_row, target_col, value)

    try:
        await asyncio.to_thread(_update)
        print(f"✅ Google Sheets: SKU {sku} updated.")
    except Exception as e:
        print(f"❌ Google Sheets: failed to update SKU {sku}: {e}")


def get_next_sku_from_sheet():
    """Return the next SKU based on the highest numeric SKU already in column A."""
    try:
        values = worksheet.col_values(1)
        numeric_skus = []

        for value in values[1:]:  # skip header
            try:
                numeric_skus.append(int(str(value).strip()))
            except (ValueError, TypeError):
                pass

        return max(numeric_skus, default=999) + 1
    except Exception as e:
        print(f"⚠️ Google Sheets: could not determine next SKU: {e}")
        return 1000


print("✅ Google Sheets connected successfully!")

# Verify the expected worksheet headers before the bot starts.
EXPECTED_HEADERS = [
    "SKU",
    "Drive Link",
    "Employee",
    "Claimed At",
    "Submitted At",
    "Reviewed By",
    "Status",
    "Paid",
]

try:
    current_headers = worksheet.row_values(1)
    if current_headers[:8] != EXPECTED_HEADERS:
        print("⚠️ Google Sheets header mismatch.")
        print(f"   Expected: {EXPECTED_HEADERS}")
        print(f"   Found:    {current_headers[:8]}")
    else:
        print("✅ Google Sheets headers verified.")
except Exception as e:
    print(f"⚠️ Could not verify Google Sheets headers: {e}")


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
LISTING_BOARD_CHANNEL_ID = 1552286157218521169
PAYMENT_CHANNEL_ID = 1552286961266335744
LISTING_STAFF_ROLE = "Listing Staff"

# 🔥 STORAGE
listing_storage = {}

# 🔥 ACTIVE CLAIM TRACKER
user_claims = {}

# 🔥 MAX ACTIVE CLAIMS
MAX_ACTIVE_CLAIMS = 1

# 🔥 SKU COUNTER
sku_counter = get_next_sku_from_sheet()

# REVIEW SYSTEM
REVIEW_CHANNEL_ID = 1552287487119073322 # Replace with your Review Channel ID

MODERATOR_ROLE = "Moderator"  # Role allowed to approve/reject


# 🔥 COUNT REMAINING LISTINGS
def get_remaining_listings():
    return sum(
        1 for listing in listing_storage.values()
        if not listing["claimed"] and not listing.get("approved", False)
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

        # 🔥 Update Google Sheets payment status
        sku = None
        for field in embed.fields:
            if field.name == "SKU":
                sku = field.value
                break

        if sku is not None:
            await update_listing_sheet(
                sku=sku,
                paid="Paid",
                status="Paid"
            )

        # 🔥 Remove button after payment
        await interaction.message.edit(
            embed=updated_embed,
            view=None
        )

        await interaction.response.send_message(
            "✅ Payment marked as paid.",
            ephemeral=True
        )

# 🔥 APPROVE / REJECT REVIEW
class ApproveListingView(View):

    def __init__(self, listing_message_id):
        super().__init__(timeout=None)
        self.listing_message_id = listing_message_id

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def approve_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        # 🔒 Moderator role check
        role = discord.utils.get(
            interaction.guild.roles,
            name=MODERATOR_ROLE
        )

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "You don't have permission to approve listings.",
                ephemeral=True
            )
            return

        listing_data = listing_storage.get(self.listing_message_id)

        if listing_data is None:
            await interaction.response.send_message(
                "Listing not found.",
                ephemeral=True
            )
            return

        if listing_data["approved"]:
            await interaction.response.send_message(
                "This listing has already been approved.",
                ephemeral=True
            )
            return

        # 🔥 Mark approved
        listing_data["approved"] = True
        listing_data["submitted"] = False
        listing_data["rejected"] = False
        listing_data["completed"] = True
        listing_data["reviewed_by"] = interaction.user.id
        listing_data["claimed"] = False

        # 🔥 UPDATE GOOGLE SHEETS
        await update_listing_sheet(
            sku=listing_data["sku"],
            reviewed_by=interaction.user.display_name,
            status="Approved",
        )

        # 🔥 Unlock employee
        claimer = listing_data["claimer"]

        if claimer in user_claims:
            user_claims[claimer] = max(
                0,
                user_claims[claimer] - 1
            )

        # 🔥 Update review message
        embed = discord.Embed(
            title="✅ Listing Approved",
            color=discord.Color.green()
        )

        embed.add_field(
            name="SKU",
            value=str(listing_data["sku"]),
            inline=False
        )

        embed.add_field(
            name="Approved By",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="Status",
            value="✅ Approved",
            inline=False
        )

        await interaction.message.edit(
            embed=embed,
            view=None
        )

        # 🔥 Update employee workspace
        workspace_channel = bot.get_channel(
            listing_data["workspace_channel"]
        )

        if workspace_channel:

            try:
                workspace_message = await workspace_channel.fetch_message(
                    listing_data["workspace_message"]
                )

                approved_embed = discord.Embed(
                    title="✅ Listing Approved",
                    description=(
                        f"SKU: {listing_data['sku']}\n\n"
                        "Your listing has been approved.\n"
                        "You may now claim another listing."
                    ),
                    color=discord.Color.green()
                )

                approved_embed.set_footer(
                    text="Ebay Warehouse Listing System"
                )

                await workspace_message.edit(
                    embed=approved_embed,
                    view=None
                )

            except Exception as e:
                print(e)

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
                value=f"<@{listing_data['claimer']}>",
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

        # 🔥 Notify employee
        claimer = interaction.guild.get_member(
            listing_data["claimer"]
        )

        if claimer:
            try:
                await claimer.send(
                    f"✅ Your listing (SKU {listing_data['sku']}) has been approved.\n"
                    "You may now claim another listing."
                )
            except:
                pass

        await interaction.response.send_message(
            "✅ Listing approved.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.red,
        emoji="❌"
    )
    async def reject_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        # 🔒 Moderator role check
        role = discord.utils.get(
            interaction.guild.roles,
            name=MODERATOR_ROLE
        )

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "You don't have permission to reject listings.",
                ephemeral=True
            )
            return

        listing_data = listing_storage.get(
            self.listing_message_id
        )

        if listing_data is None:
            await interaction.response.send_message(
                "Listing not found.",
                ephemeral=True
            )
            return

        listing_data["submitted"] = False
        listing_data["approved"] = False
        listing_data["rejected"] = True
        listing_data["reviewed_by"] = interaction.user.id

        # 🔥 UPDATE GOOGLE SHEETS
        await update_listing_sheet(
            sku=listing_data["sku"],
            reviewed_by=interaction.user.display_name,
            status="Rejected",
        )

        embed = discord.Embed(
            title="❌ Listing Rejected",
            color=discord.Color.red()
        )

        embed.add_field(
            name="SKU",
            value=str(listing_data["sku"]),
            inline=False
        )

        embed.add_field(
            name="Rejected By",
            value=interaction.user.mention,
            inline=False
        )

        embed.add_field(
            name="Status",
            value="🔴 Rejected",
            inline=False
        )

        await interaction.message.edit(
            embed=embed,
            view=None
        )

        # 🔥 Update employee workspace
        workspace_channel = bot.get_channel(
            listing_data["workspace_channel"]
        )

        if workspace_channel:

            try:
                workspace_message = await workspace_channel.fetch_message(
                    listing_data["workspace_message"]
                )

                rejected_embed = discord.Embed(
                    title="❌ Listing Rejected",
                    description=(
                        f"SKU: {listing_data['sku']}\n\n"
                        "Your work needs corrections.\n"
                        "After fixing it, click **Done** again."
                    ),
                    color=discord.Color.red()
                )

                rejected_embed.set_footer(
                    text="Ebay Warehouse Listing System"
                )

                await workspace_message.edit(
                    embed=rejected_embed,
                    view=CompleteListingView(self.listing_message_id)
                )

            except Exception as e:
                print(e)

        # 🔥 Notify employee
        claimer = interaction.guild.get_member(
            listing_data["claimer"]
        )

        if claimer:
            try:
                await claimer.send(
                    f"❌ Your listing (SKU {listing_data['sku']}) was rejected.\n"
                    "Please fix the issues and press **Done** again when finished."
                )
            except:
                pass

        await interaction.response.send_message(
            "❌ Listing rejected.\nThe employee must fix the listing and submit it again.",
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
            "React with ✅ to claim this listing.\n\n"
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
        content=role.mention,
        embed=embed
    )

    await message.add_reaction("✅")

    # 🔥 STORE LISTING
    listing_storage[message.id] = {
        "sku": sku_counter,
        "link": link,

        "claimed": False,
        "completed": False,

        "claimer": None,
        "claimed_at": None,
        "submitted_at": None,

        "submitted": False,
        "approved": False,
        "rejected": False,

        "review_message": None,
        "workspace_message": None,
        "workspace_channel": None,

        "reject_reason": None,
        "reviewed_by": None
    }

    # 🔥 ADD LISTING TO GOOGLE SHEETS
    await add_listing_to_sheet(
        sku=listing_storage[message.id]["sku"],
        link=listing_storage[message.id]["link"],
    )

    sku_counter += 1

    try:
        await ctx.message.delete()
    except:
        pass

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

        # 🔒 Already waiting for review
        if listing_data.get("submitted") and not listing_data.get("rejected"):
            await interaction.response.send_message(
                "This listing is already waiting for moderator review.",
                ephemeral=True
            )
            return

        # 🔥 Mark as submitted for review
        listing_data["submitted"] = True
        listing_data["claimer"] = interaction.user.id
        listing_data["approved"] = False
        listing_data["rejected"] = False
        listing_data["submitted_at"] = datetime.now()

        # 🔥 UPDATE GOOGLE SHEETS
        await update_listing_sheet(
            sku=listing_data["sku"],
            submitted_at=listing_data["submitted_at"].strftime("%Y-%m-%d %H:%M:%S"),
            status="Waiting Review",
        )

        # 🔥 Send to review channel
        review_channel = bot.get_channel(REVIEW_CHANNEL_ID)

        if review_channel:

            embed = discord.Embed(
                title="📦 Listing Waiting For Review",
                color=discord.Color.orange()
            )

            embed.add_field(
                name="SKU",
                value=str(listing_data["sku"]),
                inline=False
            )

            embed.add_field(
                name="Employee",
                value=interaction.user.mention,
                inline=False
            )

            embed.add_field(
                name="Drive Folder",
                value=listing_data["link"],
                inline=False
            )

            embed.add_field(
                name="Status",
                value="🟡 Waiting Review",
                inline=False
            )

            review_msg = await review_channel.send(
                embed=embed,
                view=ApproveListingView(self.listing_message_id)
            )

            listing_data["review_message"] = review_msg.id

        # 🔥 Update workspace message
        submitted_embed = discord.Embed(
            title="🟡 Listing Submitted",
            description=(
                f"SKU: {listing_data['sku']}\n\n"
                "Your work has been submitted.\n"
                "Please wait for moderator approval."
            ),
            color=discord.Color.orange()
        )

        submitted_embed.set_footer(
            text="Ebay Warehouse Listing System"
        )

        await interaction.message.edit(
            embed=submitted_embed,
            view=None
        )

        await interaction.response.send_message(
            "✅ Your listing has been submitted for review.\n\n"
            "You cannot claim another listing until it has been approved.",
            ephemeral=True
        )

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

    # 🔒 Ignore listings already waiting for review or already approved
    if (
            listing_data.get("submitted")
            and not listing_data.get("rejected")
    ) or listing_data.get("approved"):
        return

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
    listing_data["claimed_at"] = datetime.now()

    # 🔥 UPDATE GOOGLE SHEETS
    await update_listing_sheet(
        sku=listing_data["sku"],
        employee=user.display_name,
        claimed_at=listing_data["claimed_at"].strftime("%Y-%m-%d %H:%M:%S"),
        status="Claimed",
    )

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

    workspace_embed.add_field(
        name="Status",
        value="🔵 Claimed",
        inline=False
    )

    workspace_embed.set_footer(
        text="Ebay Warehouse Listing System"
    )

    workspace_msg = await workspace_channel.send(
        embed=workspace_embed,
        view=CompleteListingView(message.id)
    )

    listing_data["workspace_message"] = workspace_msg.id
    listing_data["workspace_channel"] = workspace_channel.id

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


