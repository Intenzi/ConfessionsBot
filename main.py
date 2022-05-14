import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, Select, View

from data import *
import json
import asyncio
import traceback

# for my dotenv file
from decouple import config


intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!!", case_insensitive=True, intents=intents,
                   strip_after_prefix=True)

slash = bot.tree


class Body(Modal, title='Anonymous Message Editor'):
    content = discord.ui.TextInput(
        label='Message',
        style=discord.TextStyle.long,
        placeholder='The text that will become your anonymous message',
        required=True,
        max_length=4000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

    async def on_error(self, error: Exception, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f'Oops! Something went wrong.\nError: {error}', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)


class Dropdown(Select):
    def __init__(self):

        with open("storage.json", "r") as f:
            data = json.load(f)

        options = [discord.SelectOption(label=k) for k in data["blocked_anon_numbers"]]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose the anon_id_number...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.val = True
        self.view.stop()


class DropdownView(View):
    def __init__(self):
        self.val = False
        super().__init__(timeout=60)

        # Adds the dropdown to our view object.
        self.add_item(Dropdown())

    async def on_timeout(self):
        return


@bot.event
async def on_ready():
    print("Bot running with:")
    print("Username: ", bot.user.name)
    print("User ID: ", bot.user.id)
    await slash.sync(guild=discord.Object(id=GUILD_ID))


@slash.command(guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    content='The text of your anonymous message, leave blank for a paragraph editor',
    attachment='An optional image that appears below the text',
)
async def confess(interaction, content: str = None, attachment: discord.Attachment = None):
    """Send an anonymous message to this channel"""
    # Remove the next two lines to let slash command be used in any channel
    if not interaction.channel_id == CHANNEL_ID:
        return

    with open("storage.json", "r") as f:
        data = json.load(f)

    # Blocked Check
    if interaction.user.id in data["blocked"]:
        return await interaction.response.send_message("You have been blocked from confessing.", ephemeral=True)

    emb = discord.Embed(color=discord.Color.random())
    data["count"] += 1
    emb.set_footer(text=f"Anon #{data['count']}")

    # Add to storage
    data[str(data["count"])] = interaction.user.id

    with open("storage.json", "w") as f:
        json.dump(data, f, indent=4)

    option = False
    if content is None and attachment is None:
        # Take long input
        modal = Body()
        await interaction.response.send_modal(modal)
        option = await modal.wait()
        if option:
            return
        content = str(modal.content)
        option = True

    if content:
        emb.description = content

    if attachment:
        emb.set_image(url=attachment.url)

    if option:
        await interaction.followup.send("Done, your message is below.", ephemeral=True)
    else:
        await interaction.response.send_message("Done, your message is below.", ephemeral=True)

    ch = interaction.guild.get_channel(CHANNEL_ID)
    await ch.send(embed=emb)


@slash.command(guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
async def block(interaction, anon_number: int):
    """
    Block anon-id from confessing
    """
    with open("storage.json", "r") as f:
        data = json.load(f)

    if not 0 < anon_number < len(data)-2:
        return await interaction.response.send_message(f"The anon id **#{anon_number}** does not exist.", ephemeral=True)

    # Add user_id to blocked list
    data["blocked"].append(data[str(anon_number)])
    # Add anon_number to block_number_list for unblocking
    data["blocked_anon_numbers"].append(str(anon_number))

    with open("storage.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(f"The anon id **#{anon_number}** is now blocked from sending further messages.", ephemeral=True)


@slash.command(guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
async def unblock(interaction):
    """
    Unblock anon-id from confessing
    """
    my_view = DropdownView()

    try:
        await interaction.response.send_message(view=my_view, ephemeral=True)
    except:
        return await interaction.response.send_message("No anon to unblock currently.")

    await my_view.wait()

    if not my_view.val:
        return await interaction.followup.send("Cancelled!", ephemeral=True)

    # We have the anon-id now
    anon_number = my_view.children[0].values[0]
    with open("storage.json", "r") as f:
        data = json.load(f)

    # Remove user_id from blocked list
    data["blocked"].remove(data[anon_number])
    # Remove anon_number from block_number_list
    data["blocked_anon_numbers"].remove(anon_number)

    with open("storage.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.followup.send(f"The anon id **#{anon_number}** is now unblocked.", ephemeral=True)


async def main():
    async with bot:
        await bot.start(config('TOKEN'))  # You can replace it with your bots token as bot.start("token_long_much")


if __name__ == "__main__":
    asyncio.run(main())
