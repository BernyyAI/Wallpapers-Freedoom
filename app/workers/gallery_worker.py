from PySide6.QtCore import QThread, Signal
from app.service.downloader import download_wallpaper_list

class GalleryWorker(QThread):
    finished = Signal(list)
    error = Signal(str)
    cancelled = Signal(list)  # Nueva señal para cancelación

    def __init__(self, query="wallpaper"):
        super().__init__()
        self.query = query
        self._is_cancelled = False

    def cancel(self):
        """Marcar el worker para cancelación"""
        self._is_cancelled = True

    def run(self):
        try:
            wallpapers = []
            # Pasar el worker para chequear cancelación
            wallpapers = download_wallpaper_list(query=self.query, worker=self)
            
            if self._is_cancelled:
                self.cancelled.emit(wallpapers)  # Emitir con lo descargado hasta ahora
            else:
                self.finished.emit(wallpapers)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))