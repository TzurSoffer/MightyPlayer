import time
import json
import threading
import re
import pyautogui
import syncedlyrics
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def retryOnTimeout(func, retries=-1, backoff=2, *args, **kwargs):
    attempt = 1
    while True:
        try:
            return(func(*args, **kwargs))
        except Exception as e:
            print(f"Attempt {attempt} failed with error: {e}")
            if attempt != retries:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise  #< Let the last exception propagate
        attempt += 1

class Lyrics:
    def __init__(self, lyrics):
        self.synced = self._isSynced(lyrics)
        self.lyrics = self._convertToDict(lyrics)

    def _isSynced(self, lyrics) -> bool:
        """ Checks if the lyrics are synced. """
        if lyrics == None:
            return(False)
        timestampPattern = re.compile(r"\[\d{1,2}:\d{2}(?:\.\d{2})?\]")
        return(bool(timestampPattern.search(lyrics)))
    
    def isSynced(self) -> bool:
        """ Returns True if the lyrics are synced, False otherwise. """
        return(self.synced)
    
    def _convertToDict(self, lyrics) -> dict:
        if lyrics == None:
            return({0.0: "No lyrics available, you will have to guess for this one :("})

        if not self.synced:
            return({0.0: lyrics})

        lyricsDict = {0.0: ""}                        #< Initialize with a default entry for 0 seconds
        for line in lyrics.strip().splitlines():
            timestamp, text = line[1:].split("]", 1)
            timestamp = self.lrcToInr(timestamp)
            lyricsDict[timestamp] = text.strip()
        return(lyricsDict)

    def lrcToInr(self, lrcTimestamp) -> float:
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

    def getNearestTimestamp(self, currentTime) -> float:
        timestamps = reversed(self.lyrics.keys())
        for timestamp in timestamps:
            if currentTime >= timestamp:
                return(timestamp)
        return(0.0)

    def getLyricsFromTimeStamp(self, currentTime) -> str:
        return(self.lyrics[self.getNearestTimestamp(currentTime)])
    
    def getLyrics(self) -> str:
        """Returns the lyrics as a string."""
        if not self.synced:
            return(self.lyrics[0.0])
        
        lyrics = ""
        for text in self.lyrics.values():
            lyrics += f"{text}\n"
        return(lyrics)

    def __str__(self):
        return(self.getLyrics())

    def __getitem__(self, currentTime):
        return(self.getLyricsFromTimeStamp(currentTime))

class Song:
    def __init__(self, sp:spotipy.Spotify):
        self.sp = sp
        self.songName = None
        self.artistName = None
        self.albumName = None
        self.isPlaying = False
        self.progress = 0.0
        self.duration = None
        self.lyrics = None

    def updateSongInfo(self) -> bool:
        current = retryOnTimeout(self.sp.current_playback)
        if current == None or current.get("item") == None:
            return(False)

        track = current["item"]
        songName = track["name"]
        self.artistsName = [artist["name"] for artist in track["artists"]]
        self.artistName = self.artistsName[0] if self.artistsName else "Unknown Artist"
        self.albumName = track["album"]["name"]
        self.isPlaying = current.get("is_playing", False)
        self.progress = current["progress_ms"]*0.001  #< Convert ms to seconds
        self.duration = track["duration_ms"]*0.001    #< Convert ms to seconds
        if songName != self.songName and type(songName) == str:
            self.songName = songName
            self.lyrics = self._findLyrics()
        return(True)

    def _findLyrics(self) -> Lyrics:
        return(Lyrics(syncedlyrics.search("{} - {}".format(self.songName, self.artistName))))

    def getCurrentLyric(self) -> str:
        if self.lyrics:
            return(self.lyrics.getLyricsFromTimeStamp(self.progress))
        return("No lyrics available for this song :(")
    
    def getCurrentLyricTimestamp(self, at=None) -> float:
        if self.lyrics:
            if at == None:
                at = self.progress
            return(self.lyrics.getNearestTimestamp(at))
        return(0.0)
    
    def like(self) -> bool:
        """
        Likes the current song
        """
        current = self.sp.current_playback()
        if current and current["item"]:
            track_id = current["item"]["id"]
            self.sp.current_user_saved_tracks_add([track_id])
            print(f"Liked song: {current['item']['name']} by {', '.join(artist['name'] for artist in current['item']['artists'])}")
            return(True)
        else:
            print("No song is currently playing.")
            return(False)
    
    def addToPlaylist(self, playlistId) -> bool:
        """
        Adds the current song to the specified playlist.
        """
        current = self.sp.current_playback()
        if current and current["item"]:
            track_id = current["item"]["id"]
            self.sp.playlist_add_items(playlistId, [track_id])
            print(f"Added song: {current['item']['name']} by {', '.join(artist['name'] for artist in current['item']['artists'])} to playlist {playlistId}.")
            return(True)
        else:
            print("No song is currently playing.")
            return(False)

class SpotifyPlayer:
    def __init__(self, secretsFile="secrets.json"):
        with open(secretsFile, "r") as f:
            secrets = json.load(f)
            self.clientID = secrets["spotify"]["clientId"]
            self.clientSecret = secrets["spotify"]["clientSecret"]
            self.callbackUri = secrets["spotify"]["callbackUri"]

        self.sp = self._createSpotifyObject()
        if not self._isAuthenticated():
            print("Authentication failed. Please check your credentials.")
            return

        self.song = Song(self.sp)
    
    def _createSpotifyObject(self) -> spotipy.Spotify:
        """
        Creates a Spotify object with the current authentication.
        """
        return(spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self.clientID,
            client_secret=self.clientSecret,
            redirect_uri=self.callbackUri,
            scope="user-read-playback-state user-modify-playback-state user-library-modify playlist-modify-public playlist-modify-private"
        )))

    def _isAuthenticated(self) -> bool:
        if not retryOnTimeout(self.sp.current_user):
            return(False)
        return(True)
    
    def _updateSongInfo(self) -> None:
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

    def next(self) -> None:
        """Skips to the next track on the user"s active device."""
        pyautogui.press("nexttrack")

    def previous(self) -> None:
        """Goes back to the previous track on the user"s active device."""
        pyautogui.press("prevtrack")

    def pausePlay(self) -> None:
        """Pauses/Plays playback on the user"s active device."""
        pyautogui.press("playpause")

    def pause(self) -> None:
        """Pauses playback on the user"s active device."""
        if self._getCurrentSongInfo() == None:
            return()
        self.pausePlay()

    def play(self) -> None:
        """Plays playback on the user"s active device."""
        if self._getCurrentSongInfo() == None:
            self.pausePlay()

    def getLyrics(self) -> Lyrics:
        """Returns the lyrics object of the currently playing song."""
        return(self.song.lyrics.getLyrics() if self.song.lyrics else "No lyrics available for this song :(")

    def getCurrentLyrics(self) -> str:
        """Returns the currently playing song lyrics."""
        return(self.song.getCurrentLyric())

    def getCurrentLyricIndex(self, timestamp=None, at=None) -> int:
        if self.song.lyrics:
            if timestamp == None:
                timestamp = self.song.getCurrentLyricTimestamp(at=at)
            index = list(self.song.lyrics.lyrics.keys()).index(timestamp)
            return(index)
        return(-1)
    
    def isSynced(self) -> bool:
        """Returns True if the lyrics are synced, False otherwise."""
        if self.song.lyrics == None:
            return(False)
        return(self.song.lyrics.isSynced())
    
    def likeCurrentSong(self) -> bool:
        """Likes the currently playing song on the user"s active device."""
        return(self.song.like())
    
    def getCurrentTime(self) -> float:
        """Returns the current playback time of the currently playing song in seconds."""
        return(self.song.progress)
    
    def getAvailablePlaylists(self) -> list:
        """Returns a list of available playlists for the user."""
        playlists = self.sp.current_user_playlists()
        return([{"id": pl["id"], "name": pl["name"]} for pl in playlists["items"]])

    def addToPlaylist(self, playlistId) -> bool:
        """Adds the currently playing song to the specified playlist."""
        return(self.song.addToPlaylist(playlistId))
    
    def getSongDuration(self) -> float:
        """Returns the duration of the currently playing song in seconds."""
        return(self.song.duration)
    
    def getPlaybackProgressPercent(self) -> float:
        """Returns the playback progress of the currently playing song in seconds."""
        return(self.song.progress/self.song.duration if self.song.duration else 0.0)

    def isPlaying(self) -> bool:
        """
        Returns True if a song is currently playing, False otherwise.
        """
        return(self.song.isPlaying)

    def seekTo(self, seconds) -> None:
        """
        Seeks to the specified time in seconds in the currently playing song.
        """
        try:
            if self._isAuthenticated():
                self.sp.seek_track(int(seconds * 1000))
        except:   #< If not premium user, this will fail
            print("Seeking is not supported for non-premium users or if the song is not playing.")
            pass

    def seekToPercent(self, percent) -> None:
        """
        Seeks to the specified percentage of the currently playing song.
        """
        if self._isAuthenticated() and self.song.duration is not None:
            seconds = self.song.duration * percent
            self.seekTo(seconds)

    def startUpdateLoop(self, updateInterval=1, callback=None) -> None:
        """
        Starts a loop that updates the song info and lyrics at the specified interval.
        """
        def loop():
            while True:
                time.sleep(updateInterval)
                self._updateSongInfo()
                if callable(callback):
                    callback(self.song)
        
        threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    import time
    player = SpotifyPlayer(secretsFile="components/secrets.json")
    
    currentSong = player._updateSongInfo()
    shownLyrics = ""
    while currentSong and currentSong["lyrics"] != None:
        currentSong = player._updateSongInfo()
        currentLyrics = player.getCurrentLyrics()
        if currentLyrics != shownLyrics:
            shownLyrics = currentLyrics
            print(shownLyrics)

        time.sleep(1)
        # print(f"Currently playing: {currentSong["name"]} by {", ".join(currentSong["artists"])} "
        #       f"with progress {currentSong["progress_ms"]} ms out of {currentSong["duration_ms"]} ms.")
    else:
        print("No song is currently playing.")

