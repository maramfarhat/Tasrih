#!/usr/bin/env python3
"""Restyle l'avatar Karim (générique « sombre et élégant ») : cheveux très foncés,
peau légèrement pâle/froide, yeux bleu-gris, tenue sombre type costume.

Extrait les textures embarquées du GLB, les retouche, et écrit les fichiers
retouchés dans frontend/public/avatars/karim/ (jamais dans le GLB d'origine).

Usage:  backend/.venv/bin/python tools/restyle_karim.py
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "frontend" / "public" / "avatars" / "avatarsdk.glb"
OUT = ROOT / "frontend" / "public" / "avatars" / "karim"
OUT.mkdir(parents=True, exist_ok=True)


def read_images(path: Path) -> dict[str, Image.Image]:
    data = path.read_bytes()
    clen, _ = struct.unpack("<II", data[12:20])
    j = json.loads(data[20 : 20 + clen])
    bin_off = 20 + clen
    blen, _ = struct.unpack("<II", data[bin_off : bin_off + 8])
    bin_start = bin_off + 8
    out: dict[str, Image.Image] = {}
    for img in j.get("images", []):
        bv = j["bufferViews"][img["bufferView"]]
        off = bin_start + bv.get("byteOffset", 0)
        raw = data[off : off + bv["byteLength"]]
        import io

        name = (img.get("name") or f"img{len(out)}").replace(" ", "_")
        out[name] = Image.open(io.BytesIO(raw)).convert("RGB")
    return out


def hsv_split(im: Image.Image) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    a = np.asarray(im.convert("HSV")).astype(np.int16)
    return a, a[..., 0], a[..., 1], a[..., 2]


def save(arr_hsv: np.ndarray, name: str) -> None:
    im = Image.fromarray(arr_hsv.astype(np.uint8), mode="HSV").convert("RGB")
    im.save(OUT / name, quality=92)
    print(f"  écrit {name}  ({im.size[0]}x{im.size[1]})")


def restyle_head(im: Image.Image) -> None:
    """Cheveux quasi noirs + peau pâle/froide."""
    a, H, S, V = hsv_split(im)
    warm = (H >= 5) & (H <= 45)

    # cheveux : chaud, sombre, saturé
    hair = warm & (V < 150) & (S > 50)
    a[..., 1][hair] = (S[hair] * 0.55).astype(np.int16)          # moins saturé
    a[..., 2][hair] = np.clip(V[hair] * 0.20 + 4, 6, 60)          # très sombre
    print(f"  cheveux: {100*hair.sum()//H.size}% des pixels")

    # peau : claire, chaude -> légèrement plus claire et plus froide
    skin = warm & (V >= 150) & (S < 150)
    a[..., 1][skin] = (S[skin] * 0.80).astype(np.int16)
    a[..., 2][skin] = np.clip(V[skin] * 1.03 + 6, 0, 255)         # un peu plus pâle
    a[..., 0][skin] = np.clip(H[skin] - 2, 0, 255)                # teinte plus froide
    print(f"  peau: {100*skin.sum()//H.size}% des pixels")

    save(a, "head.jpg")


def restyle_body(im: Image.Image) -> None:
    """Même peau que la tête pour rester cohérent."""
    a, H, S, V = hsv_split(im)
    warm = (H >= 5) & (H <= 45)
    skin = warm & (V >= 140) & (S < 160)
    a[..., 1][skin] = (S[skin] * 0.80).astype(np.int16)
    a[..., 2][skin] = np.clip(V[skin] * 1.03 + 6, 0, 255)
    a[..., 0][skin] = np.clip(H[skin] - 2, 0, 255)
    save(a, "body.jpg")


def restyle_eyes(im: Image.Image) -> None:
    """Iris bleu-gris ; on garde le blanc et la pupille."""
    a, H, S, V = hsv_split(im)
    iris = (S > 40) & (V > 40) & (V < 230)
    a[..., 0][iris] = 152          # bleu-gris
    a[..., 1][iris] = 70
    a[..., 2][iris] = 140
    save(a, "eyes.jpg")


def darken_suit(im: Image.Image, name: str, value_scale: float = 0.18) -> None:
    """Rend un vêtement quasi noir (costume)."""
    a, H, S, V = hsv_split(im)
    a[..., 1] = (S * 0.30).astype(np.int16)
    a[..., 2] = np.clip(V * value_scale + 6, 4, 255)
    save(a, name)


def main() -> None:
    print(f"lecture {GLB.name}")
    imgs = read_images(GLB)
    if "AvatarHeadMale_Color_1K" in imgs:
        print("tête :")
        restyle_head(imgs["AvatarHeadMale_Color_1K"])
    if "AvatarBodyMale_Color_1K" in imgs:
        print("corps :")
        restyle_body(imgs["AvatarBodyMale_Color_1K"])
    if "AvatarEyes_Color_512" in imgs:
        print("yeux :")
        restyle_eyes(imgs["AvatarEyes_Color_512"])
    print("tenue :")
    if "longsleeve_Debed_Color_1K" in imgs:
        darken_suit(imgs["longsleeve_Debed_Color_1K"], "top.jpg", 0.16)
    if "jeans_AZAT_Color_1K" in imgs:
        darken_suit(imgs["jeans_AZAT_Color_1K"], "bottom.jpg", 0.14)
    if "sneakers_AZAT_Color_1K" in imgs:
        darken_suit(imgs["sneakers_AZAT_Color_1K"], "shoes.jpg", 0.18)
    print(f"terminé → {OUT}")


if __name__ == "__main__":
    main()
