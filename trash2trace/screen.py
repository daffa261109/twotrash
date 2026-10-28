"""Jendela layar penuh tanpa Chromium. Pi Zero tidak punya NEON, jadi Chromium menolak jalan."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

_CATEGORY_COLOR = {
    "organic": "#3ddc6a",
    "nonorganic": "#7ec8ff",
    "other": "#ffb020",
}


def screen_command(port: int) -> list[str]:
    return [sys.executable, "-m", "trash2trace.screen", "--port", str(port)]


def presentation(data: dict) -> dict:
    tone = str(data.get("tone") or "idle")
    title = str(data.get("title") or "")
    headline = str(data.get("headline") or "")
    show_category = bool(title) and title != headline and tone not in ("idle", "wait", "reading")
    return {
        "category": title if show_category else "",
        "headline": headline,
        "detail": str(data.get("detail") or ""),
        "category_color": _CATEGORY_COLOR.get(tone, "#f4fff8"),
        "headline_color": "#ffe08a" if tone == "wait" else "#f4fff8",
        "big": tone == "wait",
    }


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=2) as response:
        return response.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Layar penuh pemilah.")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
    except ImportError:
        print("Jendela layar belum bisa dibuka. Di Pi jalankan:")
        print("  sudo apt install python3-tk python3-pil.imagetk")
        return 1
    _run(args.port, tk, Image, ImageTk)
    return 0


def _run(port: int, tk, image_module, image_tk_module) -> None:
    import io

    root = tk.Tk()
    root.title("TRASH2TRASH")
    root.configure(bg="#07110e", cursor="none")
    root.attributes("-fullscreen", True)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

    copy = tk.Frame(root, bg="#07110e")
    copy.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
    width = root.winfo_screenwidth() or 800
    logo_size = max(36, width // 16)
    text_size = max(18, width // 36)
    brand = tk.Frame(copy, bg="#07110e")
    brand.pack(anchor="w")
    tk.Label(brand, text="TRASH", fg="#3ddc6a", bg="#07110e", font=("DejaVu Sans", logo_size, "bold")).pack(side="left")
    tk.Label(brand, text="2", fg="#f7fff9", bg="#07110e", font=("DejaVu Sans", logo_size, "bold")).pack(side="left")
    tk.Label(copy, text="TRASH", fg="#3ddc6a", bg="#07110e", font=("DejaVu Sans", logo_size, "bold")).pack(anchor="w")
    category = tk.Label(copy, text="", fg="#3ddc6a", bg="#07110e", font=("DejaVu Sans", text_size, "bold"))
    category.pack(anchor="w", pady=(18, 0))
    headline = tk.Label(copy, text="", fg="#f4fff8", bg="#07110e", font=("DejaVu Sans", text_size, "bold"), wraplength=max(240, width // 2 - 80), justify="left")
    headline.pack(anchor="w", pady=(8, 0))
    detail = tk.Label(copy, text="", fg="#b7c9bf", bg="#07110e", font=("DejaVu Sans", max(14, text_size - 6), "bold"), wraplength=max(240, width // 2 - 80), justify="left")
    detail.pack(anchor="w", pady=(8, 0))

    shot = tk.Label(root, bg="#000000", highlightthickness=3, highlightbackground="#3ddc6a")
    shot.grid(row=0, column=1, sticky="nsew", padx=(0, 28), pady=24)
    holder: dict = {"image": None}
    base = f"http://127.0.0.1:{port}"

    def tick() -> None:
        try:
            view = presentation(json.loads(_get(base + "/status").decode()))
            category.configure(text=view["category"], fg=view["category_color"])
            size = max(72, width // 8) if view["big"] else text_size
            headline.configure(text=view["headline"], fg=view["headline_color"], font=("DejaVu Sans", size, "bold"))
            detail.configure(text=view["detail"])
        except Exception:
            pass
        try:
            picture = image_module.open(io.BytesIO(_get(base + "/frame.jpg")))
            box_w = max(1, shot.winfo_width())
            box_h = max(1, shot.winfo_height())
            if box_w > 20 and box_h > 20:
                resample = getattr(getattr(image_module, "Resampling", image_module), "BILINEAR")
                picture = picture.resize((box_w, box_h), resample)
            photo = image_tk_module.PhotoImage(picture)
            holder["image"] = photo
            shot.configure(image=photo)
        except Exception:
            pass
        root.after(150, tick)

    root.after(150, tick)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
