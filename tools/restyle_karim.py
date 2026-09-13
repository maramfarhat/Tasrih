#!/usr/bin/env python3
"""Restyle l'avatar Karim : peau méditerranéenne naturelle, cheveux brun foncé,
yeux marron, costume sombre. Objectif : un rendu naturel et chaleureux, pas pâle.

Extrait les textures embarquées du GLB, les retouche, et écrit les fichiers
retouchés dans frontend/public/avatars/karim/ (jamais dans le GLB d'origine).

Usage:  backend/.venv/bin/python tools/restyle_karim.py
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "frontend" / "public" / "avatars" / "avatarsdk.glb"
OUT = ROOT / "frontend" / "public" / "avatars" / "karim"
OUT.mkdir(parents=True, exist_ok=True)

# Cibles (HSV, échelle PIL 0-255)
SKIN = {"h": 13, "s": 90, "v": 200}   # hâlé méditerranéen, sain
HAIR = {"h": 15, "s": 100, "v": 70}   # brun foncé naturel
IRIS = {"h": 17, "s": 150, "v": 80}   # marron


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
        name = (img.get("name") or f"img{len(out)}").replace(" ", "_")
        out[name] = Image.open(io.BytesIO(raw)).convert("RGB")
    return out


def hsv_split(im: Image.Image) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    a = np.asarray(im.convert("HSV")).astype(np.int16)
    return a, a[..., 0], a[..., 1], a[..., 2]


def blend(a: np.ndarray, H, S, V, mask: np.ndarray, target: dict, k: float) -> None:
    """Déplace les canaux HSV des pixels du mask vers la teinte cible (mélange doux)."""
    if not mask.any():
        return
    a[..., 0][mask] = np.clip(H[mask] + (target["h"] - H[mask]) * k, 0, 255).astype(np.int16)
    a[..., 1][mask] = np.clip(S[mask] + (target["s"] - S[mask]) * k, 0, 255).astype(np.int16)
    a[..., 2][mask] = np.clip(V[mask] + (target["v"] - V[mask]) * k, 0, 255).astype(np.int16)


def save(arr_hsv: np.ndarray, name: str) -> None:
    im = Image.fromarray(arr_hsv.astype(np.uint8), mode="HSV").convert("RGB")
    im.save(OUT / name, quality=92)
    print(f"  écrit {name}  ({im.size[0]}x{im.size[1]})")


def restyle_head(im: Image.Image) -> None:
    """Peau hâlée naturelle + cheveux brun foncé."""
    a, H, S, V = hsv_split(im)
    warm = (H >= 5) & (H <= 45)
    hair = warm & (V < 150) & (S > 50)
    skin = warm & (V >= 150) & (S < 150)
    print(f"  cheveux: {100 * hair.sum() // H.size}% · peau: {100 * skin.sum() // H.size}%")
    blend(a, H, S, V, hair, HAIR, 0.75)
    blend(a, H, S, V, skin, SKIN, 0.70)
    save(a, "head.jpg")


def restyle_body(im: Image.Image) -> None:
    """Même peau que la tête pour rester cohérent."""
    a, H, S, V = hsv_split(im)
    warm = (H >= 5) & (H <= 45)
    skin = warm & (V >= 140) & (S < 160)
    print(f"  peau: {100 * skin.sum() // H.size}%")
    blend(a, H, S, V, skin, SKIN, 0.70)
    save(a, "body.jpg")


def restyle_eyes(im: Image.Image) -> None:
    """Iris marron ; on garde le blanc et la pupille."""
    a, H, S, V = hsv_split(im)
    iris = (S > 40) & (V > 40) & (V < 230)
    print(f"  iris: {100 * iris.sum() // H.size}%")
    blend(a, H, S, V, iris, IRIS, 0.70)
    save(a, "eyes.jpg")


def restyle_cloth(im: Image.Image, name: str, value_scale: float) -> None:
    """Assombrit un vêtement (costume) sans le rendre noir absolu."""
    a, H, S, V = hsv_split(im)
    a[..., 1] = (S * 0.35).astype(np.int16)
    a[..., 2] = np.clip(V * value_scale + 6, 4, 255).astype(np.int16)
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
        restyle_cloth(imgs["longsleeve_Debed_Color_1K"], "top.jpg", 0.30)
    if "jeans_AZAT_Color_1K" in imgs:
        restyle_cloth(imgs["jeans_AZAT_Color_1K"], "bottom.jpg", 0.26)
    if "sneakers_AZAT_Color_1K" in imgs:
        restyle_cloth(imgs["sneakers_AZAT_Color_1K"], "shoes.jpg", 0.30)
    print(f"terminé → {OUT}")


if __name__ == "__main__":
    main()
