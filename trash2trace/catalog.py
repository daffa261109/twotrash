"""Tabel subkategori sampah. API boleh mengirim id atau nama ini di field item."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WasteItem:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...] = ()


# Kategori pemilah tetap tiga. Subkategori hanya memperjelas benda di layar.
ITEMS: tuple[WasteItem, ...] = (
    WasteItem("kulit_pisang", "Kulit pisang", "organic", ("pisang",)),
    WasteItem("sisa_nasi", "Sisa nasi", "organic"),
    WasteItem("sisa_sayur", "Sisa sayur", "organic"),
    WasteItem("kulit_buah", "Kulit buah", "organic"),
    WasteItem("daun", "Daun", "organic"),
    WasteItem("ampas_kopi", "Ampas kopi", "organic"),
    WasteItem("ampas_teh", "Ampas teh", "organic"),
    WasteItem("cangkang_telur", "Cangkang telur", "organic"),
    WasteItem("tulang", "Tulang", "organic"),
    WasteItem("botol", "Botol", "nonorganic", ("botol plastik", "botol kaca")),
    WasteItem("kaleng_minuman", "Kaleng minuman", "nonorganic", ("sampah kaleng minuman", "kaleng")),
    WasteItem("gelas_plastik", "Gelas plastik", "nonorganic"),
    WasteItem("kantong_plastik", "Kantong plastik", "nonorganic"),
    WasteItem("tutup_botol", "Tutup botol", "nonorganic"),
    WasteItem("kertas", "Kertas", "nonorganic"),
    WasteItem("kardus", "Kardus", "nonorganic"),
    WasteItem("sedotan", "Sedotan", "nonorganic"),
    WasteItem("tisu", "Tisu", "other", ("tisu bekas",)),
    WasteItem("popok", "Popok", "other"),
    WasteItem("masker", "Masker", "other"),
    WasteItem("puntung_rokok", "Puntung rokok", "other"),
    WasteItem("styrofoam", "Styrofoam", "other"),
    WasteItem("sampah_campuran", "Sampah campuran", "other"),
)

_CATEGORIES = {"organic", "nonorganic", "other"}


def _key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _index() -> dict[str, WasteItem]:
    found: dict[str, WasteItem] = {}
    for item in ITEMS:
        if item.category not in _CATEGORIES:
            raise ValueError(f"Kategori {item.category} tidak dikenal")
        for label in (item.id, item.name, *item.aliases):
            key = _key(label)
            if key in found and found[key].id != item.id:
                raise ValueError(f"Nama bentrok: {label}")
            found[key] = item
    return found


_BY_KEY = _index()


def find_item(value: str) -> WasteItem | None:
    if not value or not value.strip():
        return None
    return _BY_KEY.get(_key(value))
