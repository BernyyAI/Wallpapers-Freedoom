import ctypes
from pathlib import Path

def set_wallpaper(image_path: Path):
    image_path = str(image_path.resolve())

    result = ctypes.windll.user32.SystemParametersInfoW(
        20,      
        0,
        image_path,
        3        
    )

    if not result:
        raise RuntimeError("No se pudo aplicar el wallpaper")
