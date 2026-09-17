import os
import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

import aiosqlite


# =========================================================
# CONFIG
# =========================================================

# Put YOUR application IDs here.
# These applications will NEVER be blocked.
#
# IMPORTANT:
# Use the APPLICATION ID of your bot/app, not the bot's user ID.
EXEMPT_APPLICATION_IDS = {
    123456789012345678,  # Replace with your User Install bot application ID
}

DB_PATH = os.path.join("data", "userinstall.db")

TIMEOUT_DURATION = timedelta(hours=1)
TIMEOUT_TEXT = "1 hour"


# =========================================================
# DATABASE
# =========================================================

async def init_database():
    os.makedirs("data", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelisted_userinstall (
                guild_id INTEGER NOT NULL,
                application_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, application_id)
            )
        """)

        await db.commit()


async def is_whitelisted(guild_id: int, application_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM whitelisted_userinstall
            WHERE guild_id = ?
            AND application_id = ?
            LIMIT 1
            """,
            (guild_id, application_id)
        )

        result = await cursor.fetchone()
        await cursor.close()

        return result is not None


# =========================================================
# COG
# =========================================================

class BlockUserInstall(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ready = False

    async def cog_load(self):
        await init_database()
        self.ready = True

    # -----------------------------------------------------
    # Detect messages created from interactions
    # -----------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # Ignore DMs
        if message.guild is None:
            return

        # Ignore our own messages
        if message.author.id == self.bot.user.id:
            return

        # -------------------------------------------------
        # Get interaction metadata
        # -------------------------------------------------

        metadata = getattr(message, "interaction_metadata", None)

        if metadata is None:
            return

        # Get application ID
        application_id = getattr(metadata, "application_id", None)

        if application_id is None:
            return

        try:
            application_id = int(application_id)
        except (ValueError, TypeError):
            return

        # -------------------------------------------------
        # Only handle User Install applications
        # -------------------------------------------------

        authorizing_owners = getattr(
            metadata,
            "authorizing_integration_owners",
            None
        )

        if authorizing_owners is None:
            return

        # Discord:
        #
        # "0" = GUILD_INSTALL
        # "1" = USER_INSTALL
        #
        # We only care about USER_INSTALL.
        if "1" not in authorizing_owners:
            return

        # -------------------------------------------------
        # Never block our own applications
        # -------------------------------------------------

        if application_id in EXEMPT_APPLICATION_IDS:
            return

        # -------------------------------------------------
        # Check whitelist
        # -------------------------------------------------

        if await is_whitelisted(
            message.guild.id,
            application_id
        ):
            return

        # -------------------------------------------------
        # Prevent duplicate processing
        # -------------------------------------------------

        user_id = message.author.id

        # -------------------------------------------------
        # Timeout user
        # -------------------------------------------------

        try:
            member = message.guild.get_member(user_id)

            if member is None:
                try:
                    member = await message.guild.fetch_member(user_id)
                except discord.NotFound:
                    return

            # Don't attempt to timeout the server owner
            if member.id == message.guild.owner_id:
                return

            # Don't timeout ourselves
            if member.id == self.bot.user.id:
                return

            # Make sure we can timeout them
            if not member.guild_permissions.moderate_members:
                return

            # Hierarchy check
            me = message.guild.me

            if me is not None:
                if member.top_role >= me.top_role:
                    return

            await member.timeout(
                TIMEOUT_DURATION,
                reason=f"Using non-whitelisted User Install application {application_id}"
            )

            # -------------------------------------------------
            # Send warning message
            # -------------------------------------------------

            await message.channel.send(
                f"{member.mention} muted for {TIMEOUT_TEXT} "
                f"reason using userinstall bot"
            )

        except discord.Forbidden:
            # Bot does not have enough permissions
            pass

        except discord.HTTPException:
            pass

        except Exception as e:
            print(
                f"[BlockUserInstall] Error while processing "
                f"{message.author} ({message.author.id}): {e}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(BlockUserInstall(bot))