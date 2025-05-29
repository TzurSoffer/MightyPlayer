import copy
import os
os.environ["KIVY_NO_CONSOLELOG"] = "1"
import threading
import time

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import BooleanProperty, NumericProperty, ListProperty
from kivy.animation import Animation

from spotify import SpotifyPlayer

def calcFontSize(text, width, maxSize, multiplier=2):
    """Calculate a responsive font size based on text length and available width."""
    if not text:
        return(maxSize)
    return(min(maxSize, width/len(text)*multiplier))

class HoverBehavior(object):
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return

        pos = args[1]
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered == inside:
            return
        self.hovered = inside
        if inside:
            self.on_hover()
        else:
            self.on_unhover()

    def on_hover(self):
        pass

    def on_unhover(self):
        pass

class ImageButton(ButtonBehavior, Image, HoverBehavior):
    def on_hover(self):
        Animation.cancel_all(self)
        anim = Animation(scale=1.2, duration=0.2)
        anim.start(self)

    def on_unhover(self):
        Animation.cancel_all(self)
        anim = Animation(scale=1.0, duration=0.2)
        anim.start(self)

    scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(scale=self.update_scale)

    def update_scale(self, instance, value):
        # update size based on scale and texture size
        if self.texture_size != (0, 0):
            base_w, base_h = self.texture_size
            self.size = (base_w * value, base_h * value)

class DropdownOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0.6, 0.6, 0.6, .8)            #< Dark gray
        self.color = (1, 1, 1, 1)                              #< White
        self.font_size = calcFontSize(self.text, self.width, 18)  #< Responsive font size
        self.size_hint_y = None
        self.height = 50

class Timer:
    def __init__(self):
        self.timeNow = time.time()
        self.time = 0
    
    def setTime(self, setTime):
        self.time = setTime
        self.timeNow = time.time()
    
    def getTime(self):
        return(self.time + (time.time() - self.timeNow))

    def __repr__(self):
        return(self.getTime())

class MiniSpotifyPlayer(BoxLayout):
    progress = NumericProperty(0)
    lyrics_lines = ListProperty([])
    playing = BooleanProperty(True)

    def __init__(self, imageFolder="./images/", secretsFile="secrets.json", **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.imageFolder = imageFolder
        self.backend = SpotifyPlayer(secretsFile=secretsFile)
        self.backend.startUpdateLoop(updateInterval=2, callback=self._update)

        self.current_index = 0
        self.time = Timer()
        self.playlists = self.backend.getAvailablePlaylists()

        self._setup_ui()
        self._start_update_loop()

    def _setup_ui(self):
        # Root is FloatLayout to allow floating widgets (like centered controls)
        self.root_layout = FloatLayout()
        self.add_widget(self.root_layout)

        # Dark background
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0.12, 0.12, 0.12, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg_rect, size=self._update_bg_rect)

        # Lyrics scroll view (placed inside root layout, fills most of screen)
        self.lyrics_box = BoxLayout(orientation='vertical', size_hint_y=None, padding=10)
        self.lyrics_box.bind(minimum_height=self.lyrics_box.setter('height'))

        self.scroll = ScrollView(size_hint=(1, 0.9), pos_hint={'x': 0, 'y': 0.1})
        self.scroll.add_widget(self.lyrics_box)
        self.root_layout.add_widget(self.scroll)

        # Centered controls container — transparent and floating
        self.controls_container = BoxLayout(size_hint=(None, None), spacing=30)
        self.controls_container.size = (60*3 + 30*2, 60)
        self.controls_container.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.controls_container.opacity = 0  # start hidden
        self.controls_container.hovered = False

        btn_size = (60, 60)
        self.prev_btn = ImageButton(source=os.path.join(self.imageFolder, "previous.png"),
                                    size_hint=(None, None), size=btn_size)
        self.prev_btn.bind(on_press=lambda x: self.backend.previous())

        self.play_btn = ImageButton(source=os.path.join(self.imageFolder, "pause.png"),
                                    size_hint=(None, None), size=btn_size)
        self.play_btn.bind(on_press=self._toggle_play)

        self.next_btn = ImageButton(source=os.path.join(self.imageFolder, "next.png"),
                                    size_hint=(None, None), size=btn_size)
        self.next_btn.bind(on_press=lambda x: self.backend.next())

        self.controls_container.add_widget(self.prev_btn)
        self.controls_container.add_widget(self.play_btn)
        self.controls_container.add_widget(self.next_btn)

        self.root_layout.add_widget(self.controls_container)

        # Bottom bar (like + playlist) — now floating at the bottom
        self.bottom_bar = BoxLayout(orientation='horizontal', size_hint=(1, None),
                                    height=80, padding=10, spacing=20,
                                    pos_hint={'x': 0, 'y': 0.05})
        self.root_layout.add_widget(self.bottom_bar)

        # Like button
        like_img_path = os.path.join(self.imageFolder, "heart.png")
        self.like_btn = ImageButton(source=like_img_path, size_hint=(None, None), size=(60, 60))
        self.like_btn.bind(on_press=lambda x: self.backend.likeCurrentSong())
        
        self.bottom_bar.add_widget(BoxLayout())  # Spacer
        self.bottom_bar.add_widget(self.like_btn)


        # Playlist spinner
        playlist_names = [pl["name"] for pl in self.playlists]
        # self.playlist_spinner = ModernSpinner(text="Add To Playlist" if playlist_names else '',
        self.playlist_spinner = Spinner(text="Add To Playlist" if playlist_names else '',
                                        values=playlist_names,
                                        size_hint=(None, None),
                                        size=(120, 60),
                                        color=(0.9, 0.9, 0.9, 1),
                                        background_color=(0.2, 0.2, 0.2, 1),
                                        option_cls=DropdownOption)
        self.playlist_spinner.bind(text=self._add_to_selected_playlist)
        self.bottom_bar.add_widget(self.playlist_spinner)

        # Progress bar (still pinned to bottom of root layout)
        self.progress_bar = ProgressBar(size_hint=(1, None), height=15, pos_hint={'x': 0, 'y': 0})
        self.progress_bar.max = 1
        self.progress_bar.bind(on_touch_down=self._on_progress_touch)
        self.root_layout.add_widget(self.progress_bar)

        # Hover logic for center controls only
        def on_mouse_pos(window, pos):
            # Get position and size of the controls container
            x, y = self.controls_container.to_window(*self.controls_container.pos)
            width, height = self.controls_container.size

            # Add margin around the controls (e.g., 30px above and below)
            margin_vertical = 80
            margin_horizontal = 50  # optional

            in_x = x - margin_horizontal <= pos[0] <= x + width + margin_horizontal
            in_y = y - margin_vertical <= pos[1] <= y + height + margin_vertical

            if in_x and in_y:
                self._show_controls()
            else:
                self._hide_controls()

        Window.bind(mouse_pos=on_mouse_pos)

        self._update_lyrics()

    def _show_controls(self):
        if self.controls_container.opacity == 0:
            Animation.cancel_all(self.controls_container)
            Animation(opacity=1, d=0.25).start(self.controls_container)

    def _hide_controls(self):
        if self.controls_container.opacity == 1:
            Animation.cancel_all(self.controls_container)
            Animation(opacity=0, d=0.25).start(self.controls_container)

    def _update_bg_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _toggle_play(self, *args):
        self.backend.pausePlay()
        self.playing = not self.playing
        self.play_btn.source = os.path.join(self.imageFolder, "pause.png") if self.playing else os.path.join(self.imageFolder, "play.png")

    def _add_to_selected_playlist(self, spinner, playlist_name):
        selected = next((pl for pl in self.playlists if pl["name"] == playlist_name), None)
        if selected:
            self.backend.addToPlaylist(selected["id"])

    def _start_update_loop(self):
        def loop():
            while True:
                time.sleep(0.1)
                Clock.schedule_once(lambda dt: self._update_lyrics())
                Clock.schedule_once(lambda dt: self._update_progress())

        threading.Thread(target=loop, daemon=True).start()
    
    def _update(self, *args):
        self.time.setTime(self.backend.getCurrentTime())
        Clock.schedule_once(lambda dt: self._update_lyrics())
        Clock.schedule_once(lambda dt: self._update_progress())
        Clock.schedule_once(lambda dt: self._updatePlayPauseButton())
    
    def _update_lyrics(self, *args):
        lyrics = self.backend.getLyrics().splitlines()
        if lyrics != [lbl.text for lbl in self.lyrics_box.children[::-1]]:
            self.lyrics_box.clear_widgets()
            for line in lyrics:
                lbl = Label(
                    text=line,
                    halign='center',
                    markup=True,
                    size_hint_y=None,
                    height=40,
                    font_size=calcFontSize(line, self.width, 24),
                    color=(0.9, 0.9, 0.9, 1)
                )
                lbl.bind(size=lambda inst, val: inst.setter('text_size')(inst, (inst.width, None)))
                self.lyrics_box.add_widget(lbl)
            self.lyrics_lines = self.lyrics_box.children[::-1]
            if self.backend.isSynced():
                self._update_lyrics_highlight()

    def _update_lyrics_highlight(self, *args):
        self.current_index = self.backend.getCurrentLyricIndex(at=self.time.getTime())
        lyrics_lines_text = self.backend.getLyrics().splitlines()
        for i, lbl in enumerate(self.lyrics_lines):
            line = lyrics_lines_text[i]
            if i == self.current_index:
                lbl.text = f"[b][color=3399FFFF]{line}[/color][/b]"
                lbl.font_size=calcFontSize(line, self.width, 30)
            else:
                lbl.text = line
                lbl.font_size=calcFontSize(line, self.width, 24)

        # Delay the scroll adjustment to next frame so layout has been updated
        Clock.schedule_once(self._center_current_line, 0)

    def _center_current_line(self, dt):
        if not self.lyrics_lines or self.current_index >= len(self.lyrics_lines):
            return

        line_height = self.lyrics_lines[0].height if self.lyrics_lines else 40
        index = self.current_index
        content_height = self.lyrics_box.height
        viewport_height = self.scroll.height

        offset_from_bottom = line_height * index + line_height / 2
        desired_scroll_pos = offset_from_bottom - viewport_height / 2

        max_scroll = content_height - viewport_height
        if max_scroll < 1:
            max_scroll = 1

        scroll_y = desired_scroll_pos / max_scroll
        scroll_y = max(0, min(scroll_y, 1))

        self.scroll.scroll_y = 1 - scroll_y

    def _update_progress(self, *args):
        if not self.backend.getSongDuration():
            progress = 0.0
        else:
            progress = min(1, self.time.getTime()/self.backend.getSongDuration())
        self.progress = progress
        self.progress_bar.value = progress

    def _on_progress_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            width = instance.width
            clicked_ratio = touch.x / width
            self.backend.seekToPercent(clicked_ratio)

    def _updatePlayPauseButton(self, *args):
        if self.backend.isPlaying():
            self.play_btn.source = os.path.join(self.imageFolder, "pause.png")
        else:
            self.play_btn.source = os.path.join(self.imageFolder, "play.png")


class MiniSpotifyApp(App):
    def __init__(self, size=(300,300), imageFolder="./images/", secretsFile="secrets.json", **kwargs):
        Window.size = size
        super().__init__(**kwargs)
        self.imageFolder = imageFolder
        self.secretsFile = secretsFile

    def build(self):
        self.title = "Mini Spotify Player"
        return(MiniSpotifyPlayer(imageFolder=self.imageFolder, secretsFile=self.secretsFile))


if __name__ == "__main__":
    MiniSpotifyApp(secretsFile="mySecrets.json").run()
