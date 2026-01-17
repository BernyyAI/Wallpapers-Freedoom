from PySide6.QtCore import QThread, Signal
from app.service.downloader import download_wallpaper_list

class GalleryWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            wallpapers = download_wallpaper_list()
            self.finished.emit(wallpapers)
        except Exception as e:
            self.error.emit(str(e))
