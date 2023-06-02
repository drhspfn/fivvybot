# FivvyBot

## Description
A small bot, written for my own use. Has the following functions: 
* Menu, fully implemented on inline buttons, using a single message
* Storing users in the database, in the directory `./data/fivvybot.db`
* For convenience, already loaded tracks are added to the database, and when loaded, the presence of `file_id` in the database is checked
* Search for and download audio from such services:
  + Deezer
  + YouTube Music
  + SoundCloud (`Standard load (30 sec).`)
* Search for Genius texts, send them to chat. 
* Track tag fix `using Spotify`. 
* Shazam function, send the bot a voice message or video (`no longer than 15 seconds`)
* Search for a clip on YT by query or to audio


## Existing commands
* `/start` - To start the bot, as well as to update the menu
* `/clip Request` - Search for a clip on YT, can be sent in response to an audio message
* `/lyric Request` - Search for Genius lyrics, can be sent in reply to an audio message
* Read Help in the main bot menu
* When sending audio to the bot, specify `/tag` or `/lyric` to perform this function


## More details

> I'm not claiming primacy. You are free to use this code. 
