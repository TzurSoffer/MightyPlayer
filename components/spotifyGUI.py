import customtkinter as ctk
import threading
import time

# from components.spotify import SpotifyPlayer  # Replace with your actual backend module
from spotify import SpotifyPlayer  # Replace with your actual backend module

class MiniSpotifyPlayer(ctk.CTkFrame):
    def __init__(self, master=None, backendUpdateInterval=2):
        super().__init__(master)
        
        self.backend = SpotifyPlayer(secretsFile="components/secrets.json")
        self.backend.startUpdateLoop(updateInterval=backendUpdateInterval)
        self.pack(padx=5, pady=5, fill="both", expand=True)

        self.playing = True
        self.lyrics_lines = []
        self.current_index = 0
        self.playlists = []

        self._setupUI()
        self._startUpdateLoop()

        self.bind("<Configure>", self._onResize)  # Add resize awareness

    def _onResize(self, event):
        width, height = event.width, event.height
        scale = min(width / 250, height / 250)

        font_size = int(12 * scale)
        highlight_size = int(14 * scale)
        progress_height = max(8, int(10 * scale))
        button_pad = int(4 * scale)

        for i, label in enumerate(self.lyrics_labels):
            if i == self.current_index:
                label.configure(font=("Arial", highlight_size, "bold"))
            else:
                label.configure(font=("Arial", font_size))

        self.progress.configure(height=progress_height)
        for btn in (self.prev_btn, self.play_button, self.next_btn):
            btn.configure(font=("Arial", font_size))
            btn.pack_configure(padx=button_pad, ipadx=button_pad)

    def _setupUI(self):
        self.rowconfigure(0, weight=8)  # lyrics + controls
        self.rowconfigure(1, weight=1)  # progress bar
        self.rowconfigure(2, weight=1)  # bottom bar
        self.columnconfigure(0, weight=1)

        # --- Top: stack lyrics + controls ---
        self.stack_container = ctk.CTkFrame(self)
        self.stack_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=2)

        self.stack_container.rowconfigure(0, weight=1)
        self.stack_container.columnconfigure(0, weight=1)

        self.lyrics_container = ctk.CTkFrame(self.stack_container)
        self.lyrics_container.grid(row=0, column=0, sticky="nsew")

        self.lyrics_scroll = ctk.CTkScrollableFrame(self.lyrics_container)
        self.lyrics_scroll.pack(fill="both", expand=True)

        self.lyrics_labels = []

        self.controls_frame = ctk.CTkFrame(
            self.stack_container, fg_color="transparent", bg_color="transparent"
        )
        self.controls_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.controls_frame.lift()

        self.prev_btn = ctk.CTkButton(self.controls_frame, text="⏮", command=self.backend.previous)
        self.play_button = ctk.CTkButton(self.controls_frame, text="⏸", command=self._togglePlay)
        self.next_btn = ctk.CTkButton(self.controls_frame, text="⏭", command=self.backend.next)

        for btn in (self.prev_btn, self.play_button, self.next_btn):
            btn.pack(side="left", padx=5, ipadx=2, expand=True, fill="x")

        self.lyrics_scroll.bind("<Enter>", lambda e: self._setControlsVisible(True))
        self.lyrics_scroll.bind("<Leave>", self._checkIfStillHovering)
        self.controls_frame.bind("<Enter>", lambda e: self._setControlsVisible(True))
        self.controls_frame.bind("<Leave>", self._checkIfStillHovering)

        self._setControlsVisible(False)

        # --- Middle: progress bar ---
        self.progress_var = ctk.DoubleVar()
        self.progress = ctk.CTkProgressBar(self, variable=self.progress_var, mode="determinate")
        self.progress.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        self.progress.bind("<Button-1>", self._onProgressClick)

        # --- Bottom: like and playlist ---
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        bottom_frame.columnconfigure((0, 1), weight=1)

        ctk.CTkButton(bottom_frame, text="❤️ Like", command=self.backend.likeCurrentSong).grid(
            row=0, column=0, padx=5, sticky="ew"
        )

        self.playlists = self.backend.getAvailablePlaylists()
        playlist_names = [pl["name"] for pl in self.playlists]
        self.playlist_dropdown = ctk.CTkOptionMenu(
            bottom_frame, values=playlist_names, command=self._addToSelectedPlaylist
        )
        self.playlist_dropdown.grid(row=0, column=1, padx=5, sticky="ew")

        # Lyrics setup (keep as-is)
        lyrics = self.backend.getLyrics().splitlines()
        for line in lyrics:
            label = ctk.CTkLabel(self.lyrics_scroll, text=line, anchor="center", font=("Arial", 16), justify="center")
            label.pack(fill="x", pady=1)
            self.lyrics_labels.append(label)

    def _togglePlay(self):
        self.backend.pausePlay()
        self.playing = not self.playing
        self.play_button.configure(text="⏸" if self.playing else "▶️")

    def _addToSelectedPlaylist(self, playlist_name):
        selected = next((pl for pl in self.playlists if pl["name"] == playlist_name), None)
        if selected:
            self.backend.addToPlaylist(selected["id"])

    def _startUpdateLoop(self):
        def loop():
            while True:
                time.sleep(1)
                self._updateLyricsContent()
                self._updateLyricsHighlight()
                self._updateProgress()

        threading.Thread(target=loop, daemon=True).start()

    def _updateLyricsContent(self):
        lyrics = self.backend.getLyrics().splitlines()
        if lyrics != [label.cget("text") for label in self.lyrics_labels]:
            for label in self.lyrics_labels:
                label.destroy()
            self.lyrics_labels.clear()
            for line in lyrics:
                label = ctk.CTkLabel(self.lyrics_scroll, text=line, anchor="center", font=("Arial", 16), justify="center")
                label.pack(fill="x", pady=2)
                self.lyrics_labels.append(label)

    def _updateLyricsHighlight(self):
        self.current_index = self.backend.getCurrentLyricIndex()
        for i, label in enumerate(self.lyrics_labels):
            if i == self.current_index:
                label.configure(font=("Arial", 18, "bold"))
            else:
                label.configure(font=("Arial", 16))

        if self.lyrics_labels:
            total_lines = len(self.lyrics_labels)
            if total_lines > 0:
                center_ratio = max(0, (self.current_index - 3) / max(1, total_lines))
                self.lyrics_scroll._parent_canvas.yview_moveto(center_ratio)

    def _updateProgress(self):
        progress = self.backend.getPlaybackProgressPercent()
        if 0 <= progress <= 1:
            self.progress_var.set(progress)

    def _onProgressClick(self, event):
        width = self.progress.winfo_width()
        clicked_ratio = event.x / width
        self.backend.seekToPercent(clicked_ratio)

    def _setControlsVisible(self, visible):
        if visible:
            self.controls_frame.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.controls_frame.place_forget()

    def _checkIfStillHovering(self, event=None):
        widget_under_mouse = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        if widget_under_mouse not in (self.lyrics_scroll, self.controls_frame):
            self._setControlsVisible(False)


# Standalone launcher
if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Mini Spotify Player")
    app.geometry("250x250")

    MiniSpotifyPlayer(master=app)
    app.mainloop()