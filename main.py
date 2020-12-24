import requests as req
import json
import os
import sys
import asyncio
import discord
import sqlite3 as sql3
from discord.ext import commands, tasks


if os.getenv('DEBUG') == 'False':
    __DEBUG__ = False
else:
    __DEBUG__ = True

if os.getenv('PRODUCTION') == 'False':
    __PRODUCTION__ = False
else:
    __PRODUCTION__ = True

BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_LOCATION = 'database/allegro.db'

if __PRODUCTION__:
    SANDBOX_URL = r''
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
else:
    SANDBOX_URL = r'.allegrosandbox.pl'
    CLIENT_ID = os.getenv('SANDBOX_ID')
    CLIENT_SECRET = os.getenv('SANDBOX_SECRET')

DELAY = int(os.getenv('DELAY'))


def d_print(*args, **kwargs):
    if __DEBUG__:
        print('DEBUG ', *args, file=sys.stderr, **kwargs)


def log_error(*args, **kwargs):
    print('ERROR ', *args, file=sys.stderr, **kwargs)


"""
-----------------------------------------------------------------------------------------
Database
-----------------------------------------------------------------------------------------
"""


def readProductsJSON(data: str):
    products = json.loads(data)

    return products['products']


def readProductsDB(location: str):
    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute('SELECT name, maxPrice, minPrice FROM products')
    fetched = cur.fetchall()
    cur.close()
    conn.close()

    products = []

    for p in fetched:
        products.append({
            'name': p[0],
            'max-price': p[1],
            'min-price': p[2],
        })

    return products


def getTableValues(location: str):
    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute('SELECT id, name, maxPrice, minPrice FROM products')
    products = cur.fetchall()
    cur.close()
    conn.close()

    return products


def addProductToDB(location: str, product: dict):
    query = "INSERT INTO products(name, maxPrice, minPrice) VALUES('{name}', {maxprice}, {minprice})"

    conn = sql3.connect(location)
    conn.execute(query.format(
        name=product['name'], maxprice=product['max-price'], minprice=product['min-price']))
    conn.commit()
    conn.close()


def removeProductFromDB(location: str, id: int):
    query = "DELETE FROM products WHERE id = {id}"

    conn = sql3.connect(location)
    conn.execute(query.format(id=id))
    conn.commit()
    conn.close()


def readProductDB(location: str, id: int):
    query = 'SELECT name, maxPrice, minPrice FROM products WHERE id = {id}'

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
            'max-price': p[1],
            'min-price': p[2]
        })

    return products


def addChecked(location: str, product: dict):
    query = "INSERT INTO checked(id, price, url) VALUES('{id}', {price}, '{url}')"

    conn = sql3.connect(location)
    conn.execute(query.format(
        id=product['id'], price=product['price'], url=product['url']))
    conn.commit()
    conn.close()


def compareChecked(location: str, product: dict):
    query = "SELECT price FROM checked WHERE id = {id}"

    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute(query.format(id=product['id']))
    fetched = cur.fetchall()
    cur.close()

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


def getChecked(location: str):
    query = "SELECT * FROM checked"
    conn = sql3.connect(location)
    cur = conn.cursor()
    cur.execute(query)
    fetched = cur.fetchall()
    cur.close()

    ret = []

    for f in fetched:
        ret.append({
            'id': f[0],
            'price': f[1],
            'url': f[2],
        })

    return ret


"""
-----------------------------------------------------------------------------------------
Allegro API
-----------------------------------------------------------------------------------------
"""


def getToken():
    AUTH_URL = r'https://allegro.pl'+SANDBOX_URL + \
        r'/auth/oauth/token?grant_type=client_credentials'

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
                    if (float(item['sellingMode']['price']['amount']) <= float(validation['max-price']) and
                            float(item['sellingMode']['price']['amount']) >= float(validation['min-price'])):
                        valid.append(item['vendor']['url'])
            except:
                if (float(item['sellingMode']['price']['amount']) <= float(validation['max-price']) and
                        float(item['sellingMode']['price']['amount']) >= float(validation['min-price'])):
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
                    if (float(item['sellingMode']['price']['amount']) <= float(validation['max-price']) and
                            float(item['sellingMode']['price']['amount']) >= float(validation['min-price'])):
                        valid.append({
                            'id': item['id'],
                            'price': float(item['sellingMode']['price']['amount']),
                            'url': item['vendor']['url']
                        })
            except:
                if (float(item['sellingMode']['price']['amount']) <= float(validation['max-price']) and
                        float(item['sellingMode']['price']['amount']) >= float(validation['min-price'])):
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
bot = commands.Bot(command_prefix='|',
                   description='AllegroBot', intents=intents)


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
                if len(result) >= 1500:
                    try:
                        await ctx.send(result)
                        result = ""
                    except req.HTTPError as exc:
                        log_error(exc)
                        await ctx.send('I am unable to check all products! Sorry...')

        await ctx.send(result)
    except req.HTTPError as exc:
        log_error(exc)
        await ctx.send('I am unable to check all products! Sorry...')


@bot.command(description='List all checked products')
async def listChecked(ctx):
    try:
        products = getChecked(DB_LOCATION)
        result = ""

        for p in products:
            result = result + str(p['price']) + ' @ ' + str(p['url']) + '\n'
            if len(result) >= 1500:
                try:
                    d_print(result)
                    await ctx.send(result)
                    result = ""
                except discord.errors.HTTPException as exc:
                    log_error(exc)
                    result = ""

        d_print(result)
        await ctx.send(result)
        result = ""
    except discord.errors.HTTPException as exc:
        log_error(exc)
        result = ""


@bot.command(description='Perform Allegro check on single product from the list', pass_context=True)
async def check(ctx, *, message):
    try:
        result = ""
        id = int(message)
        products = readProductDB(DB_LOCATION, id)
        token = getToken()
        for product in products:
            result = result + product['name'] + '\n'
            info = getInfo(token, product)

            valid = getValidLinks(info['items'], product)

            for v in valid:
                result = result + v + '\n'
                if len(result) > 1500:
                    try:
                        d_print(result)
                        await ctx.send(result)
                        result = ""
                    except discord.errors.HTTPException as exc:
                        log_error(exc)
                        result = ""

        await ctx.send(result)
    except req.HTTPError as exc:
        log_error(exc)
        await ctx.send('I am unable to check all products! Sorry...')
    except discord.errors.HTTPException as exc:
        log_error(exc)
        await ctx.send('I am unable to check all products! Sorry...')
    except ValueError as exc:
        log_error(exc)
        await ctx.send("You provided wrong ID. To check the ID, please call `|listProducts` command.")


@bot.command(description='Show all products on the list', pass_context=True)
async def listProducts(ctx):
    try:
        products = getTableValues(DB_LOCATION)
        result = "id | name | max price | min price\n"
        for p in products:
            result = result + str(p[0]) + ' | ' + p[1] + \
                ' | ' + str(p[2]) + ' | ' + str(p[3]) + '\n'
        await ctx.send(result)
    except Exception as exc:
        log_error(exc)
        await ctx.send('I am unable to list products! Sorry...')


@bot.command(description='Load full JSON object from message', pass_context=True)
async def addJSON(ctx, *, message):
    try:
        items = readProductsJSON(message)
        for item in items:
            try:
                addProductToDB(DB_LOCATION, item)
            except sql3.Error as exc:
                log_error(exc)
                await ctx.send(exc)
    except json.JSONDecodeError as exc:
        log_error(exc)
        await ctx.send('Wrong format! Correct format is:\n```json\n{"name":"name of product","max-price":123.00}\n```\n')
    except TypeError as exc:
        log_error(exc)
        await ctx.send('Wrong format! Correct format is:\n```json\n{"name":"name of product","max-price":123.00}\n```\n')


@bot.command(description='Add single product to the list', pass_context=True)
async def add(ctx, *, message):
    try:
        d_print(message)
        product = json.loads(message)
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
        await ctx.send('Gratz! Added {prod} with maximal price of {maxprice} and minimal price of {minprice}.'.format(
            prod=product['name'],
            maxprice=product['max-price'],
            minprice=product['min-price']))


@bot.command(description='Delete single product from the list', pass_context=True)
async def delete(ctx, *, message):
    try:
        id = int(message)
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
            info = getInfo(token, product)
            valid = getValidProducts(info['items'], product)

            d_print(valid)

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

            if len(checked) > 0:
                result = result + product['name'] + '\n'

            for c in checked:
                result = result + c['url'] + '\n'
                if len(result) >= 1500:
                    try:
                        d_print(result)
                        await channel.send(result)
                        result = ""
                    except discord.errors.HTTPException as exc:
                        log_error(exc)
                        result = ""
        try:
            d_print(result)
            await channel.send(result)
        except discord.errors.HTTPException as exc:
            log_error(exc)
        await asyncio.sleep(DELAY)


@bot.event
async def on_ready():
    d_print('Logged in as')
    d_print(bot.user.name)
    d_print(bot.user.id)
    d_print('------')

    bgCheck.start()


"""
-----------------------------------------------------------------------------------------
Main
-----------------------------------------------------------------------------------------
"""


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
