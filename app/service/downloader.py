import requests
from pathlib import Path
import random

WALLPAPER_DIR = Path(__file__).resolve().parent.parent / "assets" / "wallpaperss"

UNSPLASH_ACCESS_KEY = "sCDDEz4gbv1AqxU3tYyKNX1ABXyXdOV4KISFHjH-bAc"

def get_existing_wallpapers(folder: Path) -> set[str]:
    return {p.stem for p in folder.glob("*.jpg") if not p.name.endswith("_thumb.jpg")}


def download_random_wallpaper(query="wallpaper"):
    WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)

    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "orientation": "landscape",
        "content_filter": "high",
    }
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    image_url = data["urls"]["full"]
    image_id = data["id"]

    img_response = requests.get(image_url, timeout=10)
    img_response.raise_for_status()

    file_path = WALLPAPER_DIR / f"{image_id}.jpg"

    with open(file_path, "wb") as f:
        f.write(img_response.content)

    return file_path

def download_wallpaper_list(query="anime wallpaper", count=6, max_attempts=20):
    WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)

    existing_ids = get_existing_wallpapers(WALLPAPER_DIR)
    downloaded = []
    attempts = 0

    url = "https://api.unsplash.com/photos/random"
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }

    while len(downloaded) < count and attempts < max_attempts:
        attempts += 1

        params = {
            "query": query,
            "orientation": "landscape",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        item = response.json()

        image_id = item["id"]

        
        if image_id in existing_ids:
            continue

        image_url = item["urls"]["full"]
        thumb_url = item["urls"]["small"]

        img_path = WALLPAPER_DIR / f"{image_id}.jpg"
        thumb_path = WALLPAPER_DIR / f"{image_id}_thumb.jpg"

        
        img_data = requests.get(image_url, timeout=10).content
        img_path.write_bytes(img_data)

        
        thumb_data = requests.get(thumb_url, timeout=10).content
        thumb_path.write_bytes(thumb_data)

        downloaded.append((img_path, thumb_path))
        existing_ids.add(image_id)

    return downloaded
