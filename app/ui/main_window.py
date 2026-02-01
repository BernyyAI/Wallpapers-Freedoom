from pathlib import Path
import json
import sys
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QMessageBox, QLabel,
    QGridLayout, QScrollArea, QSizePolicy, QHBoxLayout, QLineEdit,
    QGraphicsBlurEffect, QFrame, QDialog, QApplication
)
from PySide6.QtGui import QPixmap, QMovie
from PySide6.QtCore import Qt, QTimer
from app.service.downloader import download_random_wallpaper, download_wallpaper_list
from app.service.wallpapers import set_wallpaper
from app.workers.gallery_worker import GalleryWorker


def get_base_dir():
    """Ruta para archivos internos (assets incluidos en el .exe)"""
    if getattr(sys, 'frozen', False):
        
        return Path(sys._MEIPASS) / "app"
    else:
        
        return Path(__file__).resolve().parent.parent

def get_data_dir():
    """Ruta para archivos de usuario (favoritos, wallpapers descargados)"""
    if getattr(sys, 'frozen', False):
        
        appdata = Path(os.getenv('APPDATA'))
        data_dir = appdata / "Wallpaper Freedom"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    else:
        
        return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
DATA_DIR = get_data_dir()
FAVORITES_FILE = DATA_DIR / "favorites.json"


class PreviewDialog(QDialog):
    """Diálogo para mostrar vista previa del wallpaper"""
    
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista Previa")
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        image_label = QLabel()
        pixmap = QPixmap(str(image_path))
        
        screen = QApplication.primaryScreen().geometry()
        max_width = int(screen.width() * 0.8)
        max_height = int(screen.height() * 0.8)
        
        scaled_pixmap = pixmap.scaled(
            max_width, max_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(image_label)
        
        close_button = QPushButton("Cerrar")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: #eaeaea;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                border-color: #ff9800;
                background-color: #242424;
            }
        """)
        close_button.clicked.connect(self.accept)
        
        layout.addWidget(close_button, alignment=Qt.AlignCenter)
        
        self.resize(scaled_pixmap.width() + 40, scaled_pixmap.height() + 100)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
                color: #eaeaea;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #2a2a2a;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ff9800;
            }
        """)

        button_style = """
            QPushButton {
                background-color: #1e1e1e;
                color: #eaeaea;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                border-color: #ff9800;
                background-color: #242424;
            }
            QPushButton:pressed {
                background-color: #ff9800;
                color: #121212;
            }
            QPushButton:disabled {
                background-color: #181818;
                color: #666;
                border-color: #1f1f1f;
            }
        """

        search_style = """
            QLineEdit {
                background-color: #1e1e1e;
                color: #eaeaea;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #ff9800;
                background-color: #242424;
            }
            QLineEdit::placeholder {
                color: #666;
            }
        """

        self.setWindowTitle("Wallpaper Freedom")
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        central_widget.setStyleSheet("background: transparent;")
        
        self.favorites = self.load_favorites()

        buttons_layout = QHBoxLayout()
        self.apply_button = QPushButton("Aplicar Wallpaper")
        buttons_layout.addWidget(self.apply_button)
        layout.addLayout(buttons_layout)

        self.load_button = QPushButton("Cargar Galería")
        layout.addWidget(self.load_button)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar wallpapers (ej: nature, city, ocean)...")
        self.search_input.setStyleSheet(search_style)
        self.search_input.returnPressed.connect(self.search_wallpapers)
        
        self.search_button = QPushButton("Buscar")
        self.search_button.setStyleSheet(button_style)
        self.search_button.clicked.connect(self.search_wallpapers)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setStyleSheet(button_style)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.hide()
        
        search_layout.addWidget(self.search_input, stretch=4)
        search_layout.addWidget(self.search_button, stretch=1)
        search_layout.addWidget(self.cancel_button, stretch=1)
        layout.addLayout(search_layout)

        filter_layout = QHBoxLayout()
        self.show_all_button = QPushButton("Todos")
        self.show_all_button.setStyleSheet(button_style)
        self.show_all_button.clicked.connect(self.show_all_wallpapers)
        
        self.show_favorites_button = QPushButton("Favoritos")
        self.show_favorites_button.setStyleSheet(button_style)
        self.show_favorites_button.clicked.connect(self.show_favorites_only)
        
        filter_layout.addWidget(self.show_all_button)
        filter_layout.addWidget(self.show_favorites_button)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.selected_info = QLabel("Seleccionado: ninguno")
        self.selected_info.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.selected_info)

        self.delete_button = QPushButton("Eliminar Wallpaper")
        buttons_layout.addWidget(self.delete_button)
        self.delete_button.clicked.connect(self.delete_selected_wallpaper)

        for btn in (self.load_button, self.apply_button, self.delete_button):
            btn.setStyleSheet(button_style)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout()
        self.gallery_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.gallery_widget.setStyleSheet("background: transparent;")

        for i in range(3):
            self.gallery_layout.setColumnStretch(i, 1)

        self.gallery_widget.setLayout(self.gallery_layout)
        self.gallery_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.scroll_area.setWidget(self.gallery_widget)
        layout.addWidget(self.scroll_area, stretch=1)

        self.loader_label = QLabel(self.scroll_area.viewport())
        self.loader_label.setAlignment(Qt.AlignCenter)
        self.loader_movie = QMovie(str(BASE_DIR / "assets" / "ui" / "loading.gif"))
        self.loader_label.setMovie(self.loader_movie)
        self.loader_label.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        self.gallery_widget.setGraphicsEffect(None)
        self.loader_label.hide()

        self.selected_wallpaper = None
        self.selected_label = None
        self.worker = None
        self.current_filter = "all"
        self.selected_wallpapers = []
        self.selected_labels = []

        self.load_button.clicked.connect(self.load_gallery)
        self.apply_button.clicked.connect(self.apply_selected_wallpaper)
        self.load_gallery_from_disk()
        self.wallpaper_labels = []

        QTimer.singleShot(0, self.reflow_gallery)

    def load_favorites(self):
        if FAVORITES_FILE.exists():
            try:
                with open(FAVORITES_FILE, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_favorites(self):
        FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(list(self.favorites), f)

    def toggle_favorite(self, img_path: str, star_label: QLabel):
        if img_path in self.favorites:
            self.favorites.remove(img_path)
            star_label.setText("☆")
            star_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 24px;
                    background: transparent;
                }
                QLabel:hover {
                    color: #ff9800;
                }
            """)
        else:
            self.favorites.add(img_path)
            star_label.setText("☆")
            star_label.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-size: 24px;
                    background: transparent;
                }
                QLabel:hover {
                    color: #ffb84d;
                }
            """)
        self.save_favorites()

    def show_all_wallpapers(self):
        self.current_filter = "all"
        self.reload_gallery_view()

    def show_favorites_only(self):
        self.current_filter = "favorites"
        self.reload_gallery_view()

    def reload_gallery_view(self):
        self.selected_label = None
        self.selected_wallpaper = None
        self.selected_labels.clear()
        self.selected_wallpapers.clear()
        self.selected_info.setText("Seleccionado: ninguno")
        
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.load_gallery_from_disk()

    def search_wallpapers(self):
        query = self.search_input.text().strip()
        
        if not query:
            QMessageBox.warning(self, "Atención", "Ingresá un término de búsqueda")
            return
        
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        self.load_button.setEnabled(False)
        self.show_loader()

        self.worker = GalleryWorker(query=query)
        self.worker.finished.connect(self.on_gallery_loaded)
        self.worker.error.connect(self.on_gallery_error)
        self.worker.cancelled.connect(self.on_download_cancelled)
        self.worker.start()

        self.search_button.hide()
        self.cancel_button.show()

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)

    def on_download_cancelled(self, partial_wallpapers):
        self.hide_loader()
        
        for img_path, thumb_path in partial_wallpapers:
            try:
                if img_path.exists():
                    img_path.unlink()
                if thumb_path.exists():
                    thumb_path.unlink()
            except Exception:
                pass
        
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        self.load_button.setEnabled(True)
        self.cancel_button.hide()
        self.search_button.show()
        
        QMessageBox.information(
            self, "Descarga cancelada",
            f"Se canceló la descarga. Se eliminaron {len(partial_wallpapers)} archivos parciales."
        )

    def load_gallery_from_disk(self):
        wallpapers_dir = DATA_DIR / "wallpaperss"

        if not wallpapers_dir.exists():
            return

        columns = 3
        count = self.gallery_layout.count()
        row = count // columns
        col = count % columns

        for img_path in wallpapers_dir.glob("*.jpg"):
            if img_path.name.endswith("_thumb.jpg"):
                continue

            if self.current_filter == "favorites" and str(img_path) not in self.favorites:
                continue

            thumb_path = img_path.with_name(img_path.stem + "_thumb.jpg")
            if not thumb_path.exists():
                continue

            container = QWidget()
            container.setFixedSize(300, 200)
            container.setProperty("wallpaper_container", True)
            main_layout = QVBoxLayout(container)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(5)

            image_container = QWidget()
            image_container.setFixedSize(300, 170)

            label = QLabel(image_container)
            pixmap = QPixmap(str(thumb_path))

            label.setPixmap(pixmap.scaled(300, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.setFixedSize(300, 170)
            label.setAlignment(Qt.AlignCenter)
            label.setCursor(Qt.PointingHandCursor)
            label.setProperty("wallpaper_path", str(img_path))
            label.setProperty("main_container", container)
            label.mousePressEvent = lambda e, l=label: self.on_wallpaper_clicked(l, e)

            preview_btn = QPushButton("⛶", image_container)
            preview_btn.setFixedSize(35, 35)
            preview_btn.move(260, 130)
            preview_btn.setCursor(Qt.PointingHandCursor)
            preview_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(30, 30, 30, 200);
                    color: #ff9800;
                    border: 1px solid #2a2a2a;
                    border-radius: 6px;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:hover {
                    border-color: #ff9800;
                    background-color: rgba(36, 36, 36, 250);
                    color: #ffb84d;
                }
            """)
            preview_btn.clicked.connect(lambda checked, p=img_path: self.show_preview(p))

            star_label = QLabel("☆" if str(img_path) in self.favorites else "☆")
            star_label.setAlignment(Qt.AlignCenter)
            star_label.setCursor(Qt.PointingHandCursor)
            
            if str(img_path) in self.favorites:
                star_label.setStyleSheet("""
                    QLabel {
                        color: #ff9800;
                        font-size: 24px;
                        background: transparent;
                    }
                    QLabel:hover {
                        color: #ffb84d;
                    }
                """)
            else:
                star_label.setStyleSheet("""
                    QLabel {
                        color: #666;
                        font-size: 24px;
                        background: transparent;
                    }
                    QLabel:hover {
                        color: #ff9800;
                    }
                """)

            star_label.mousePressEvent = lambda e, p=str(img_path), s=star_label: self.toggle_favorite(p, s)

            main_layout.addWidget(image_container)
            main_layout.addWidget(star_label)
            self.gallery_layout.addWidget(container, row, col)

            col += 1
            if col >= columns:
                col = 0
                row += 1

        self.gallery_widget.adjustSize()

    def load_gallery(self):
        self.load_button.setEnabled(False)
        self.show_loader()
        self.loader_label.show()
        
        self.worker = GalleryWorker()
        self.worker.finished.connect(self.on_gallery_loaded)
        self.worker.error.connect(self.on_gallery_error)
        self.worker.cancelled.connect(self.on_download_cancelled)
        self.worker.start()

        self.search_button.hide()
        self.cancel_button.show()

    def on_gallery_loaded(self, wallpapers):
        self.hide_loader()

        for img_path, thumb_path in wallpapers:
            self.add_wallpaper(img_path, thumb_path)

        self.reflow_gallery()
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        self.cancel_button.hide()
        self.search_button.show()

    def add_wallpaper(self, img_path, thumb_path):
        container = QWidget()
        container.setFixedSize(300, 200)
        container.setProperty("wallpaper_container", True)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        image_container = QWidget()
        image_container.setFixedSize(300, 170)

        label = QLabel(image_container)
        pixmap = QPixmap(str(thumb_path))

        label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border-radius: 14px;
            }
        """)

        label.setPixmap(pixmap.scaled(300, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setFixedSize(300, 170)
        label.setAlignment(Qt.AlignCenter)
        label.setCursor(Qt.PointingHandCursor)
        label.setProperty("wallpaper_path", str(img_path))
        label.setProperty("main_container", container)
        label.mousePressEvent = lambda e, l=label: self.on_wallpaper_clicked(l, e)

        preview_btn = QPushButton("⛶", image_container)
        preview_btn.setFixedSize(35, 35)
        preview_btn.move(260, 130)
        preview_btn.setCursor(Qt.PointingHandCursor)
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 30, 200);
                color: #ff9800;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                border-color: #ff9800;
                background-color: rgba(36, 36, 36, 250);
                color: #ffb84d;
            }
        """)
        preview_btn.clicked.connect(lambda checked, p=img_path: self.show_preview(p))

        star_label = QLabel("☆" if str(img_path) in self.favorites else "☆")
        star_label.setAlignment(Qt.AlignCenter)
        star_label.setCursor(Qt.PointingHandCursor)
        
        if str(img_path) in self.favorites:
            star_label.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-size: 24px;
                    background: transparent;
                }
                QLabel:hover {
                    color: #ffb84d;
                }
            """)
        else:
            star_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 24px;
                    background: transparent;
                }
                QLabel:hover {
                    color: #ff9800;
                }
            """)

        star_label.mousePressEvent = lambda e, p=str(img_path), s=star_label: self.toggle_favorite(p, s)

        main_layout.addWidget(image_container)
        main_layout.addWidget(star_label)
        self.gallery_layout.addWidget(container)

    def on_gallery_error(self, message):
        self.hide_loader()
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)
        self.cancel_button.hide()
        self.search_button.show()
        QMessageBox.critical(self, "Error", message)

    def on_wallpaper_clicked(self, label: QLabel, event=None):
        path = label.property("wallpaper_path")
        if not path:
            return

        ctrl_pressed = False
        if event:
            ctrl_pressed = event.modifiers() & Qt.ControlModifier

        if ctrl_pressed:
            if label in self.selected_labels:
                label.setStyleSheet("")
                self.selected_labels.remove(label)
                if Path(path) in self.selected_wallpapers:
                    self.selected_wallpapers.remove(Path(path))
            else:
                label.setStyleSheet("border: 3px solid #FF8300; border-radius: 6px;")
                self.selected_labels.append(label)
                self.selected_wallpapers.append(Path(path))
            
            count = len(self.selected_wallpapers)
            if count == 0:
                self.selected_info.setText("Seleccionado: ninguno")
                self.selected_label = None
                self.selected_wallpaper = None
            elif count == 1:
                self.selected_info.setText(f"Seleccionado: {self.selected_wallpapers[0].name}")
                self.selected_label = self.selected_labels[0]
                self.selected_wallpaper = self.selected_wallpapers[0]
            else:
                self.selected_info.setText(f"Seleccionados: {count} wallpapers")
                self.selected_label = self.selected_labels[0]
                self.selected_wallpaper = self.selected_wallpapers[0]
        else:
            for lbl in self.selected_labels:
                try:
                    lbl.setStyleSheet("")
                except RuntimeError:
                    pass
            
            self.selected_labels.clear()
            self.selected_wallpapers.clear()

            label.setStyleSheet("border: 3px solid #FF8300; border-radius: 6px;")
            self.selected_label = label
            self.selected_wallpaper = Path(path)
            self.selected_labels.append(label)
            self.selected_wallpapers.append(Path(path))
            self.selected_info.setText(f"Seleccionado: {self.selected_wallpaper.name}")

    def apply_selected_wallpaper(self):
        if not self.selected_wallpaper:
            QMessageBox.warning(self, "Atención", "Seleccioná un wallpaper primero")
            return
        
        if len(self.selected_wallpapers) > 1:
            QMessageBox.warning(self, "Atención", "Solo podés aplicar un wallpaper a la vez. Deseleccioná los demás primero.")
            return

        try:
            set_wallpaper(self.selected_wallpaper)
            QMessageBox.information(self, "Wallpaper aplicado", "El fondo se aplicó correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected_wallpaper(self):
        if not self.selected_wallpapers:
            QMessageBox.warning(self, "Atención", "No hay ningún wallpaper seleccionado")
            return

        count = len(self.selected_wallpapers)
        
        if count == 1:
            message = f"¿Eliminar este wallpaper?\n\n{self.selected_wallpapers[0].name}"
        else:
            message = f"¿Eliminar {count} wallpapers seleccionados?"

        reply = QMessageBox.question(self, "Confirmar eliminación", message, QMessageBox.Yes | QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        try:
            for img_path in self.selected_wallpapers:
                thumb_path = img_path.with_name(img_path.stem + "_thumb.jpg")

                if img_path.exists():
                    img_path.unlink()

                if thumb_path.exists():
                    thumb_path.unlink()

                if str(img_path) in self.favorites:
                    self.favorites.remove(str(img_path))
            
            self.save_favorites()

            for label in self.selected_labels:
                try:
                    main_container = label.property("main_container")
                    if main_container:
                        self.gallery_layout.removeWidget(main_container)
                        main_container.deleteLater()
                except RuntimeError:
                    pass

            self.selected_labels.clear()
            self.selected_wallpapers.clear()
            self.selected_label = None
            self.selected_wallpaper = None
            self.selected_info.setText("Seleccionado: ninguno")

            self.reflow_gallery()

            if count == 1:
                QMessageBox.information(self, "Eliminado", "Wallpaper eliminado correctamente")
            else:
                QMessageBox.information(self, "Eliminados", f"{count} wallpapers eliminados correctamente")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def reflow_gallery(self):
        widgets = []

        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widgets.append(widget)

        if not widgets:
            return

        thumbnail_width = 300 
        available_width = self.scroll_area.viewport().width()
        columns = max(1, available_width // thumbnail_width)

        row = 0
        col = 0

        for widget in widgets:
            self.gallery_layout.addWidget(widget, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow_gallery()
        self.loader_label.resize(self.gallery_widget.size())
        self.loader_label.raise_()
        self.position_loader()
        
    def show_loader(self):
        blur = QGraphicsBlurEffect(self.gallery_widget)
        blur.setBlurRadius(12)

        self.gallery_widget.setGraphicsEffect(blur)
        self.loader_label.resize(self.gallery_widget.size())
        self.loader_label.raise_()
        self.position_loader()
        self.loader_label.show()
        self.loader_movie.start()
        self.load_button.setEnabled(False)

    def position_loader(self):
        viewport = self.scroll_area.viewport()
        self.loader_label.resize(viewport.size())
        self.loader_label.move(0, 0)
        self.loader_label.raise_()

    def hide_loader(self):
        self.loader_movie.stop()
        self.loader_label.hide()
        self.gallery_widget.setGraphicsEffect(None)
        self.load_button.setEnabled(True)
        self.scroll_area.setEnabled(True)

    def show_preview(self, image_path):
        dialog = PreviewDialog(image_path, self)
        dialog.exec()