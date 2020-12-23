import requests as req
import json
import os
import asyncio
import discord
import sqlite3 as sql3
from discord.ext import commands, tasks

__DEBUG__ = False
__PRODUCTION__ = False

BOT_TOKEN = r'discord bot token here'
DB_LOCATION = 'database/allegro.db'

if __PRODUCTION__:
    SANDBOX_URL = r''
    CLIENT_ID = 'allegro rest api client id'
    CLIENT_SECRET = 'allegro rest api client secret'
else:
    SANDBOX_URL = r'.allegrosandbox.pl'
    CLIENT_ID = 'allegrosandbox rest api client id'
    CLIENT_SECRET = 'allegrosandbox rest api client secret'


def d_print(*args):
    if __DEBUG__:
        print(*args)

def log_error(*args):
    print('ERROR ', *args)

"""
-----------------------------------------------------------------------------------------
Database
-----------------------------------------------------------------------------------------
"""

def readProductsJSON(name: str):
    with open(name) as f:
        data = f.read().replace('\n', '')

    products = json.loads(data)

    return products['products']


def readProductsDB(location: str):
    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute('SELECT name, maxPrice FROM products')
    fetched = cur.fetchall()
    cur.close()
    conn.close()

    products = []

    for p in fetched:
        products.append({
            'name': p[0],
            'max-price': p[1]
        })

    return products


def getTableValues(location: str):
    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute('SELECT id, name, maxPrice FROM products')
    products = cur.fetchall()
    cur.close()
    conn.close()

    return products


def addProductToDB(location: str, product: dict):
    query = "INSERT INTO products(name, maxPrice) VALUES('{name}', {price})"

    conn = sql3.connect(location)
    conn.execute(query.format(name=product['name'], price=product['max-price']))
    conn.commit()
    conn.close()


def removeProductFromDB(location: str, id: int):
    query = "DELETE FROM products WHERE id = {id}"

    conn = sql3.connect(location)
    conn.execute(query.format(id=id))
    conn.commit()
    conn.close()
 

def readProductDB(location: str, id: int):
    query = 'SELECT name, maxPrice FROM products WHERE id = {id}'

    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute(query.format(id=id))
    fetched = cur.fetchall()
    cur.close()
    conn.close()

    products = []

    for p in fetched:
        products.append({
            'name': p[0],
            'max-price': p[1]
        })

    return products


def addChecked(location: str, product: dict):
    query = "INSERT INTO checked(id, price, url) VALUES('{id}', {price}, '{url}')"

    conn = sql3.connect(location)
    conn.execute(query.format(id=product['id'], price=product['price'], url=product['url']))
    conn.commit()
    conn.close()


def compareChecked(location: str, product: dict):
    query = "SELECT price FROM checked WHERE id = {id}"

    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute(query.format(id=product['id']))
    fetched = cur.fetchall()
    cur.close()

    d_print(type(fetched[0][0]))

    if fetched[0][0] > product['price']:
        return 1
    elif fetched[0][0] < product['price']:
        return -1
    else:
        return 0

def updateChecked(location: str, product: dict):
    query = "UPDATE checked SET price = {price} WHERE id = {id}"

    conn = sql3.connect(location)
    conn.execute(query.format(id=product['id'], price=product['price']))
    conn.commit()
    conn.close()

"""
-----------------------------------------------------------------------------------------
Allegro API
-----------------------------------------------------------------------------------------
"""


def getToken():
    AUTH_URL = r'https://allegro.pl'+SANDBOX_URL+r'/auth/oauth/token?grant_type=client_credentials'

    res = req.get(AUTH_URL, auth=(CLIENT_ID, CLIENT_SECRET))
    if not res.ok:
       res.raise_for_status()

    body = res.json()

    return body['access_token']


def getInfo(token: str, product: dict):
    HEADERS = {
        'Authorization': r'Bearer '+token,
        'Accept': r'application/vnd.allegro.public.v1+json'
    }
    BASE_URL = r'https://api.allegro.pl'+SANDBOX_URL+r'/offers/listing?phrase='

    res = req.get(BASE_URL+product['name'], headers=HEADERS)
    if not res.ok:
        res.raise_for_status()

    resp_body = res.json()

    return resp_body


def getValidLinks(products: dict, validation: dict):
    BASE_URL = r'https://allegro.pl'+SANDBOX_URL+r'/oferta/'

    valid = []

    for item in products['regular']:
        if item['sellingMode']['format'] == 'BUY_NOW':
            d_print(item, '\n-----')
            try:
                if item['vendor']['id'] == 'ALLEGRO_LOKALNIE':
                    if float(item['sellingMode']['price']['amount']) <= float(validation['max-price']):
                        valid.append(item['vendor']['url'])
            except:
                if float(item['sellingMode']['price']['amount']) <= float(validation['max-price']):
                    valid.append(BASE_URL+item['id'])

    return valid


def getValidProducts(products: dict, validation: dict):
    BASE_URL = r'https://allegro.pl'+SANDBOX_URL+r'/oferta/'
    valid = []

    for item in products['regular']:
        if item['sellingMode']['format'] == 'BUY_NOW':
            d_print(item, '\n-----')
            try:
                if item['vendor']['id'] == 'ALLEGRO_LOKALNIE':
                    if float(item['sellingMode']['price']['amount']) <= float(validation['max-price']):
                        valid.append({
                            'id': item['id'],
                            'price': float(item['sellingMode']['price']['amount']),
                            'url': item['vendor']['url']
                        })
            except:
                if float(item['sellingMode']['price']['amount']) <= float(validation['max-price']):
                    valid.append({
                        'id': item['id'],
                        'price': float(item['sellingMode']['price']['amount']),
                        'url': BASE_URL+item['id']
                    })
    
    return valid

"""
-----------------------------------------------------------------------------------------
BOT
-----------------------------------------------------------------------------------------
"""


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='|', description='AllegroBot', intents=intents)


@bot.command(description='Perform Allegro check on all the products from the list')
async def checkAll(ctx):
    try:
        result = ""
        products = readProductsDB(DB_LOCATION)
        token = getToken()
        for product in products:
            result = result + product['name'] + '\n'
            info = getInfo(token, product)
            valid = getValidLinks(info['items'], product)

            for v in valid:
                result = result + v + '\n'
                
        await ctx.send(result) 
    except req.HTTPError as exc:
        log_error(exc)
        await ctx.send('I am unable to check all products! Sorry...')


@bot.group(description='Perform Allegro check on single product from the list')
async def check(ctx):
    try:
        result = ""
        id = int(ctx.subcommand_passed)
        products = readProductDB(DB_LOCATION, id)
        token = getToken()
        for product in products:
            result = result + product['name'] + '\n'
            info = getInfo(token, product)

            valid = getValidLinks(info['items'], product)

            for v in valid:
                result = result + v + '\n' 

        await ctx.send(result) 
    except req.HTTPError as exc:
        log_error(exc)
        await ctx.send('I am unable to check all products! Sorry...')
    except ValueError as exc:
        log_error(exc)
        await ctx.send("You provided wrong ID. To check the ID, please call `|listProducts` command.")


@bot.command(description='Show all products on the list')
async def listProducts(ctx):
    try:
        products = getTableValues(DB_LOCATION)
        result = "id | name | max price\n"
        for p in products:
            result = result + str(p[0]) + ' | ' + p[1] + ' | ' + str(p[2]) + '\n'
        await ctx.send(result)
    except Exception as exc:
        log_error(exc)
        await ctx.send('I am unable to list products! Sorry...')


@bot.group(description='Add single product to the list')
async def add(ctx):
    try:
        product = json.loads(ctx.subcommand_passed)
        d_print(product)
        addProductToDB(DB_LOCATION, product)
    except json.JSONDecodeError as exc:
        log_error(exc)
        await ctx.send('Wrong format! Correct format is:\n```json\n{"name":"name of product","max-price":123.00}\n```\n')
    except TypeError as exc:
        log_error(exc)
        await ctx.send('Wrong format! Correct format is:\n```json\n{"name":"name of product","max-price":123.00}\n```\n')
    except sql3.Error as exc:
        log_error(exc)
        await ctx.send(exc)
    else:
        await ctx.send('Gratz! Added {prod} with maximal price of {price}.'.format(prod=product['name'], price=product['max-price']))


@bot.group(description='Delete single product from the list')
async def delete(ctx):
    try:
        id = int(ctx.subcommand_passed)
        d_print(id)
        removeProductFromDB(DB_LOCATION, id)
    except sql3.Error as exc:
        log_error(exc)
        await ctx.send(exc)
    except ValueError as exc:
        log_error(exc)
        await ctx.send("You provided wrong ID. To check the ID, please call `|listProducts` command.")
    else:
        await ctx.send('Gratz! Removed {id} from list.'.format(id=id))


@tasks.loop()
async def bgCheck():
    channel = bot.get_channel(791348366595457064)
    while not bot.is_closed():
        d_print('task in background called')

        result = ""
        products = readProductsDB(DB_LOCATION)
        token = getToken()
        for product in products:
            result = result + product['name'] + '\n'
            info = getInfo(token, product)
            valid = getValidProducts(info['items'], product)

            checked = []

            for v in valid:
                try:
                    ret = compareChecked(DB_LOCATION, v)
                    if ret > 0:
                        updateChecked(DB_LOCATION, v)
                        checked.append(v)
                except IndexError:
                    addChecked(DB_LOCATION, v)
                    checked.append(v)

            for c in checked:
                result = result + c['url'] + '\n'

        await channel.send(result)
        await asyncio.sleep(60*10)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    bgCheck.start()


"""
-----------------------------------------------------------------------------------------
Main
-----------------------------------------------------------------------------------------
"""


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
