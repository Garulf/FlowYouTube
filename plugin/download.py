from tkinter import ttk
import sys
import tkinter as tk
from tkinter.messagebox import showinfo
import sys
import time
import os
from pathlib import Path
from threading import Thread
import argparse

# Embedded Python does not import modules from the plugin's lib directory
parser = argparse.ArgumentParser()
parser.add_argument("url", help="The url of the video to download")
parser.add_argument("itag", help="The itag of the video to download")
parser.add_argument("lib", help="The path to the plugin's lib directory")
args = parser.parse_args()
sys.path.append(args.lib)

from pytube import YouTube
from find_desktop import get_desktop


WIDTH = 400
HEIGHT = 150
WINDOW_SIZE = f"{WIDTH}x{HEIGHT}"
WINDOW_TITLE = "FlowYouTube Video Download"
ICON = "icon.png"


def convert_to_percent(value, total):
    return (value / total) * 100

def convert_to_mb(value):
    return value / 1024 / 1024

def remove_temp_files(file_path):
    for x in range(5):
        try:
            os.remove(file_path)
            break
        except PermissionError:
            time.sleep(1)

class DownloadProgressBar(ttk.Progressbar):

    PACK = {"side": "top", "fill": "both", "expand": True}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack(**self.PACK)

    def update(self, percent):
        self["value"] = percent
        super().update()

class DownloadProgressCancelButton(tk.Button):

    DEFAULT_LABEL = "Cancel"
    PACK = {"side": "bottom", "fill": "both", "expand": True}

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.pack(**self.PACK)
        self["text"] = self.DEFAULT_LABEL
        self["command"] = master.destroy

class DownloadProgressRateLabel(tk.Label):

    DEFAULT_TEXT = "Transfer Rate: {} MB/s"
    PACK = {"side": "bottom", "fill": "both", "expand": True}

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self["text"] = self.DEFAULT_TEXT.format(0)
        self.pack(**self.PACK)

    def update(self, rate):
        self["text"] = self.DEFAULT_TEXT.format(rate)

class DownloadDescriptionLabel(tk.Label):

    DEFAULT_TEXT = "Loading..."
    TEXT_FMT = "Downloading: {}"
    PACK = {"side": "bottom", "fill": "x", "expand": True}

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self["text"] = self.DEFAULT_TEXT
        self.bind("<Configure>", lambda e: self.configure(wraplength=self.winfo_width()))
        self.pack(**self.PACK)

    def update(self, video_title):
        self["text"] = self.TEXT_FMT.format(video_title)

class DownloadProgressETA(tk.Label):
    TEXT_FMT = "{} of {:.2f} MB ({:.2f}%)"
    DEFAULT_TEXT = TEXT_FMT.format(0, 0, 0)

    PACK = {"side": "bottom", "fill": "both", "expand": True}

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self["text"] = self.DEFAULT_TEXT
        self.pack(**self.PACK)

    def update(self, bytes_downloaded, total_size, percent):
        self["text"] = self.TEXT_FMT.format(convert_to_mb(bytes_downloaded), convert_to_mb(total_size), percent)

class DownloadProgressWindow(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconphoto(False, tk.PhotoImage(file=ICON))
        self.title(WINDOW_TITLE)
        self._download_complete = False
        self.geometry(WINDOW_SIZE)
        self.resizable(0, 0)
        self.eval(f'tk::PlaceWindow {self.winfo_toplevel()} center')
        self.create_widgets()
        self.update_idletasks()
        self.bind('<Escape>', lambda e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def create_widgets(self):
        self.progress_bar = DownloadProgressBar(self, orient="horizontal", length=WIDTH - 20, mode="determinate")
        self.cancel_button = DownloadProgressCancelButton(self)
        self.rate = DownloadProgressRateLabel(self)
        self.eta = DownloadProgressETA(self)
        self.label = DownloadDescriptionLabel(self)

    def destroy(self):
        super().destroy()
 
    def download(self):
        self.download_thread = Thread(target=self._download, daemon=True)
        self.download_thread.start()

    def _download(self):
        yt = YouTube(self.url)
        yt.register_on_progress_callback(self.update_progress)
        yt.register_on_complete_callback(self.download_complete)
        self.video = yt.streams.get_by_itag(self.itag)
        self.label.update(self.video.title)
        self.start = time.time()
        self.video.download(output_path=get_desktop(), skip_existing=False)

    def download_complete(self, stream_object, file_path):
        self._download_complete = True
        showinfo("Download Complete", f"File was downloaded to {file_path}")
        self.destroy()

    def update_progress(self, stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percent = convert_to_percent(bytes_downloaded, total_size)
        self.progress_bar.update(percent)
        self.eta.update(bytes_downloaded, total_size, percent)
        self.rate.update(convert_to_mb(bytes_downloaded))

    def start(self, url, itag):
        self.url = url
        self.itag = itag
        self.download()
        self.mainloop()

if __name__ == "__main__":
    download_progress_win = DownloadProgressWindow()
    download_progress_win.start(args.url, args.itag)
