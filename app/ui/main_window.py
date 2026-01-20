from pathlib import Path
import json

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QMessageBox, QLabel,
    QGridLayout, QScrollArea, QSizePolicy, QHBoxLayout, QLineEdit,
    QGraphicsBlurEffect, QFrame
)
from PySide6.QtGui import QPixmap, QMovie
from PySide6.QtCore import Qt, QTimer

from app.service.downloader import download_random_wallpaper, download_wallpaper_list
from app.service.wallpapers import set_wallpaper
from app.workers.gallery_worker import GalleryWorker




BASE_DIR = Path(__file__).resolve().parent.parent
FAVORITES_FILE = BASE_DIR / "assets" / "favorites.json"


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
        
        search_layout.addWidget(self.search_input, stretch=4)
        search_layout.addWidget(self.search_button, stretch=1)
        
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

        for btn in (
            self.load_button,
            self.apply_button,
            self.delete_button
        ):
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
        self.gallery_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )


        self.scroll_area.setWidget(self.gallery_widget)

        
        layout.addWidget(self.scroll_area, stretch=1)

        self.loader_label = QLabel(self.scroll_area.viewport())

        self.loader_label.setAlignment(Qt.AlignCenter)

        self.loader_movie = QMovie(
            str(BASE_DIR / "assets" / "ui" / "loading.gif")
        )
        self.loader_label.setMovie(self.loader_movie)

        self.loader_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 120);
        """)
        
        self.gallery_widget.setGraphicsEffect(None)
        self.loader_label.hide()

        self.selected_wallpaper = None
        self.selected_label = None
        self.worker = None
        self.current_filter = "all"  

        
        self.load_button.clicked.connect(self.load_gallery)
        self.apply_button.clicked.connect(self.apply_selected_wallpaper)
        
        
        self.load_gallery_from_disk()
        self.wallpaper_labels = []
        

        QTimer.singleShot(0, self.reflow_gallery)

    def load_favorites(self):
        """Cargar lista de favoritos desde archivo JSON"""
        if FAVORITES_FILE.exists():
            try:
                with open(FAVORITES_FILE, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_favorites(self):
        """Guardar favoritos en archivo JSON"""
        FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(list(self.favorites), f)

    def toggle_favorite(self, img_path: str, star_label: QLabel):
        """Alternar estado de favorito"""
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
        """Mostrar todos los wallpapers"""
        self.current_filter = "all"
        self.reload_gallery_view()

    def show_favorites_only(self):
        """Mostrar solo favoritos"""
        self.current_filter = "favorites"
        self.reload_gallery_view()

    def reload_gallery_view(self):
        """Recargar la vista de la galería según el filtro actual"""

        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.load_gallery_from_disk()

    def search_wallpapers(self):
        query = self.search_input.text().strip()
        
        if not query:
            QMessageBox.warning(
                self,
                "Atención",
                "Ingresá un término de búsqueda"
            )
            return
        
        self.search_button.setEnabled(False)
        self.search_input.setEnabled(False)
        self.load_button.setEnabled(False)
        self.show_loader()

        self.worker = GalleryWorker(query=query)
        self.worker.finished.connect(self.on_gallery_loaded)
        self.worker.error.connect(self.on_gallery_error)
        self.worker.start()


    def load_gallery_from_disk(self):
        wallpapers_dir = BASE_DIR / "assets" / "wallpaperss"

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
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            label = QLabel()
            pixmap = QPixmap(str(thumb_path))

            label.setPixmap(
                pixmap.scaled(
                    300, 170,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

            label.setFixedSize(300, 170)
            label.setAlignment(Qt.AlignCenter)
            label.setCursor(Qt.PointingHandCursor)

            label.setProperty("wallpaper_path", str(img_path))
            label.mousePressEvent = lambda e, l=label: self.on_wallpaper_clicked(l)

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

            container_layout.addWidget(label)
            container_layout.addWidget(star_label)

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
        self.worker.start()



    def on_gallery_loaded(self, wallpapers):
        self.hide_loader()

        for img_path, thumb_path in wallpapers:
            self.add_wallpaper(img_path, thumb_path)

        self.reflow_gallery()
        
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)

    def add_wallpaper(self, img_path, thumb_path):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        label = QLabel()
        pixmap = QPixmap(str(thumb_path))

        label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border-radius: 14px;
            }
            """)

        label.setProperty("hover", False)

        label.setStyleSheet("""
        QLabel {
            background-color: #1e1e1e;
            border-radius: 14px;
        }

        QLabel[hover="true"] {
            background-color: #242424;
        }
        """)

        label.enterEvent = lambda e, l=label: (
            l.setProperty("hover", True),
            l.style().polish(l)
        )

        label.leaveEvent = lambda e, l=label: (
            l.setProperty("hover", False),
            l.style().polish(l)
        )

        label.setStyleSheet("""
        QLabel[selected="true"] {
            border: 2px solid #ff9800;
        }
        """)


        label.setPixmap(
            pixmap.scaled(
                300, 170,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        label.setFixedSize(300, 170)
        label.setAlignment(Qt.AlignCenter)
        label.setCursor(Qt.PointingHandCursor)

        label.setProperty("wallpaper_path", str(img_path))
        label.mousePressEvent = lambda e, l=label: self.on_wallpaper_clicked(l)

        # Estrella de favorito
        star_label = QLabel("⭐" if str(img_path) in self.favorites else "☆")
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

        container_layout.addWidget(label)
        container_layout.addWidget(star_label)

        self.gallery_layout.addWidget(container)


    def on_gallery_error(self, message):
        self.hide_loader()
        
        self.search_button.setEnabled(True)
        self.search_input.setEnabled(True)

        QMessageBox.critical(self, "Error", message)


    def on_wallpaper_clicked(self, label: QLabel):
        path = label.property("wallpaper_path")
        if not path:
            return

        if self.selected_label:
            self.selected_label.setStyleSheet("")

        label.setStyleSheet("""
            border: 3px solid #FF8300;
            border-radius: 6px;
        """)

        self.selected_label = label
        self.selected_wallpaper = Path(path)

        self.selected_info.setText(
            f"Seleccionado: {self.selected_wallpaper.name}"
        )




    def apply_selected_wallpaper(self):
        if not self.selected_wallpaper:
            QMessageBox.warning(
            self,
            "Atención",
            "Seleccioná un wallpaper primero"
            )
            return

        try:
            set_wallpaper(self.selected_wallpaper)
            QMessageBox.information(
            self,
            "Wallpaper aplicado",
            "El fondo se aplicó correctamente"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

    def delete_selected_wallpaper(self):
        if not self.selected_wallpaper or not self.selected_label:
            QMessageBox.warning(
                self,
                "Atención",
                "No hay ningún wallpaper seleccionado"
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar este wallpaper?\n\n{self.selected_wallpaper.name}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            
            img_path = self.selected_wallpaper
            thumb_path = img_path.with_name(img_path.stem + "_thumb.jpg")

            if img_path.exists():
                img_path.unlink()

            if thumb_path.exists():
                thumb_path.unlink()


            if str(img_path) in self.favorites:
                self.favorites.remove(str(img_path))
                self.save_favorites()

            

            parent = self.selected_label.parent()
            self.gallery_layout.removeWidget(parent)
            parent.deleteLater()

            
            self.selected_label = None
            self.selected_wallpaper = None
            self.selected_info.setText("Seleccionado: ninguno")

            self.reflow_gallery()

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
        rect = self.centralWidget().rect()
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