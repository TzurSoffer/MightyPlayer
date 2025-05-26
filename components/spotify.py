import json
import re
import pyautogui
import spotipy
import syncedlyrics
from spotipy.oauth2 import SpotifyOAuth

class Lyrics:
    def __init__(self, lyrics):
        self.synced = self._isSynced(lyrics)
        self.lyrics = self._convertToDict(lyrics.strip())

    def _isSynced(self, lyrics):
        """ Checks if the lyrics are synced. """
        timestampPattern = re.compile(r"\[\d{1,2}:\d{2}(?:\.\d{2})?\]")
        return(bool(timestampPattern.search(lyrics)))
    
    def _convertToDict(self, lyrics):
        if not self.synced:
            return({0.0: lyrics})

        lyricsDict = {}
        for line in lyrics.splitlines():
            timestamp, text = line[1:].split("]", 1)
            timestamp = self.lrcToInr(timestamp)
            lyricsDict[timestamp] = text.strip()
        return(lyricsDict)

    def lrcToInr(self, lrcTimestamp):
        """Converts LRC time format ([mm:ss.xx]) to total seconds."""
        lrcTimestamp = lrcTimestamp.strip("[]")  #< Remove brackets
        pattern = re.compile(r"(\d+):(\d+(?:\.\d+)?)")
        match = pattern.match(lrcTimestamp)

        if match:
            minutes, seconds = match.groups()
            minutes = int(minutes)
            seconds = float(seconds)

            totalTime = (minutes * 60) + seconds  #< Removed hours from calculation
            return(totalTime)                     #< Convert to integer if needed
        return(None)                              #< Invalid timestamp format

    def getLyricsFromTimeStamp(self, currentTime):
        timestamps = reversed(self.lyrics.keys())
        for timestamp in timestamps:
            if currentTime >= timestamp:
                return(self.lyrics[timestamp])
        return("")

    def __str__(self):
        return(self.lyrics)

    def __getitem__(self, currentTime):
        return(self.getLyricsFromTimeStamp(currentTime))

class Song:
    def __init__(self, sp:spotipy.Spotify):
        self.sp = sp
        self.songName = None
        self.artistName = None
        self.albumName = None
        self.progress = None
        self.duration = None
        self.lyrics = None

    def updateSongInfo(self):
        current = self.sp.current_playback()

        if current and current["is_playing"]:
            track = current["item"]

            songName = track["name"]
            self.artistsName = [artist["name"] for artist in track["artists"]]
            self.artistName = self.artistsName[0] if self.artistsName else "Unknown Artist"
            self.albumName = track["album"]["name"]
            self.progress = current["progress_ms"]*0.001  #< Convert ms to seconds
            self.duration = track["duration_ms"]*0.001    #< Convert ms to seconds
            if songName != self.songName and type(songName) == str:
                self.songName = songName
                self.lyrics = self._findLyrics()
            return(True)

        print("No track is currently playing.")
        return(False)

    def _findLyrics(self):
        return(Lyrics(syncedlyrics.search("{} - {}".format(self.songName, self.artistName))))
    
    def getCurrentLyric(self):
        if self.lyrics:
            return(self.lyrics.getLyricsFromTimeStamp(self.progress))
        return("No lyrics available for this song :(")

class SpotifyPlayer:
    def __init__(self, secretsFile="secrets.json"):
        with open(secretsFile, "r") as f:
            secrets = json.load(f)
            self.clientID = secrets["spotify"]["clientId"]
            self.clientSecret = secrets["spotify"]["clientSecret"]
            self.callbackUri = secrets["spotify"]["callbackUri"]

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self.clientID,
            client_secret=self.clientSecret,
            redirect_uri=self.callbackUri,
            scope="user-read-playback-state user-modify-playback-state"
        ))

        self.song = Song(self.sp)
    
    def _isAuthenticated(self):
        if not self.sp.current_user():
            return False
        return True
    
    def _updateSongInfo(self):
        """
        Retrieves the currently playing song from Spotify.
        """
        if not self._isAuthenticated():
            print("Not authenticated with Spotify.")
            return None
        ret = self.song.updateSongInfo()
        if ret:
            return({
                "name": self.song.songName,
                "artists": self.song.artistsName,
                "album": self.song.albumName,
                "progress": self.song.progress,
                "duration": self.song.duration,
                "lyrics": self.song.lyrics
            })

    def _pausePlay(self):
        """Pauses/Plays playback on the user"s active device."""
        pyautogui.press("playpause")

    def skip(self):
        """Skips to the next track on the user"s active device."""
        pyautogui.press("nexttrack")

    def previous(self):
        """Goes back to the previous track on the user"s active device."""
        pyautogui.press("prevtrack")
    
    def pause(self):
        """Pauses playback on the user"s active device."""
        if self._getCurrentSongInfo() == None:
            return()
        self._pausePlay()

    def play(self):
        """Plays playback on the user"s active device."""
        if self._getCurrentSongInfo() == None:
            self._pausePlay()
        return()
    
    def currentLyric(self):
        """Returns the currently playing song lyrics."""
        return(self.song.getCurrentLyric())

if __name__ == "__main__":
    import time
    player = SpotifyPlayer(secretsFile="components/secrets.json")
    
    currentSong = player._updateSongInfo()
    shownLyrics = ""
    while currentSong["lyrics"] != None:
        currentSong = player._updateSongInfo()
        currentLyrics = player.currentLyric()
        if currentLyrics != shownLyrics:
            shownLyrics = currentLyrics
            print(shownLyrics)

        time.sleep(1)
        # print(f"Currently playing: {currentSong["name"]} by {", ".join(currentSong["artists"])} "
        #       f"with progress {currentSong["progress_ms"]} ms out of {currentSong["duration_ms"]} ms.")
    else:
        print("No song is currently playing.")

