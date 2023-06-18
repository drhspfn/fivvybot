from aiogram import Dispatcher, types
import sqlite3
import json, sys, os
from aiogram.utils import exceptions
from async_lru import alru_cache
from datetime import datetime
import time
import random, re
import asyncio
import eyed3
from urllib.request import urlopen
from typing import Union
import unidecode
import requests
from shazamio import Shazam
import ytmusicapi
import pytube as pt 
from pydeezer import Deezer
import lyricsgenius
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from youtubesearchpython.__future__ import VideosSearch
import logging
import string

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(levelname)s | %(message)s')



TEMP_PATH = "./data/temp/"
NO_IMAGE_URL = "https://targettiles.co.uk/wp-content/uploads/2019/09/products-sku2015_854.jpg"
YOUTUBE_REGEX_ID = r"(?:\/|%3D|v=|vi=|v%3D|youtu.be%2F|embed\/|e\/|watch\?|&v=|\?v=|&vi=)([0-9A-Za-z_-]{11})"

class Fivvy:
    def __init__(self, dp:Dispatcher=None) -> None:
        logging.log(logging.INFO, "Start the bot init...")
        self.DP = dp
        self.config = {}
        self.locales = {}

        self.WEB_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"}
        self.audioCaption = "<code>{} - {} {}</code>\n\n<a href='tg://user?id=5994630794'>Fivvy Music 🇺🇦</a>"



        self.DATA = {}
        self.default = {
            "lang": "xx",               # User language
            "ad": True,                 # On/Off ads in the bot
            "update_s_mes": False,      # After downloading a track, whether or not to automatically go to the menu
            "sendKeys": True,           # The 'Lyric' 'Clip' buttons in the audio message
            "reg_date": "00.00.2022",   # User registration date
            "dls": -1,                  # Number of tracks downloaded by the user
            "cached_dls": -1,           # Same thing, but the cache
            "writeAlbum": True,         # Whether to send a track album in messages
            "message": {"id": 0, "chat":0},         # Place for information about the message-main menu
            "searchTracks":{"search_type":"", "count": 0, "list": []},      # Track search info
            "function_active": None,    # Which function is active, searchTags, searchLyric and other
            "updateMenu": False,        # Whether to update the menu, so it does not fly up in the chat
            "mes_to_dell": [],          # Message list for deletion, errors, user's messages...
            "shazam_lyric": {"lyric": "", "artist": "", "title": "", "previewlink":""} # shazam.. idk. ;)
        }


        self._load_config()
        self._loadLocales()


        # ...
        self.fastButtongs = {}
        for lang, translations in self.locales.items():
            self.fastButtongs.update({lang: translations['Butons']})


        # language text for buttons
        self.langTexts = {
            "en": {"uk": "Ukrainian 🇺🇦","de":"German 🇩🇪", "ru": "Russian"},
            "uk": {"en": "Англійська 🇺🇸","de": "Німецька 🇩🇪","ru": "Роciйська"},
            "de": {"en": "Englisch 🇺🇸", "uk" :"Ukrainisch 🇺🇦","ru": "Russisch"},
            "reg": {"en": "English 🇺🇸", "uk": "Ukrainian 🇺🇦","de":"German 🇩🇪"},
            "none": "🏳️"
        }

        # Init the API's
        try:
            logging.log(logging.INFO, "Set up local Web Session...")
            self.WebSession = requests.Session()
            self.WebSession.headers.update(self.WEB_HEADERS)
            logging.log(logging.INFO, "Set up Shazam API...")
            self.shazam = Shazam()
            logging.log(logging.INFO, "Set up Deezer API...")
            self.deezerAPI = Deezer(self.config['deezerARL'])
            print(self.deezerAPI.get_cookies())
            logging.log(logging.INFO, "Set up YT Music API...")
            self.ytmusicAPI = ytmusicapi.YTMusic(auth = "./data/ytm_oauth.json")
            logging.log(logging.INFO, "Set up Genus API...")
            self.geniusAPI = lyricsgenius.Genius(self.config['geniusAPI']) 
            logging.log(logging.INFO, "Set up Spotify API...")
            self.spotifyAPI = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=self.config['SPOTIFY']['CLIENT_ID'],
                    client_secret=self.config['SPOTIFY']['CLIENT_SECRET']
                )
            )

            self.conn = sqlite3.connect("./data/fivvybot.db")
            self.cursor = self.conn.cursor()
        except Exception as error:
            sys.exit(error)


    def _load_config(self):
        try:
            with open('./data/config.json', 'r', encoding="utf-8") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            sys.exit()

    def _loadLocales(self):
        for file_name in os.scandir('./data/locales'):
            if file_name.name.endswith('.json') and file_name.is_file():
                localization = os.path.splitext(file_name.name)[0]
                with open(file_name.path, 'r', encoding='utf-8') as f:
                    self.locales[localization] = json.load(f)

    async def getText(self, phrase:str, userid:int=None, lang:str=None):
        if userid:
            lang = await self.user_get(userid, "lang")            

        if lang in self.locales:
            return self.locales[lang].get(phrase, self.locales[lang]['error'])
        else:
            return "unknown language"

    """
        USERS
    """
    async def add_user(self, userid:int, lang:str):  
        sql = "INSERT INTO users (userID, lang, reg_date) VALUES (?, ?, ?);"
        try:
            current_date = datetime.now()
            reg_date = current_date.strftime("%d.%m.%Y")
            self.conn.execute(sql, (userid,lang,reg_date,))
            self.conn.commit()
            self.user_exists.cache_clear()
            await self.user_set(userid, {"lang": lang, "ad": True})
            return True
        
        except Exception as err:
            return False
    @alru_cache(maxsize=32, ttl=30)
    async def user_exists(self, userid:int):
        sql = f"SELECT lang, ad, sendKeys, writeAlbum, dls, reg_date, update_s_mes FROM users WHERE userID = {userid}"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        if rows:
            return {
                "userid": userid,
                "lang": rows[0][0],
                "ad": bool(rows[0][1]),
                "sendKeys": bool(rows[0][2]),
                "writeAlbum": bool(rows[0][3]),
                "dls": int(rows[0][4]),
                "reg_date": rows[0][5],
                "update_s_mes": bool(rows[0][6])
            }
        
    async def _default_user(self, userid:int):
        userData = await self.user_exists(userid)
        data = self.default
        if userData:
            data.update({
                "lang": userData['lang'],
                "ad": userData['ad'],
                "sendKeys": userData['sendKeys'],
                'writeAlbum': userData['writeAlbum'],
                'update_s_mes': userData['update_s_mes'],
                "reg_date": userData['reg_date'],
                "dls": userData['dls'],
                "cached_dls": userData['dls'],
            })

        await self.DP.storage.set_data(user=userid, data=data)
        return data

    async def update_user_db(self, userid:int, data:dict):
        try:
            if 'lang' in data:
                await self.user_set(userid, {"lang": data['lang']})
                self.user_exists.cache_clear()
                #await self._clear_user_exists(userid)
                await self.resetButtons()
    

            sql = "UPDATE users SET {} WHERE userID = {}"
            sqlList = []
            for dataKey in data.keys():
                await self.user_set(userid, {dataKey: data[dataKey]})
                insert = data[dataKey]
                if type(insert) == bool: insert = int(insert)
                sqlList.append("{} = '{}'" .format(dataKey,insert)) 

            sql = sql.format(" ".join(sqlList), userid)
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        
        except Exception as err:
            print(err)
            return False

    """
        GENIUS
    """
    def _get_genius(self, search_query:str, userid:int):
        answerResult = {"artist":"", "title": "", "lyric":"", "url": ""}
        try:
            geniusSearch = self.geniusAPI.search_songs(search_query, 1)
            if geniusSearch:
                if geniusSearch.get("hits", None) != None:
                    parseUrl = geniusSearch['hits'][0]['result']['url']
                    
                    resultLyric = self.geniusAPI.lyrics(song_url=parseUrl)
                    resultLyric = resultLyric.split("\n")
                    resultLyric.pop(0)
                    resultLyric = '\n'.join(resultLyric)
                    if len(resultLyric) >= 4000:
                        answerResult["url"] = parseUrl
                    else:
                        answerResult["lyric"] = resultLyric

                    titleFixed = geniusSearch['hits'][0]['result']['full_title']
                    if titleFixed.find("by") != -1:
                        titleFixed = titleFixed.split("by")[0].strip()
                    

                    answerResult["artist"] = geniusSearch['hits'][0]['result']['artist_names']
                    answerResult["title"] = titleFixed
                    return answerResult
        except:
            return None   
        
        return None

    async def genius(self, loop:asyncio.BaseEventLoop, search_query:str, userid:int):
        return await loop.run_in_executor(None, lambda: self._get_genius(search_query, userid))

    """
        TAG FINDER
    """
    def _get_tags(self, search_query:str, userid:int):
        answer = {'cover': '', 'artist':'', 'title': '', 'album':''}
        spotifyResults = self.spotifyAPI.search(search_query , limit=1)
        if spotifyResults:
            for track in spotifyResults['tracks']['items']:
                answer.update({
                    'title': track['name'],
                    "album": track['album']['name'],
                    'cover': track['album']['images'][0]['url'],
                    'artist': ', '.join(artist['name'] for artist in track['artists'])
                
                })
            return answer
        
        return None

    async def findTags(self, loop:asyncio.BaseEventLoop, search_query:str, userid:int):
        return await loop.run_in_executor(None, lambda: self._get_tags(search_query, userid))
    

    """
        SHAZAM
    """
    async def getShazam(self, pathFile:str):
        sondData = await self.shazam.recognize_song(pathFile)
        os.remove(pathFile)
        return sondData

    async def getShazamButtons(self, userid, lyricSection, videoSection, previewLink, artist, title):
        userLang = await self.user_get(userid, "lang")
        markup = types.InlineKeyboardMarkup(row_width=2)

        youtubeLink = self.WebSession.get(videoSection.get('youtubeurl', ''))
        ytLink = youtubeLink.json().get('actions', [{}])[0].get('uri') if youtubeLink.ok else None

        buttons = [
            ("SEND LYRIC", "lyric", lyricSection),
            ("LISTEN PREVIEW", "previewlink", previewLink),
            ("YOUTUBE", None, ytLink)
        ]
        await self.user_set(userid, {"shazam_lyric": {"lyric":lyricSection, "artist": artist, "title": title, "previewlink": previewLink}})
        for text, key, value in buttons:
            if value:
                if text == "YOUTUBE":
                    markup.add(types.InlineKeyboardButton(text, value))
                else:
                    markup.add(types.InlineKeyboardButton(text, callback_data=f"inlineMenu_shazam_{key}"))


        markup.add(types.InlineKeyboardButton(self.fastButtongs[userLang]["Back"], callback_data="inlineMenu_menu_goMMenu"))
        return markup

    """
        DOWNLOAD
    """

    async def downloadPreview(self, loop:asyncio.BaseEventLoop, url:str, filePath:str):
        return await loop.run_in_executor(None, lambda: self._downloadPreview(url, filePath))

    def _downloadPreview(self, url:str, filePath:str):
        with self.WebSession.get(url, stream=True) as response:
            with open(filePath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                    else:
                        break

        return open(filePath, "rb")

    def _downloadTrack(self, download_from:str, track:dict, userid:int):
        fileName = f"{track['artist']} - {track['title']}"
        fileName = re.sub(r'[^\w\d]+', '-', fileName)

        fileName = unidecode.unidecode_expect_nonascii(fileName) 
        path_to_mp3 = f"{TEMP_PATH}/{fileName}"

        if track:
            try:
                if download_from == "deezer":
                    deezerTrack = self.deezerAPI.get_track(track['trackID'])
                    #print(("link", self.deezerAPI.get_track_download_url(deezerTrack['info'])))
                    self.deezerAPI.download_track(
                        deezerTrack['info'], 
                        TEMP_PATH,
                        with_metadata=True,
                        with_lyrics=False,
                        show_messages=False,
                        filename=fileName
                    ) 
                elif download_from == "sc":
                    downlod_link = track.get('sc_link', None)
                    newName = track.get('permalink', None)
                    if newName: path_to_mp3 = f"{TEMP_PATH}/{newName}"
                    
                    if downlod_link and newName:
                        cmd = f"scdl -l {downlod_link} --path {TEMP_PATH} --onlymp3 --auth-token {self.config.get('soundcloudAUTH')} --name-format {newName} --hide-progress --hidewarnings"
                        os.system(cmd)
                    else:
                        return (None, )
                        


                elif download_from == "ytm":
                    ytdl = pt.YouTube("https://www.youtube.com/watch?v="+track['trackID'])
                    t = ytdl.streams.filter(only_audio=True).first()
                    out_file = t.download(output_path=TEMP_PATH, )
                    base, _ = os.path.splitext(out_file)
                    path_to_mp3 = base
                    os.system(f'ffmpeg -i "{out_file}" -vn -ar 44100 -loglevel quiet -ac 2 -b:a 192k "{path_to_mp3+".mp3"}"')
                    os.remove(out_file)

                    audiofile = eyed3.load(path_to_mp3 + '.mp3')
                    audiofile.tag.artist = track['artist']
                    audiofile.tag.album = track['album']
                    audiofile.tag.album_artist = track['artist']
                    audiofile.tag.title = track['title']
                    if track['cover']:
                        try:
                            response = urlopen(ytdl.thumbnail_url)
                            imagedata = response.read()
                            audiofile.tag.images.set(3, imagedata, "image/jpeg", u"cover")
                        except Exception as err:
                            print("error download cover: " + str(err))
                    audiofile.tag.save()
            
            except Exception as err:
                print(err)
                return (None,)
            return (path_to_mp3+".mp3",)

        return (None, )
    
    async def download(self, loop:asyncio.BaseEventLoop, download_from:str, track:dict, userid:int):
        time_start = time.time()
        print("start downloading")
        data = await loop.run_in_executor(None, lambda: self._downloadTrack(download_from, track, userid))
        
        time_end = time.time()
        total_time = time_end - time_start
        #logging.log(logging.INFO, f"[DL] 'download' made a request for: {total_time:.3f}")
        return data

    def _download_by_id(self, download_from:str, track_id:int):    
        if download_from == "deezer":
            deezerTrack = self.deezerAPI.get_track(track_id)
            artist = deezerTrack['tags'].get('artist', "")
            title = deezerTrack['tags'].get('title', "")
            album = deezerTrack['tags'].get("album", "")
            ####################################################
            artist_new = re.sub(r'[^\w\d]+', '-', artist)
            artist_new = re.sub(r'[<>:"/\\|?*]', '', artist_new)
            ####################################################
            title_new = re.sub(r'[^\w\d]+', '-', title)
            title_new = re.sub(r'[<>:"/\\|?*]', '', title_new)
            ####################################################
            ####################################################
            filename = "{}-{}.mp3".format(artist_new, title_new)
            self.deezerAPI.download_track(
                deezerTrack['info'], 
                TEMP_PATH,
                with_metadata=True,
                with_lyrics=False,
                show_messages=False,
                filename=filename
            ) 


        path_to_mp3 = f"{TEMP_PATH}/{filename}"
        return {"path": path_to_mp3, "artist": artist, "title": title, "album": album}
    

    async def download_by_id(self, loop:asyncio.BaseEventLoop, download_from:str, track_id:int):
        return await loop.run_in_executor(None, lambda: self._download_by_id(download_from, track_id))

    
    """
        SEARCH
    """
    async def get_yt_clip(self, search_qu:str):
        videosSearch = VideosSearch(search_qu, limit = 1)
        videosResult = await videosSearch.next()
        if videosResult.get('result', []):
            return {
                "videoID": videosResult['result'][0]['id'],
                "videoTitle": videosResult['result'][0]['title'],
                "videoThumbnailPH": videosResult['result'][0]['thumbnails'][-1]['url']
            }
    
        return None

    async def get_from_base(self, searchID):
        time_start = time.time()

        sql = f"SELECT * FROM music WHERE searchID = '{searchID}'"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()


        time_end = time.time()
        total_time = time_end - time_start
        #logging.log(logging.INFO, f"[DB] 'get_from_base' made a request for: {total_time:.3f}")
        
        if rows:
            return {
                "searchID": searchID,
                "service_type": rows[0][1],
                "fileID": rows[0][2],
                "artist": rows[0][3],
                "title": rows[0][4],
                "album": rows[0][5],
            }
    
    async def add_to_base(self, searchID, service_type:str, fileID, audio_artist:str, audio_title:str, audio_album:str=""):
        sql = "INSERT INTO music (searchID, service_type, fileID, artist, title, album) VALUES (?, ?, ?, ?, ?, ?);"
        try:
            self.conn.execute(sql, (searchID, service_type, fileID, audio_artist, audio_title, audio_album, ))
            self.conn.commit()
            return True
        except Exception as err:
            return False

    async def _get_statistics(self, admin:bool=False) -> dict:
        time_start = time.time()

        ############################################
        total_stats = {}
        sql = "SELECT service_type, COUNT(*) AS count FROM music WHERE service_type IN ('deezer', 'ytm', 'sc') GROUP BY service_type;"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        for row in rows:
            if admin: total_stats.update({row[0]: row[1]})
            else: total_stats.update({row[0]: int(row[1]) + 476})

        self.cursor.execute("SELECT COUNT(*) FROM users")
        user_result = self.cursor.fetchone()
        user_count = user_result[0]
        if admin: total_stats.update({"users": user_count})
        else: total_stats.update({"users": int(user_count)+1213})
        ############################################
        time_end = time.time()
        total_time = time_end - time_start
        #logging.log(logging.INFO, f"[DB] '_get_statistics' made a request for: {total_time:.3f}")
        return total_stats

    def _search_tracks(self, search_type:str, search_query:str, userid:int):
        answerResult = {"search_type":search_type, "count": 0, "list": []}
        ################################################################################
        if search_type == "deezer":
            deezerData = self.deezerAPI.search_tracks(search_query, 10)
            if deezerData:
                for track in deezerData:
                    answerResult['list'].append({
                        "trackID": track['id'],
                        "artist":track['artist']['name'],
                        "title":track['title'],
                        "album": track['album']['title'] if 'album' in track else " ",
                        "cover": track.get('album', {}).get("cover_medium", "-")
                    })
                    answerResult['count'] += 1
        ################################################################################
        elif search_type == "ytm":
            ytmResults = self.ytmusicAPI.search(search_query, "songs",)
            if ytmResults:
                for track in ytmResults[:10]:
                    try:
                        answerResult['list'].append({
                            "trackID": track['videoId'],
                            "artist": ", ".join(artist["name"] for artist in track['artists']),
                            "title": track['title'],
                            "album": track['album'].get('name', ''),
                            "cover": track['thumbnails'][-1]['url']
                        })
                    except AttributeError:
                        continue

                    answerResult['count'] += 1
        
        elif search_type == "sc":
            search_url = f"https://api-v2.soundcloud.com/search/tracks?q={search_query}&sc_a_id=61d7a44c6d2f985830d3cab8a015b1016710057f&variant_ids=&facet=genre&user_id=890701-793020-659807-587111&client_id=DgFeY88vapbGCcK7RrT2E33nmNQVWX82&limit=10&offset=0&linked_partitioning=1&app_version=1684503954&app_locale=en"
            req = self.WebSession.get(search_url)
            if req:
                data = req.json().get('collection', {})
                if data:
                    with open('track_data.json', 'w') as f:
                        json.dump(data, f, indent=4)
                    for track in data:
                        try:
                            title = track.get('title', 'unknown')
                            artist = track.get('publisher_metadata', {}).get('artist', None)
                            if not artist:
                                artist = track.get('user').get('full_name')
                                if not artist:
                                    artist = track.get('user').get('username')
                            
                            title = title.replace(artist, "").strip()

                            album = track.get('publisher_metadata', {}).get('album_title', title)
                            album = album.replace(artist, "").strip()
                            answerResult['list'].append({
                                "trackID": track['id'],
                                "sc_link": track.get('permalink_url', None),
                                "permalink": track.get('permalink', None),
                                "artist": artist,
                                "title": title,
                                "album": album,
                                "cover": track.get('artwork_url', "")
                            })
                        except AttributeError:
                            continue

                        answerResult['count'] += 1


        
        if  answerResult['count']:
            return answerResult
        
        return None
    
    @alru_cache(maxsize=32)
    async def search(self, loop:asyncio.BaseEventLoop, search_type:str, search_query:str, userid:int):
        time_start = time.time()


        toUpdate =  await loop.run_in_executor(None, lambda: self._search_tracks(search_type, search_query, userid))
        await self.user_set(userid, {"searchTracks": toUpdate})

        time_end = time.time()
        total_time = time_end - time_start
        #logging.log(logging.INFO, f"[FC] 'search' made a request for: {total_time:.3f}")
        return toUpdate
    
    
    def _youtube_by_id(self, video_id:str):
        video  = pt.YouTube("https://www.youtube.com/watch?v="+video_id)
        
        return video.bypass_age_gate()

    async def youtube_by_id(self, loop:asyncio.BaseEventLoop, video_id:str):
        return await loop.run_in_executor(None, lambda: self._youtube_by_id(video_id))

    """
        OTHER
    """
    @alru_cache(maxsize=32)
    async def youtube_id(self, url):
        match = re.search(YOUTUBE_REGEX_ID, url)
        if match:
            video_id = match.group(1)
            return video_id
        else:
            return None


    def set_dp(self, dp:Dispatcher):
        self.DP = dp

    async def random_filename(self, mp3: bool = True, fileType: str = "temp", needExt:bool=True):
        extension = "mp3" if mp3 else "ogg"
        if needExt: return f"{fileType.strip()}_{random.randint(1, 9999)}.{extension}"
        else: return f"{fileType.strip()}_{random.randint(1, 9999)}"

    async def resetButtons(self):
        self.button_MainMenu.cache_clear()
        self.button_Settings.cache_clear()

    @alru_cache(maxsize=32)
    async def button_MainMenu(self, userid=None, lang=None):
        if lang:  userLang = lang
        elif userid: userLang = await self.user_get(userid, "lang")
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        keySearch = types.InlineKeyboardButton(self.fastButtongs[userLang]["mainMenu_search"], callback_data="inlineMenu_menu_goSearch")
        keyLyric = types.InlineKeyboardButton(self.fastButtongs[userLang]["mainMenu_lyric"], callback_data="inlineMenu_menu_goLyric")
        keyTag = types.InlineKeyboardButton(self.fastButtongs[userLang]["mainMenu_tag"], callback_data="inlineMenu_menu_goTag")
        keyHelp = types.InlineKeyboardButton(self.fastButtongs[userLang]["Help"], callback_data="inlineMenu_menu_goHelp")
        keySettings = types.InlineKeyboardButton(self.fastButtongs[userLang]["mainMenu_settings"], callback_data="inlineMenu_menu_goSettings")
        markup.add(keySearch, keyLyric, keyTag)
        markup.add(keyHelp)
        markup.add(keySettings)
        return markup

    @alru_cache(maxsize=32)
    async def button_Settings(self, userid=None, lang=None):
        if lang:  userLang = lang
        elif userid: userLang = await self.user_get(userid, "lang")
        #userLang = await self.user_get(userid, "lang")
        userAd = False#await self.get_user(userid, "ad")

        markup = types.InlineKeyboardMarkup(row_width=2)
        keyLanguage = types.InlineKeyboardButton(self.fastButtongs[userLang]["settings_Lang"], callback_data="inlineMenu_menu_goSLang")
        keyAudioKeys = types.InlineKeyboardButton(self.fastButtongs[userLang]["settings_Keys"], callback_data="inlineMenu_menu_changeKeys")
        keyAlbumText = types.InlineKeyboardButton(self.fastButtongs[userLang]["settings_Album"], callback_data="inlineMenu_menu_changeAlbumT")
        keyBack = types.InlineKeyboardButton(self.fastButtongs[userLang]["Back"], callback_data="inlineMenu_menu_goMMenu")
        if userAd:
            keyBuyAD = types.InlineKeyboardButton(self.fastButtongs[userLang]["settings_buyAD"], callback_data="inlineMenu_menu_goSAd")
            markup.add(keyLanguage, keyBuyAD)
        else:
            markup.add(keyLanguage, keyAudioKeys, keyAlbumText)
        
        markup.add(keyBack)
        return markup

    @alru_cache(maxsize=32)
    async def button_SearchTrack(self, userid=None, lang=None):
        if lang:  userLang = lang
        elif userid: userLang = await self.user_get(userid, "lang")
        markup = types.InlineKeyboardMarkup(row_width=2)
        key_Deezer = types.InlineKeyboardButton("Deezer", callback_data="inlineMenu_sTrack_deezer")
        key_SC = types.InlineKeyboardButton("SoundCloud (beta)", callback_data="inlineMenu_sTrack_sc")
        key_YTM = types.InlineKeyboardButton("YT Music", callback_data="inlineMenu_sTrack_ytm")
        key_Back = types.InlineKeyboardButton(self.fastButtongs[userLang]["Back"], callback_data="inlineMenu_menu_goMMenu")
        markup.add(key_YTM, key_Deezer, key_SC, key_Back)

        return markup
    
    @alru_cache(maxsize=32)
    async def button_back(self, userid=None, lang=None, to:str="menu"):
        to_dict = {
            "menu": "goMMenu",
            'search': 'goSSearch'
        }

        if lang:  userLang = lang
        elif userid: userLang = await self.user_get(userid, "lang")

        markup = types.InlineKeyboardMarkup(row_width=2)
        key_Back = types.InlineKeyboardButton(self.fastButtongs[userLang]["Back"], callback_data=f"inlineMenu_menu_{to_dict[to]}")
        markup.add(key_Back)

        return markup
    """
        NEW DATA SYSTEM
    """

    async def user_get(self, userid, key:Union[str, list]):
        data = await self.DP.storage.get_data(user=userid)
        if not data:
            await self._default_user(userid)
            return await self.user_get(userid, key)

        if isinstance(key, str):
            return data.get(key, {})
        elif isinstance(key, list):
            answer = {}
            for itm in key:
                answer.update({itm: data.get(itm, {})})
                
            return answer
        else:
            return data

    async def user_set(self, userid:int, data:dict):
        userData = await self.DP.storage.get_data(user=userid)
        if not userData:
            await self._default_user(userid)
            return await self.user_set(userid, data)
        
        userData.update(data)
        #print(userData)
        return await self.DP.storage.set_data(user=userid, data=userData)

    async def add_to_dell(self, userid:int, message:types.Message):
        data = await self.DP.storage.get_data(user=userid)
        if not data:
            await self._default_user(userid)
            return await self.add_to_dell(userid, message)
        
        data['mes_to_dell'].append(message)
        return await self.DP.storage.set_data(user=userid, data=data)

    async def del_all_mes(self, userid):
        data = await self.DP.storage.get_data(user=userid)
        if not data:
            await self._default_user(userid)
            return await self.del_all_mes(userid)

        if data['mes_to_dell']:
            for mesID in range(len(data['mes_to_dell'])):
                try:
                    await data['mes_to_dell'][mesID].delete()
                except exceptions.MessageToDeleteNotFound:
                    continue

            data['mes_to_dell'].clear()
            return await self.DP.storage.set_data(user=userid, data=data)

    async def random_fast_key():
        groups = [
            ''.join(random.choices(string.ascii_uppercase, k=4)),
            ''.join(random.choices(string.ascii_uppercase, k=4)),
            ''.join(random.choices(string.ascii_uppercase, k=3)),
            ''.join(random.choices(string.ascii_uppercase, k=4))
        ]
        result = '-'.join(groups)
        return result




    def search_custom_tracks(self, text_data:str):
        self.cursor.execute("SELECT file_id, search_text FROM custom_tracks WHERE search_text LIKE ?", ('%' + text_data + '%',))
        results = self.cursor.fetchall()
        return results
