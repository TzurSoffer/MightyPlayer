# 🎵 Mini Spotify Player

A lightweight, touch-friendly Spotify player built with Kivy that features:

*   Synchronized lyrics display
    
*   Animated player controls
    
*   Adding to any playlist
    
*   Liking songs
    
*   Progress tracking
    

Designed for minimal UI clutter and smooth user interaction.

- - -

## 📸 Features

*   ✅ Synchronized lyric lines with highlight
    
*   ✅ Play/Pause/Next/Previous controls
    
*   ✅ Add to any spotify playlist with dropdown
    
*   ✅ Like current track
    
*   ✅ Responsive hover effects
    
*   ✅ Custom styling via image folder
    

- - -

## 🚀 Getting Started

### 1\. **Clone the Repository**

`git clone https://github.com/TzurSoffer/MightyPlayer.git`

After the repository is cloned, cd into it

`cd MightyPlayer`

### 2\. **Install Dependencies**

`pip install -r requirements.txt`

### 3\. **Prepare Spotify Credentials**

To use Spotify’s API, you must register your app and obtain a **Client ID** and **Client Secret**.

#### Step-by-step:

1.  Visit the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
    
2.  Log in and click **"Create an App"**
    
3.  Enter a name and description.
    
4.  Once created, go to the app settings to get:
    
    *   `Client ID`
        
    *   `Client Secret`
        
5.  Add a redirect URI (e.g., `https://example.org/callback`) under "Edit Settings"

6. copy the Client Id and Client Secret and place them inside the `secrets.json` file.

7. If the redirect URI you chose for the spotify developer dashboard is not `https://example.org/callback`, make sure to change the `callbackUri` in the `secrets.json` file to the new URI.

- - -

- - -

## 🛠 Running the App

Make sure your terminal is in the project directory and run ```python main.py ```

- - -

## 🧠 How It Works

*   The app uses the [Spotipy](https://spotipy.readthedocs.io/) library to communicate with Spotify's API.
    
*   Lyrics are retrieved (via your SpotifyPlayer backend) and updated live using [syncedlyrics](https://github.com/moehmeni/syncedlyrics), ensuring the lyrics are displayed in sync with the song's progress.
    
*   Progress bar reflects the current position of the track.
    
*   The `secrets.json` file provides the Spotify OAuth2 credentials.

- - -

## 💡 Tips

*   You may need to authorize the app in your browser during the first run.
    
*   The `SpotifyPlayer` class should handle authentication and token refreshing.
    
*   Kivy's touch-optimized layout means this works great on Raspberry Pi or touchscreen devices too.
    

- - -

## 📜 License

MIT License — free for personal and commercial use.

- - -
