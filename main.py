import signal, sys
def shutdown(signal, frame):
    loop = asyncio.get_event_loop()
    loop.stop()
    return sys.exit('Intercept CTRL + C. Exit...')

signal.signal(signal.SIGINT, shutdown)
import logging
from aiogram import Dispatcher, Bot, executor, types
from aiogram.utils import exceptions
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import aiohttp
from data.util import Fivvy
import asyncio
from random import choice
import os, re, eyed3
from urllib.request import urlopen


TEMP_PATH = './data/temp/'
BOT_UNAVAILABLE = "I'm sorry, but I'm not available in groups, send me a private message. Don't mess with the group ;)"
BOT_UNAVAILABLE_STICKERS = ["CAACAgIAAxkBAAIW32RnY2sew5GtJiaQxpN0ZMG6T_QeAALGCwACMDDRSDCM6vy68yvoLwQ", \
    "CAACAgIAAxkBAAIW4GRnY7G7OWvwMVTnybIVveUnf8WKAALmCwACFxQ4SL0JAAHunW88qy8E", \
    "CAACAgIAAxkBAAIW4WRnY8OnU9vREkBv5tlufU1nxZ4oAALbDAACO1OxSEDhc0ZYg20rLwQ", \
    "CAACAgIAAx0CbhFhsgADK2RnZDWzGmP4HYTh5aIt9TxsNhWhAALwAQAC6NbiEs2dQhfXoLEbLwQ", \
    "CAACAgIAAx0CbhFhsgADLGRnZEtEkLcQgV5CIEEr9yDcuoYpAAL6CAACeQIJSOVTxx8NpjZcLwQ", \
    "CAACAgIAAx0CbhFhsgADLWRnZFwUoKI6-Zcp3EDyd25WLeOgAALhCQACkZYISMHdtkBSi2MGLwQ", \
    "CAACAgIAAx0CbhFhsgADLmRnZG8xu3k5BN-cpXFh33nx1QOjAAJqDwAC4fiQSOfWIcUnv0MtLwQ"]


util = Fivvy(TEMP_PATH)
bot = Bot(token=util.config['botToken'], parse_mode="html", disable_web_page_preview=True, timeout=30)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
util.set_dp(dp)

if not os.path.exists(TEMP_PATH):
    os.mkdir(TEMP_PATH)
###############################################################
####################### [ COMMANDS ] ##########################
###############################################################
@dp.message_handler(commands=['start'])
async def handle_StartMessage(message: types.Message):
    userid = message.from_user.id
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))

    userCheck =  await util.user_exists(userid)
    if not userCheck:
        return await sendRegistration(message)
    else:
        mainMessage = await util.user_get(userid, 'message')
        if mainMessage.get('id', 0) != 0:
            return await message.delete()
        
        return await sendMainMenu(message)

@dp.message_handler(commands=['lyric'])
async def lyricHandler(message: types.Message):
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))
        
    searchText = message.text or message.caption
    searchText = searchText.replace("/lyric", "").strip()
    if not searchText or len(searchText) < 5:
        if message.reply_to_message and message.reply_to_message.audio:
            if message.reply_to_message.audio.performer and message.reply_to_message.audio.title:
                searchText = f"{message.reply_to_message.audio.performer} - {message.reply_to_message.audio.title}"
            else:
                searchText = message.reply_to_message.audio.file_name


    if len(searchText) <= 10:
        return await message.delete()
    return await sendLyric(message, searchText)

@dp.message_handler(commands=['clip'])
async def clipHandler(message: types.Message):
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))

    searchText = message.text or message.caption
    searchText = searchText.replace("/clip", "").strip()
    if not searchText or len(searchText) < 5:
        if message.reply_to_message and message.reply_to_message.audio:
            if message.reply_to_message.audio.performer and message.reply_to_message.audio.title:
                searchText = f"{message.reply_to_message.audio.performer} - {message.reply_to_message.audio.title}"
            else:
                searchText = message.reply_to_message.audio.file_name

    if len(searchText) <= 10:
        return await message.delete()
    
    return await handleClipCommand(message, searchText, True)
###############################################################
####################### [ PUBLICS ] ##########################
###############################################################
async def handleQuery(message: types.Message):
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))


    userid = message.from_user.id
    functionActive = await util.user_get(userid, 'function_active')
    functionActiveDatas = functionActive.split("_") if functionActive else None
    if functionActiveDatas:
        if functionActiveDatas[0] == "searchTrack":
            await generateResult(message, functionActiveDatas[1])
            await message.delete()

        elif functionActiveDatas[0] == "findLyric":
            return await sendLyric(message, message.text)

        return

    await util.user_set(userid, {'updateMenu': True})
    return await util.add_to_dell(userid, message)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('inlineMenu_'))
async def main_Handler(callback_query: types.CallbackQuery):
    if callback_query.message.chat.type != "private":
        await callback_query.message.reply(BOT_UNAVAILABLE, "html")
        return await callback_query.message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))

    userid = callback_query.from_user.id
    username = callback_query.from_user.first_name

    getData = await util.user_get(userid, ['writeAlbum', 'lang', "update_s_mes"])

    writeAlbum = getData['writeAlbum']
    userLang = getData['lang']
    update_s_mes = getData['update_s_mes']


    dataStrip = callback_query.data.split("_")
    inlineType = dataStrip[1]
    #############################################################################
    if not await util.user_exists(userid) and inlineType != "reg":
        await sendRegistration(callback_query.message, userid, username)
        return await callback_query.message.delete()
    #############################################################################
    inlineData = dataStrip[2]

    if inlineType == "menu":
        if inlineData == "goMMenu":
            await util.user_set(userid, {'function_active': None})
            return await sendMainMenu(callback_query.message, userid, username)
            
        elif inlineData == "goSSettings":
            return await sendSettings(callback_query.message, userid, username, userLang)

        elif inlineData == "goSSearch":
            markup = await util.button_SearchTrack(lang=userLang)
            messageContent = await util.getText("searchTrack_Main", lang=userLang)
            await util.user_set(userid, {'function_active': None})
            return await edit_message(callback_query.message, messageContent, markup, userid, username)
        


        #################################################################################################################################
        
        
        
        if inlineData == "goSearch":
            markup = await util.button_SearchTrack(lang=userLang)
            messageContent = await util.getText("searchTrack_Main", lang=userLang)
            return await edit_message(callback_query.message, messageContent, markup, userid, username)
        
        elif inlineData == "goLyric":
            messageContent = await util.getText("searchTrack_TextSearch", lang=userLang)
            markup = await util.button_back(lang=userLang, to='menu')
            await util.user_set(userid, {'function_active': 'findLyric'})
            return await edit_message(callback_query.message, messageContent, markup, userid, username)

        elif inlineData == "goTag":
            messageContent = await util.getText("searchTags_Main", lang=userLang)
            markup = await util.button_back(lang=userLang, to='menu')
            await util.user_set(userid, {'function_active': 'findTags'})
            return await edit_message(callback_query.message, messageContent, markup, userid,  username)
            
        elif inlineData == "goHelp":
            messageContent = await util.getText("helpMessage", lang=userLang)
            markup = await util.button_back(lang=userLang, to='menu')
            await edit_message(callback_query.message, messageContent, markup, userid,  username)
            return
        
        elif inlineData == "goSettings":
            return await sendSettings(callback_query.message, userid, username, userLang)

        elif inlineData == "changeAlbumT":
            userAlbumText = await util.user_get(userid, 'writeAlbum')
            userAlbumText = not userAlbumText
            await util.update_user_db(userid, {'writeAlbum': userAlbumText})
            return await sendSettings(callback_query.message, userid, username, userLang)

        elif inlineData == "changeKeys":
            userButtons = await util.user_get(userid, 'sendKeys')
            userButtons = not userButtons
            await util.update_user_db(userid, {'sendKeys': userButtons})

            return await sendSettings(callback_query.message, userid, username, userLang)


        elif inlineData == "goSLang":
            markup = types.InlineKeyboardMarkup(row_width=2)
            keys = []

            for key in util.langTexts[userLang]:
                keys.append(types.InlineKeyboardButton(util.langTexts[userLang][key], callback_data="inlineMenu_clang_"+key))

            markup.add(*keys)
            markup.add(types.InlineKeyboardButton(util.fastButtongs[userLang]["Back"], callback_data="inlineMenu_menu_goSSettings"))

            messageContent = await util.getText("settingsLang", lang=userLang)
            await edit_message(callback_query.message, messageContent, markup, userid, username)
            return

    elif inlineType == "other":
        if inlineData == "del":
            try:
                await callback_query.message.delete()
                return
            except:
                return await callback_query.answer("I'm sorry, but this message is too old to be deleted. Delete it manually", True)

    elif inlineType == "sTrack":
        messageContent = await util.getText("searchTrack_TextSearch", lang=userLang)
        markup = await util.button_back(lang=userLang, to='search')
        await util.user_set(userid, {'function_active': f"searchTrack_{inlineData}"})
        return await edit_message(callback_query.message, messageContent, markup, userid, username)

    elif inlineType == "lyric":
        inlineData = inlineData.replace("-", " ").replace("..", " - ")
        inlineData = re.sub(r'\b(?:remastered|remix|clip)\b', '', inlineData, flags=re.IGNORECASE)
        return await sendLyric(callback_query.message,inlineData, userid, username, False)

    elif inlineType == "clip":
        inlineData = inlineData.replace("-", " ").replace("..", " - ")
        inlineData = re.sub(r'\b(?:remastered|remix|clip)\b', '', inlineData, flags=re.IGNORECASE)
        return await handleClipCommand(callback_query.message, inlineData, False, userid, username)

    elif inlineType == "deezer" or inlineType == "ytm" or inlineType == "sc":
        searchData = await util.user_get(userid, 'searchTracks')
        downloadID = int(inlineData)

        if not searchData or not searchData['count']:
            markup = await util.button_SearchTrack(lang=userLang)
            messageContent = await util.getText("searchTrack_Main", lang=userLang)
            await edit_message(callback_query.message, messageContent, markup,userid, username)
            return


        baseCheck = await util.get_from_base(searchData['list'][downloadID]['trackID'])
        if await util.user_get(userid, 'sendKeys'):
            artist = searchData['list'][downloadID]['artist']
            title = searchData['list'][downloadID]['title']

            artist = re.sub(r'\([^)]*\)', '', artist)
            title = re.sub(r'\([^)]*\)', '', title)

            artist = re.sub(r'[^\w\d]+', '-', artist)
            title = re.sub(r'[^\w\d]+', '-', title)
            dataText = f"{artist}..{title}"
            dataText = dataText[:20]
            audioMarkup = types.InlineKeyboardMarkup(row_width=2)
            lyricKey = types.InlineKeyboardButton(util.fastButtongs[userLang]["mainMenu_lyric"], callback_data=f"inlineMenu_lyric_{dataText}")
            clipKey = types.InlineKeyboardButton("Clip", callback_data=f"inlineMenu_clip_{dataText}")
            audioMarkup.add(lyricKey, clipKey)
        else:
            audioMarkup = None

        audioCaption = util.audioCaption.format(
            searchData['list'][downloadID]['artist'],
            searchData['list'][downloadID]['title'],
            "({})".format(searchData['list'][downloadID]['album']) if writeAlbum and  searchData['list'][downloadID]['album'] != " " else ""
        )

        if baseCheck:
            await callback_query.message.answer_audio(baseCheck['fileID'], audioCaption, "html", reply_markup=audioMarkup if audioMarkup else None, performer=searchData['list'][downloadID]['artist'], title=searchData['list'][downloadID]['title'])
        else:
            callbackAnswer = await util.getText("searchTrack_AlertStart", lang=userLang)
            callbackAnswer = callbackAnswer.format(
                searchData['list'][downloadID]['artist'],
                searchData['list'][downloadID]['title'],
            )
            await callback_query.answer(callbackAnswer, True)
            await bot.send_chat_action(callback_query.message.chat.id, "upload_voice")
            download = await util.download(asyncio.get_event_loop(), inlineType, searchData['list'][downloadID], userid)
            
            if download[0]:
                try:
                    audioMessage = await callback_query.message.answer_audio(open(download[0], "rb"), audioCaption, "html", reply_markup=audioMarkup if audioMarkup else None, performer=searchData['list'][downloadID]['artist'], title=searchData['list'][downloadID]['title'])
                except exceptions.ButtonDataInvalid:
                    audioMessage = await callback_query.message.answer_audio(open(download[0], "rb"), audioCaption, "html", reply_markup=None, performer=searchData['list'][downloadID]['artist'], title=searchData['list'][downloadID]['title'])
                
                await util.add_to_base(searchData['list'][downloadID]['trackID'], inlineType, audioMessage.audio.file_id, searchData['list'][downloadID]['artist'], searchData['list'][downloadID]['title'], searchData['list'][downloadID]['album'])
                os.remove(download[0])
            else:
                callbackAnswer = await util.getText("searchTrack_Error", lang=userLang)
                mesData = await callback_query.message.answer(callbackAnswer, "html")
                await util.add_to_dell(userid, mesData)

            
        await util.user_set(userid, {'updateMenu': True})
        if update_s_mes: return await sendMainMenu(callback_query.message, userid, username, True)
        
        return
    
    elif inlineType == "clang":
        if inlineData == "ru":
            if await util.user_get(userid, 'lang') == "uk":
                await callback_query.answer("Ви справді вважаєте себе людиною?", True)
            inlineData = "uk"

        check = await util.update_user_db(userid, {"lang": inlineData})
        if not check:
            return await callback_query.answer("An error occurred during the database update. Contact the Creator: @drhspfn", True)
        
        return await sendSettings(callback_query.message, userid, username, inlineData)
        
    elif inlineType == "shazam":
        shazamData = await util.user_get(userid, 'shazam_lyric')
        if inlineData == "lyric" and (shazamData and shazamData.get("artist", None) and shazamData.get('title', None) and shazamData.get("lyric", None)):
            lyricLen = "\n".join(shazamData['lyric'])
            if len(lyricLen) >= 4000:
                return await callback_query.answer("Sorry, the lyrics are too big for telegram message", True)
                 
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("DELETE ❌", callback_data="inlineMenu_other_del"))
            messageContent = await util.getText("lyricSuccess", userid)
            messageContent = messageContent.format(
                shazamData['artist'],
                shazamData['title'],
                lyricLen
            )
            return await callback_query.message.answer(messageContent, "html", reply_markup=markup)

        elif inlineData == "previewlink" and (shazamData.get("artist", None) and shazamData.get('title', None)):
            filename = '{} - {}.mp3'.format(shazamData['artist'], shazamData['title'])
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            filePath = f"{TEMP_PATH}{filename}"
            
            
            audio = await util.downloadPreview(asyncio.get_event_loop(), shazamData['previewlink'], filePath)
            await bot.send_chat_action(callback_query.message.chat.id, "upload_document")
            if audio:
                messageContent = util.audioCaption.format(
                    shazamData['artist'],
                    shazamData['title'],
                    " ", "", ""
                )
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton("DELETE ❌", callback_data="inlineMenu_other_del"))
                await callback_query.message.answer_audio(
                    audio, 
                    messageContent, 
                    "html",
                    performer=shazamData['artist'],
                    title=shazamData['title'],
                    reply_markup=markup
                )
                os.remove(filePath)
                return await util.user_set(userid, {'updateMenu': True})
            else:
                print("download error")

    elif inlineType == "reg":
        if inlineData == "ru": inlineData = "uk"
        if not await util.add_user(userid, inlineData):
            return await callback_query.answer("An error occurred during the database update. Contact the Creator: @drhspfn", True)
            

        await callback_query.answer("Registration successful. Enjoy using the bot😉", True)
        return await sendMainMenu(callback_query.message, userid, username)

async def sendMainMenu(message:types.Message, userid:int=None, username:str=None, update:bool=False, group:bool=False):
    userid = userid if userid else message.from_user.id
    username = username if username else message.from_user.first_name

    getData = await util.user_get(userid, ['lang', 'message'])

    userLang = getData['lang']
    mainMessage = getData['message']


    messageContent = await util.getText("startMessage", lang=userLang)
    messageContent = messageContent.format(username)
    markup = await util.button_MainMenu(lang=userLang)

    if mainMessage.get('id', 0) != 0:
        return await edit_message(message, messageContent, markup, userid, username, update)
    else:
        try:
            if group:
                newMainMessage = await bot.send_message(userid, messageContent,"html", reply_markup=markup,reply_to_message_id=message.message_id)
            else:
                newMainMessage = await message.answer(messageContent, "html", reply_markup=markup)
            await util.user_set(userid, {'message': {"id": newMainMessage.message_id, "chat": newMainMessage.chat.id}})
            return await message.delete()
        except exceptions.ChatNotFound:
            return
        except exceptions.BotBlocked:
            return
        except exceptions.ChatAdminRequired:
            return print("Бот не является администратором чата")
        except exceptions.RetryAfter as e:
            return print(f"Бот временно заблокирован. Повторить попытку через {e.timeout} секунд")
        except exceptions.NetworkError:
            return print("Проблемы с сетью или Telegram API")

async def edit_message(message:types.Message, messageContent:str, markup, userid:int=None, username:str=None, update:bool=False):
    userid = userid if userid else message.from_user.id
    username = username if username else message.from_user.first_name                  

    mainMessage = await util.user_get(userid, 'message')

    if not mainMessage.get('id', 0):
        newMessage = await bot.send_message(message.chat.id, messageContent, "html", reply_markup=markup)
        await util.user_set(userid, {'message': {'id': newMessage.message_id, "chat": newMessage.chat.id}})
        try:
            await message.delete()
        except:
            pass
        return 

    await util.del_all_mes(userid)


    if await util.user_get(userid, "updateMenu") or update:
        newMessage = await bot.send_message(mainMessage['chat'], messageContent, "html", reply_markup=markup)
        await bot.delete_message(mainMessage['chat'], mainMessage['id'])
        if not message.audio:
            try:await message.delete()
            except: pass
        return await util.user_set(userid, {'message': {'id': newMessage.message_id, "chat": newMessage.chat.id}, 'updateMenu': False})
    else:
        try:
            return await bot.edit_message_text(messageContent, mainMessage['chat'], mainMessage['id'], parse_mode="html", reply_markup=markup) 
        except exceptions.MessageToEditNotFound:
            await util.user_set(userid, {'message': {'id': 0, "chat": 0}})
            return await sendMainMenu(message, userid, username)
        except exceptions.RetryAfter as e:
            return print(f"Бот временно заблокирован. Повторить попытку через {e.timeout} секунд")
        except exceptions.TelegramAPIError as err:
            if str(err).find('Message is not modified') != -1:
                return print(f"|edit| Общая ошибка Telegram API\n\n{err}")
            else:
                return
            
async def generateResult(message:types.Message, type:str="deezer", searchQuery:str=None, userid:int=None, username:str=None):
    userid = userid if userid else message.from_user.id
    username = username if username else message.from_user.first_name
    searchQuery = searchQuery if searchQuery else message.text
    userAlbum = await util.user_get(userid, 'writeAlbum')
    searchData = await util.search(asyncio.get_event_loop(), type, searchQuery, message.from_user.id)
    
    
    if not searchData:
        messageContent = await util.getText("searchTrack_Error", userid)
        mesData = await message.answer(messageContent, "html")
        await util.user_set(userid, {'function_active': None})
        await util.add_to_dell(userid, mesData)
        await sendMainMenu(message, userid, username)
        return
    
    messageContent = await util.getText("searchTrack_Results", userid)
    markup = types.InlineKeyboardMarkup(row_width=2)
    keys = []
    for trackNum in range(searchData['count']):
        numText = str(trackNum+1)

        track = searchData['list'][trackNum]
        artist, title, album = track['artist'], track['title'], track['album']
        artist = re.sub(r'[<>]', '', artist)
        title = re.sub(r'[<>]', '', title)
        album = re.sub(r'[<>]', '', album)
        album_str = f" ({album})" if userAlbum and album != " " else ""
        messageContent += f"<b>#{numText}</b> | {artist} - {title}{album_str}\n"
        keys.append(types.InlineKeyboardButton(f"#{numText}", callback_data=f"inlineMenu_{type}_{trackNum}"))

    markup.add(*keys)
    markup.add(types.InlineKeyboardButton(util.fastButtongs[await util.user_get(userid, 'lang')]["Back"], callback_data="inlineMenu_menu_goSSearch"))
    await util.user_set(userid, {'function_active': None})
    return await edit_message(message, messageContent, markup, userid, username)

async def tagFinder(message:types.Message, userid:int, searchQuery:str, fileid):
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))

    mainMessage = await util.user_get(userid,"message")
    if mainMessage and mainMessage.get('id', 0) == 0:
        await sendMainMenu(message)
        return
    
    writeAlbum = await util.user_get(userid, 'writeAlbum')
    messageContent = await util.getText("searchTags_Updating", userid)
    messageData = await message.answer(messageContent, "html")
    await util.add_to_dell(userid, messageData)


    trackTags = await util.findTags(asyncio.get_event_loop(), searchQuery, userid)
    if trackTags.get("artist", None):
        audioPath = TEMP_PATH + await util.random_filename(True, "tag")
        await bot.download_file_by_id(fileid, audioPath)
        audiofile = eyed3.load(audioPath)
        if not audiofile.tag:
            audiofile.initTag()

        audiofile.tag.artist = trackTags['artist']
        audiofile.tag.album = trackTags['album']
        audiofile.tag.album_artist = trackTags['artist']
        audiofile.tag.title = trackTags['title']

        if trackTags.get("cover", None):
            response = urlopen(trackTags['cover'])  
            imagedata = response.read()
            audiofile.tag.images.set(3, imagedata , "image/jpeg" ,u"cover")
        audiofile.tag.save()
        audioData = open(audioPath, "rb")

        if await util.user_get(userid, 'sendKeys'):
            dataText = "{}..{}".format(trackTags['artist'], trackTags['title'])
            dataText = re.sub(r'[^\w\d]+', '-', dataText)
            audioMarkup = types.InlineKeyboardMarkup(row_width=2)
            lyricKey = types.InlineKeyboardButton(util.fastButtongs[await util.user_get(userid, 'lang')]["mainMenu_lyric"], callback_data=f"inlineMenu_lyric_{dataText}")
            clipKey = types.InlineKeyboardButton("Clip", callback_data=f"inlineMenu_clip_{dataText}")
            audioMarkup.add(lyricKey, clipKey)
        else:
            audioMarkup = None

        await util.user_set(userid, {"updateMenu": True})
        audioCaption = util.audioCaption.format(
            trackTags['artist'],
            trackTags['title'],
            "({})".format(trackTags.get('album', "")) if writeAlbum else ""
        )
        await message.answer_audio(audioData, audioCaption, "html", reply_markup=audioMarkup if audioMarkup else None)
            
        os.remove(audioPath)
        await sendMainMenu(message, update=True)
        return await message.delete()

async def sendLyric(message:types.Message, searchQuery:str, userid:int=None, username:str=None, delete:bool=True):
    userid = userid if userid else message.from_user.id
    username = username if username else message.from_user.first_name
    
    
    mainMessage = await util.user_get(userid,"message")
    if mainMessage and mainMessage.get('id', 0) == 0:
        await sendMainMenu(message, userid, username, True)
        return
    
    messageContent = await util.getText("lyricStart", userid)
    messageData = await message.answer(messageContent, "html")
    await util.add_to_dell(userid, messageData)

    await bot.send_chat_action(message.chat.id, "typing")
    geniusData = await util.genius(asyncio.get_event_loop(), searchQuery, userid)
    if geniusData:
        artist = geniusData['artist']
        title = geniusData['title']
        lyric = geniusData['lyric']
        url = geniusData['url']
        mesData = None
        if url and not lyric:
            messageContent = await util.getText("lyricTooLong", userid)
            messageContent = messageContent.format(url, artist, title)
            mesData = await message.answer(messageContent, "html", disable_web_page_preview=True)
            
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("DELETE ❌", callback_data="inlineMenu_other_del"))
            messageContent = await util.getText("lyricSuccess", userid)
            messageContent = messageContent.format(artist, title, lyric)

            #await util.add_lyric_to_db(asyncio.get_event_loop(), searchQuery, lyric)

            await message.answer(messageContent, "html", reply_markup=markup)

        await sendMainMenu(message, userid, username, True)
        if mesData:
            await util.add_to_dell(userid, mesData)

        if delete:
            try:await message.delete()
            except:pass

    else:
        return await sendMainMenu(message, userid, username)

async def handleClipCommand(message:types.Message, searchQuery:str=None, delete=True, userid:int=None, username:str=None):
    userid = userid if userid else message.from_user.id
    username = username if username else message.from_user.first_name


    mainMessage = await util.user_get(userid,"message")
    if mainMessage and mainMessage.get('id', 0) == 0:
        await sendMainMenu(message, userid, username)
        return
    
    if not searchQuery:
        if message.reply_to_message:
            if message.reply_to_message.audio:
                if message.reply_to_message.audio.performer and message.reply_to_message.audio.title:
                    searchQuery = f"{message.reply_to_message.audio.performer} - {message.reply_to_message.audio.title}"
                else:
                    searchQuery = message.reply_to_message.audio.file_name[:-4]
            
        else:
            if message.text:
                searchQuery = message.text.replace("/clip", "").strip()
    
    await message.answer_chat_action("typing")
    if searchQuery:
        clipData = await util.get_yt_clip(searchQuery)
        if clipData:
            videoURL = "https://www.youtube.com/watch?v=" + clipData['videoID']
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            keyLink = types.InlineKeyboardButton("YouTube", videoURL)
            keyDelete = types.InlineKeyboardButton("DELETE ❌", callback_data="inlineMenu_other_del")
            markup.add(keyLink, keyDelete)
            
            caption = await util.getText("searchClipSuccess", userid)
            caption = caption.format(videoURL, clipData['videoTitle'])

            try:
                mesData = await message.answer_photo(clipData['videoThumbnailPH'], caption,"html",reply_markup=markup)
            except exceptions.BadRequest:
                async with aiohttp.ClientSession() as session:
                    async with session.get(clipData['videoThumbnailPH']) as response:
                        image_data = await response.read()
                        mesData = await message.answer_photo(image_data, caption,"html",reply_markup=markup)


            await util.add_to_dell(userid, mesData)
            if delete: await message.delete()
        else:
            await message.delete()
    return

async def sendRegistration(message:types.Message, userid:int=None, username:str=None):
    userid = userid if userid else message.from_user.id
    userName = username if username else message.from_user.first_name

    userLang = "reg"
    markup = types.InlineKeyboardMarkup(row_width=2)
    keys = []

    for key in util.langTexts[userLang]:
        keys.append(types.InlineKeyboardButton(util.langTexts[userLang][key], callback_data="inlineMenu_reg_"+key))

    markup.add(*keys)
    messageText = await util.getText("startMessage_Lang", lang="en")
    messageText = messageText.format(userName)
    newMes = await message.answer(messageText, "html", reply_markup=markup)
    await util.user_set(userid, {'message': {'id': newMes.message_id, "chat": newMes.chat.id}})
    
@dp.message_handler(content_types=['video', 'voice'])
async def shazamHandler(message: types.Message):
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))

    
    userid = message.from_user.id
    ##################################################
    if not await util.user_exists(userid):
        return await sendRegistration(message)
    ##################################################

    getData = await util.user_get(userid,["message", 'lang'])

    mainMessage = getData['message']
    userLang = getData['lang']

    if mainMessage and mainMessage.get('id', 0) == 0:
        await sendMainMenu(message)
        return

    contentDuration = message.video.duration if message.video else message.voice.duration
    if contentDuration > 15:
        markup = await util.button_back(lang=userLang, to='menu')
        messageContent = await util.getText("shazam_DurationError", lang=userLang)
        await edit_message(message, messageContent, markup)
        return await message.delete()
        
    fileID = message.video.file_id if message.video else message.voice.file_id
    audioPath = TEMP_PATH + await util.random_filename(True, "shazam")

    await bot.download_file_by_id(fileID, audioPath)
    await bot.send_chat_action(message.chat.id, 'record_voice')

    shazamData = await util.getShazam(audioPath)
    if shazamData['matches']:
        artist = shazamData['track']['subtitle']
        title = shazamData['track']['title']

        previewLink = None
        lyricSection = None
        videoSection = None
        if 'actions' in shazamData["track"]['hub']:
            for itm in shazamData["track"]['hub']['actions']:
                if itm['type'] == "uri":
                    previewLink = itm['uri']
                    break
        if 'sections' in shazamData["track"]:
            for itm in shazamData["track"]['sections']:
                if itm['type'] == "LYRICS":
                    lyricSection = itm['text']
                    break
            for itm in shazamData["track"]['sections']:
                if itm['type'] == "VIDEO":
                    videoSection = itm
                    break


        messageContent = await util.getText("shazam_Founded", lang=userLang)
        messageContent = messageContent.format(artist, title)
        markup = await util.getShazamButtons(userid, lyricSection, videoSection, previewLink, artist, title)

        await bot.send_chat_action(message.chat.id, 'cancel')
        await edit_message(message, messageContent, markup)
        return await message.delete()

    return await message.delete() #

@dp.message_handler(content_types=['audio'])
async def handleAudioLyric(message: types.Message):
    if message.chat.type != "private":
        await message.reply(BOT_UNAVAILABLE, "html")
        return await message.answer_sticker(choice(BOT_UNAVAILABLE_STICKERS))

    
    userid = message.from_id
    ##################################################
    if not await util.user_exists(userid):
        return await sendRegistration(message)
    ##################################################
    mainMessage = await util.user_get(userid,"message")
    userLang = await util.user_get(userid,"lang")

    if mainMessage and mainMessage.get('id', 0) == 0:
        return await sendMainMenu(message)

    audioText = message.caption or message.text
    userFunction = await util.user_get(userid, "function_active")
    searchQuery = ""

    if userFunction == "use_LyricSearch" or (audioText and "/lyric" in audioText):
        captionChech = audioText.replace("/lyric", "").strip() if audioText else ""
        searchQuery = captionChech or (f"{message.reply_to_message.audio.performer} - {message.reply_to_message.audio.title}" if message.reply_to_message and message.reply_to_message.audio and message.reply_to_message.audio.performer and message.reply_to_message.audio.title else message.reply_to_message.audio.file_name if message.reply_to_message and message.reply_to_message.audio else f"{message.audio.performer} - {message.audio.title}" if message.audio and message.audio.performer and message.audio.title else message.audio.file_name if message.audio else None)

        if searchQuery and len(searchQuery) > 3: return await sendLyric(message, searchQuery)
        else: return await message.delete()

    elif userFunction == "findTags" or (audioText and "/tag" in audioText):
        if message.audio:
            if message.audio.file_name.split(".")[-1] != "mp3":
                messageContent = await util.getText("searchTags_ErrorExt", userid)
                markup = await util.button_back(lang=userLang, to='menu')
                await edit_message(message, messageContent, markup)
                return await message.delete()
                
            if audioText:
                searchQuery = audioText.replace("/tag", "").strip() 
            else:
                if message.audio:
                    if message.audio.performer and message.audio.title:
                        searchQuery = f"{message.audio.performer} - {message.audio.title}"
                    else:
                        searchQuery = message.audio.file_name

                elif message.reply_to_message:
                    if message.reply_to_message.audio:
                        if message.reply_to_message.audio.performer and message.audio.reply_to_message.title:
                            searchQuery = f"{message.audio.reply_to_message.performer} - {message.audio.reply_to_message.title}"
                        else:
                            searchQuery = message.audio.reply_to_message.file_name

            await tagFinder(message, userid, searchQuery, message.audio.file_id)
        else:
            mesData = await message.answer("Please send the audio file directly or reply to my audio message.")
            await util.add_to_dell(userid, mesData)
    else:
        await message.answer("Invalid command.")

async def sendSettings(message:types.Message, userid:int=None,username:str=None, userLang:str=None):
    userid = userid if userid else message.from_user.id
    username = username if username else message.from_user.first_name
    userLang = userLang if userLang else await util.user_get(userid, 'lang')
    userButtons = await util.user_get(userid, 'sendKeys')
    userAlbumText = await util.user_get(userid, 'writeAlbum')
    messageContent = await util.getText("settingsMain", lang=userLang)
    messageContent = messageContent.format(
        "✅" if userButtons else "❌",
        "✅" if userAlbumText else "❌"
    )
    markup = await util.button_Settings(lang=userLang)
    await util.user_set(userid, {'function_active': None})
    return await edit_message(message, messageContent, markup, userid, username)

@dp.inline_handler()
async def process_inline_query(query: types.InlineQuery):
    queryText = query.query
    
    if len(queryText) >= 6:
        CALLBACK_TEXT = "Use the button to download: {} - {} {}"
        tracks = await  util.search(asyncio.get_event_loop(), "deezer", queryText, query.from_user.id)
        results = []
        for track in tracks['list']:
            title = track.get('title')
            artist = track.get('artist')
            track_id = track.get('trackID')
            album = track.get('album')
            cover = track.get('cover')
            CALLBACK_TEXT = CALLBACK_TEXT.format(artist, title, "({})".format(album) if album else "")
            
            button = types.InlineKeyboardButton(text="Download", callback_data=track_id)
            keyboard = types.InlineKeyboardMarkup().add(button)
            result = types.InlineQueryResultArticle(
                id=track_id,
                title=title,
                thumb_url=cover,
                description=artist,
                input_message_content=types.InputTextMessageContent(message_text=CALLBACK_TEXT),
                reply_markup=keyboard
            )
            

            results.append(result)

        await bot.answer_inline_query(query.id, results)

@dp.callback_query_handler(lambda c: True)
async def process_callback_query(callback_query: types.CallbackQuery):
    #print(callback_query.data)
    trackID = int(callback_query.data)
    baseCheck = await util.get_from_base(trackID)
    writeAlbum = await util.user_get(callback_query.from_user.id, 'writeAlbum')
    if baseCheck:
        artist = baseCheck.get('artist', "")
        title = baseCheck.get('title', "")
        album = baseCheck.get('album', "")
        audioCaption = util.audioCaption.format(
            artist,
            title,
            "({})".format(album if album != " " else "") if writeAlbum else ""
        )
        try:
            await bot.send_audio(callback_query.from_user.id, baseCheck['fileID'], audioCaption, "html", performer=artist, title=title)
        except exceptions.BotBlocked:
            return
        
    else:
        data = await util.download_by_id(asyncio.get_event_loop(), "deezer", trackID)
        if data:
            artist = data.get('artist', "")
            title = data.get('title', "")
            album = data.get('album', "")
            audioCaption = util.audioCaption.format(
                artist,
                title,
                "({})".format(album if album != " " else "") if writeAlbum else ""
            )
            
            file = await bot.send_audio(callback_query.from_user.id, open(data['path'], 'rb'), audioCaption, "html", performer=artist, title=title)
            await util.add_to_base(trackID,'deezer', file.audio.file_id, artist, title, album)
            os.remove(data['path'])

    return



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
