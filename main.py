import discord
import requests
import asyncio
import math
from keep_alive import keep_alive
from discord.ext import tasks
from discord.ext.commands import Bot
from collections import defaultdict

# instantiate a Discord client
client = Bot("!")

cryptoSupportedList = list()
cryptoPairsDirectory = defaultdict(list)
cryptoList = ["BTC", "ETH", "ADA", "UNI", "LTC"]
counter = 0


# get Discord bot token (key to control a Discord bot)
def getToken():
    file = open("config.txt", "r")
    token = file.readline()
    file.close()
    return token


# start tracking cryptocurrencies price after init
@client.event
async def on_ready():
    priceTracker.start()


# each cryptocurrency from "cryptoList" is shown for 5 seconds
@tasks.loop(seconds=5)  # repeat after every 5 seconds
async def priceTracker():
    global counter
    if counter > (len(cryptoList) - 1):
        counter = 0
    if len(cryptoList) > 0:
        URL = 'https://api.binance.com/api/v1/ticker/price?symbol=' + cryptoList[counter] + 'EUR'

        # req cryptocurrency price
        r = requests.get(url=URL)
        data = r.json()
        value = float(data['price'].rstrip("0"))

        # show price in watching panel
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=cryptoList[counter] + " @ €" + '{:,}'.format(value)))

        counter = counter + 1
    else:
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="nothing to watch..."))


def createEmbed(cur_page, offset, limit, isNext):
    columns = 3
    pages = int(math.ceil(len(cryptoSupportedList) / (3 * limit)))

    embed = discord.Embed(title=" ", description=" ", color=0xF0B90B)
    embed.set_author(name="List of supported cryptocurrencies",
                     icon_url="https://public.bnbstatic.com/20190405/eb2349c3-b2f8-4a93-a286-8f86a62ea9d8.png")

    embed.add_field(name="Page " + str(cur_page) + "/" + str(pages), value="⠀", inline=False)

    # next page reaction
    if isNext:
        for i in range(columns):
            if limit * (offset + 1) <= len(cryptoSupportedList):
                embed.add_field(name="⠀", value=" ".join(cryptoSupportedList[limit * offset:limit * (offset + 1)]),
                                inline=True)
                offset = offset + 1
            else:
                embed.add_field(name="⠀", value=" ".join(cryptoSupportedList[limit * offset:len(cryptoSupportedList)]),
                                inline=True)
                offset = offset + 1
                break

    # previous page reaction
    else:
        x = 0

        if offset % columns == 0:
            y = columns
        else:
            x = columns - offset % columns
            y = offset % columns

        embed = discord.Embed(title=" ", description=" ", color=0xF0B90B)
        embed.set_author(name="List of supported cryptocurrencies",
                         icon_url="https://public.bnbstatic.com/20190405/eb2349c3-b2f8-4a93-a286-8f86a62ea9d8.png")

        embed.add_field(name="Page " + str(cur_page) + "/" + str(pages), value="⠀", inline=False)
        for i in range(columns):
            embed.add_field(name="⠀", value=" ".join(
                cryptoSupportedList[limit * (offset - pages + i + x):limit * (offset - pages + 1 + i + x)]),
                            inline=True)

        offset = offset - y

    return embed, offset


@client.command()
async def showList(ctx):
    limit = 30
    offset = 0

    pages = int(math.ceil(len(cryptoSupportedList) / (3 * limit)))
    cur_page = 1

    embed, offset = createEmbed(cur_page, offset, limit, True)

    message = await ctx.channel.send(embed=embed)

    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    # this makes sure nobody except the command sender can interact with embed
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

    while True:
        try:
            # waiting for a reaction to be added - times out after 60 seconds
            reaction, user = await client.wait_for("reaction_add", timeout=60, check=check)

            # next page reaction
            if str(reaction.emoji) == "▶️" and cur_page != pages:
                cur_page += 1
                embed, offset = createEmbed(cur_page, offset, limit, True)

                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            # previous page reaction
            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                embed, offset = createEmbed(cur_page, offset, limit, False)

                await message.edit(embed=embed)
                await message.remove_reaction(reaction, user)

            else:
                # removes reactions if the user tries to go forward on the last page or backwards on the first page
                await message.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
            # ending the loop if user doesn't react after x seconds
            await message.delete()
            break


# called whether there is a message in the chat
@client.event
async def on_message(message):
    global counter

    if message.author == client.user:
        return

    # View all commands
    if message.content == '!help':
        embed = discord.Embed(title=" ", description=" ", color=0xF0B90B)
        embed.set_author(name="Binance Price Tracker commands:",
                         icon_url="https://public.bnbstatic.com/20190405/eb2349c3-b2f8-4a93-a286-8f86a62ea9d8.png")
        embed.add_field(name="List of supported commands:", value=
        "** • !help**  - View all commands and what they do\n"
        "** • !list**  - Get list of supported cryptocurrencies\n"
        "** • !check** - Get list of supported pairs of chosen cryptocurrency, **USAGE:** !check BTC\n"
        "** • !p** - Get price of chosen cryptocurrency, **USAGE:** !p BTC/EUR\n"
        "** • !watch** - Start watching price of cryptocurrency in server member list, **USAGE:** !watch BTC\n"
        "** • !unwatch** - Stop watching price of cryptocurrency in server member list, **USAGE:** !unwatch BTC\n",
                        inline=True)
        await message.channel.send(embed=embed, delete_after=90)

    # Get list of supported cryptocurrencies
    if message.content == '!list':
        await showList(message)

    # Get list of supported pairs of chosen cryptocurrency
    if message.content.startswith('!check'):
        cryptoToBeChecked = message.content.split('!check ')
        global cryptoPairsDirectory

        if len(cryptoToBeChecked) != 2:
            await message.channel.send("Missing parameter\nExample: **!check BTC**")
        else:
            crypto = cryptoToBeChecked[1].upper()
            if crypto in cryptoPairsDirectory.keys():
                embed = discord.Embed(title=" ", description=" ", color=0xF0B90B)
                embed.set_author(name="List of supported " + crypto + " pairs",
                                 icon_url="https://public.bnbstatic.com/20190405/eb2349c3-b2f8-4a93-a286-8f86a62ea9d8.png")
                embed.add_field(name="⠀", value=" ".join(cryptoPairsDirectory[crypto]), inline=True)
                message = await message.channel.send(embed=embed, delete_after=90)
            else:
                await message.channel.send(crypto + ' is not supported')

    # Get price of chosen cryptocurrency
    if message.content.startswith('!p'):
        cryptoToBeChecked = message.content.split('!p ')

        if len(cryptoToBeChecked) != 2:
            await message.channel.send("Missing parameter/s\nExample: **!p BTC/EUR**")
        else:
            pair = cryptoToBeChecked[1].split('/', 1)
            if len(pair) != 2 or pair[1] == "":
                await message.channel.send("Missing parameter/s\nExample: **!p BTC/EUR**")
            else:
                pair[0] = pair[0].upper()
                pair[1] = pair[1].upper()

                URL = 'https://api.binance.com/api/v1/ticker/price?symbol=' + pair[0] + pair[1]
                r = requests.get(url=URL)
                data = r.json()

                if 'symbol' in data.keys() and 'price' in data.keys():
                    await message.channel.send(
                        'The current price of **' + pair[0] + '** is **' + data['price'].rstrip("0") + '** **' +
                        pair[1] + '**')
                else:
                    await message.channel.send(cryptoToBeChecked[1].upper() + ' is not supported')

    # Start watching price of cryptocurrency in server member list
    if message.content.startswith('!watch'):
        cryptoToBeWatched = message.content.split('!watch ')

        if len(cryptoToBeWatched) != 2:
            await message.channel.send("Missing parameter\nExample: **!watch BTC**")
        else:
            crypto = cryptoToBeWatched[1].upper()
            if crypto not in cryptoList and (crypto + "\n") in cryptoSupportedList:
                cryptoList.append(crypto)
                counter = counter + 1

    # Stop watching price of cryptocurrency in server member list
    if message.content.startswith('!unwatch'):
        cryptoToBeWatched = message.content.split('!unwatch ')

        if len(cryptoToBeWatched) != 2:
            await message.channel.send("Missing parameter\nExample: **!unwatch BTC**")
        else:
            crypto = cryptoToBeWatched[1].upper()
            if crypto in cryptoList:
                cryptoList.remove(crypto)
                counter = counter - 1


# initialize list of supported cryptocurrencies
def listInit():
    URL = 'https://api.binance.com/api/v3/exchangeInfo'

    data = requests.get(url=URL).json()

    global cryptoSupportedList
    global cryptoPairsDirectory

    tempDictionary = defaultdict(list)

    # creating pairs from requested data
    for s in data['symbols']:
        cryptoSupportedList.append(s['baseAsset'] + "\n")
        tempDictionary[s['baseAsset']].append(s['baseAsset'] + "/" + s['quoteAsset'] + "\n")

    cryptoSupportedList = list(set(cryptoSupportedList))
    cryptoSupportedList.sort()

    for key in sorted(tempDictionary):
        cryptoPairsDirectory[key] = sorted(tempDictionary[key])


listInit()
keep_alive()

client.run(getToken())