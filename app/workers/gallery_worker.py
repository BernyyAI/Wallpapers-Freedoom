from PySide6.QtCore import QThread, Signal
from app.service.downloader import download_wallpaper_list

class GalleryWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, query="wallpaper"):
        super().__init__()
        self.query = query

    def run(self):
        try:
            wallpapers = download_wallpaper_list(query=self.query)
            self.finished.emit(wallpapers)
        except Exception as e:
            self.error.emit(str(e))