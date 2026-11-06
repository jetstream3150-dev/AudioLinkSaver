"""Audio Link Saver 2.0 — authorized audio downloads only."""
import io
import json
import queue
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp
from PIL import Image, ImageTk

BG = "#0b1020"
PANEL = "#171f32"
INPUT = "#222d45"
FG = "#f4f7ff"
MUTED = "#a0aec8"
ACCENT = "#7c6aff"
GREEN = "#2bd4a5"
DATA_DIR = Path.home() / "AppData" / "Local" / "AudioLinkSaver" if sys.platform == "win32" else Path.home() / ".audio-link-saver"
HISTORY_PATH = DATA_DIR / "history.json"


def load_history():
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data[:500] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_history(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = HISTORY_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data[:500], ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(HISTORY_PATH)


def valid_url(value):
    parsed = urlparse(value.strip())
    return parsed.scheme in ("https", "http") and bool(parsed.netloc)


def ffmpeg_path():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base) if (base / "ffmpeg.exe").exists() else None


def extract_entries(url):
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist",
            "skip_download": True, "ignoreerrors": True, "playlistend": 250}
    with yt_dlp.YoutubeDL(opts) as dl:
        info = dl.extract_info(url, download=False)
    if not info:
        raise ValueError("動画の情報を取得できませんでした")
    if info.get("_type") == "playlist" or info.get("entries") is not None:
        entries = []
        for item in info.get("entries") or []:
            if not item:
                continue
            target = item.get("webpage_url") or item.get("url") or ""
            if target and not target.startswith("http"):
                if item.get("id"):
                    target = "https://www.youtube.com/watch?v=" + str(item["id"])
                else:
                    continue
            if valid_url(target):
                entries.append({"url": target, "title": item.get("title") or target,
                                "thumbnail": item.get("thumbnail") or ""})
        return entries
    return [{"url": url, "title": info.get("title") or url,
             "thumbnail": info.get("thumbnail") or ""}]


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Link Saver 2.0")
        self.geometry("1050x760")
        self.minsize(850, 620)
        self.configure(bg=BG)
        self.url = tk.StringVar()
        self.folder = tk.StringVar(value=str(Path.home() / "Music"))
        self.format = tk.StringVar(value="MP3")
        self.status = tk.StringVar(value="URLを貼り付けて「曲を追加」を押してください")
        self.progress_text = tk.StringVar(value="0 / 0")
        self.events = queue.Queue()
        self.tracks = []
        self.history = load_history()
        self.busy = False
        self.thumbnail_image = None
        self.setup_styles()
        self.draw()
        self.refresh_history()
        self.after(120, self.poll_events)

    def setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Dark.TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Dark.TLabel", background=BG, foreground=FG, font=("Yu Gothic UI", 11))
        s.configure("Mute.TLabel", background=BG, foreground=MUTED, font=("Yu Gothic UI", 10))
        s.configure("Panel.TLabel", background=PANEL, foreground=FG, font=("Yu Gothic UI", 10))
        s.configure("Title.TLabel", background=BG, foreground=FG, font=("Yu Gothic UI", 25, "bold"))
        s.configure("Dark.TEntry", fieldbackground=INPUT, foreground=FG, bordercolor=INPUT, padding=8)
        s.configure("Accent.TButton", background=ACCENT, foreground="white", padding=(18, 11), font=("Yu Gothic UI", 11, "bold"))
        s.map("Accent.TButton", background=[("active", "#9687ff"), ("disabled", "#4b4d65")])
        s.configure("Soft.TButton", background=INPUT, foreground=FG, padding=(12, 9))
        s.map("Soft.TButton", background=[("active", "#35425e")])
        s.configure("Dark.TCombobox", fieldbackground=INPUT, foreground=FG, background=INPUT, padding=7)
        s.configure("Dark.Horizontal.TProgressbar", background=GREEN, troughcolor=INPUT)
        s.configure("Dark.Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG,
                    rowheight=32, borderwidth=0, font=("Yu Gothic UI", 10))
        s.map("Dark.Treeview", background=[("selected", "#3c3768")])
        s.configure("Dark.Treeview.Heading", background=INPUT, foreground=FG, padding=8)
        s.configure("Dark.TNotebook", background=BG, borderwidth=0)
        s.configure("Dark.TNotebook.Tab", background=INPUT, foreground=MUTED, padding=(20, 11))
        s.map("Dark.TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", FG)])

    def draw(self):
        root = ttk.Frame(self, style="Dark.TFrame", padding=(28, 20))
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="◉  AUDIO LINK SAVER", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="YOUR MUSIC, YOUR LIBRARY   •   v2.0", style="Mute.TLabel").pack(anchor="w", pady=(0, 18))
        bar = ttk.Frame(root, style="Dark.TFrame")
        bar.pack(fill="x", pady=(0, 12))
        self.url_entry = ttk.Entry(bar, textvariable=self.url, style="Dark.TEntry")
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.paste_btn = ttk.Button(bar, text="貼り付け", style="Soft.TButton", command=self.paste)
        self.paste_btn.pack(side="left", padx=(8, 0))
        self.add_btn = ttk.Button(bar, text="＋ 曲を追加", style="Accent.TButton", command=self.add_urls)
        self.add_btn.pack(side="left", padx=(8, 0))
        settings = ttk.Frame(root, style="Dark.TFrame")
        settings.pack(fill="x", pady=(0, 16))
        ttk.Label(settings, text="保存先", style="Dark.TLabel").pack(side="left")
        ttk.Entry(settings, textvariable=self.folder, width=38, style="Dark.TEntry").pack(side="left", padx=(9, 5), fill="x", expand=True)
        ttk.Button(settings, text="参照", style="Soft.TButton", command=self.browse).pack(side="left")
        ttk.Label(settings, text="   形式", style="Dark.TLabel").pack(side="left")
        ttk.Combobox(settings, textvariable=self.format, values=["MP3", "M4A", "WAV"], state="readonly",
                     width=7, style="Dark.TCombobox").pack(side="left", padx=(8, 0))
        tabs = ttk.Notebook(root, style="Dark.TNotebook")
        tabs.pack(fill="both", expand=True)
        library = ttk.Frame(tabs, style="Panel.TFrame", padding=12)
        history = ttk.Frame(tabs, style="Panel.TFrame", padding=12)
        tabs.add(library, text="ダウンロードリスト")
        tabs.add(history, text="履歴")
        row = ttk.Frame(library, style="Panel.TFrame")
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="曲・プレイリスト一覧", style="Panel.TLabel").pack(side="left")
        ttk.Button(row, text="選択を削除", style="Soft.TButton", command=self.remove_selected).pack(side="right")
        self.tree = ttk.Treeview(library, columns=("title", "state"), show="headings", style="Dark.Treeview", selectmode="extended")
        self.tree.heading("title", text="曲名")
        self.tree.heading("state", text="状態")
        self.tree.column("title", width=680, minwidth=250)
        self.tree.column("state", width=160, minwidth=100)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_preview)
        preview = ttk.Frame(library, style="Panel.TFrame")
        preview.pack(fill="x", pady=(10, 0))
        self.thumb = tk.Label(preview, text="♪", bg=INPUT, fg=FG, width=18, height=5, font=("Yu Gothic UI", 20))
        self.thumb.pack(side="left")
        self.preview_name = ttk.Label(preview, text="曲を選択するとプレビューを表示", style="Panel.TLabel")
        self.preview_name.pack(side="left", padx=14)
        actions = ttk.Frame(library, style="Panel.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        self.save_btn = ttk.Button(actions, text="▶ すべて保存", style="Accent.TButton", command=self.start_download)
        self.save_btn.pack(side="right")
        ttk.Label(actions, text="1回に追加できるプレイリストは最大250曲", style="Panel.TLabel").pack(side="left")
        self.history_tree = ttk.Treeview(history, columns=("date", "title", "format", "result"), show="headings", style="Dark.Treeview")
        for key, label, width in [("date", "日時", 160), ("title", "曲名", 440), ("format", "形式", 70), ("result", "結果", 130)]:
            self.history_tree.heading(key, text=label)
            self.history_tree.column(key, width=width, minwidth=70)
        self.history_tree.pack(fill="both", expand=True)
        ttk.Button(history, text="履歴を消去", style="Soft.TButton", command=self.clear_history).pack(anchor="e", pady=10)
        footer = ttk.Frame(root, style="Dark.TFrame")
        footer.pack(fill="x", pady=(14, 0))
        self.progress = ttk.Progressbar(footer, maximum=100, style="Dark.Horizontal.TProgressbar")
        self.progress.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, style="Dark.TLabel").pack(side="left", pady=7)
        ttk.Label(footer, textvariable=self.progress_text, style="Mute.TLabel").pack(side="right", pady=7)
        ttk.Label(root, text="権利者が保存を許可した音源にのみ使用してください。", style="Mute.TLabel").pack(anchor="w")

    def paste(self):
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            messagebox.showwarning("貼り付け", "テキストをコピーしてください")

    def browse(self):
        path = filedialog.askdirectory(initialdir=self.folder.get())
        if path:
            self.folder.set(path)

    def set_busy(self, value):
        self.busy = value
        for button in (self.add_btn, self.save_btn, self.paste_btn):
            button.configure(state="disabled" if value else "normal")

    def add_urls(self):
        if self.busy:
            return
        urls = [x.strip() for x in self.url.get().splitlines() if x.strip()]
        if not urls or any(not valid_url(u) for u in urls):
            messagebox.showerror("URL", "http:// または https:// で始まる有効なURLを入力してください")
            return
        self.set_busy(True)
        self.status.set("曲名・プレイリスト情報を取得中…")
        threading.Thread(target=self.lookup_worker, args=(urls,), daemon=True).start()

    def lookup_worker(self, urls):
        try:
            items = []
            for url in urls:
                items.extend(extract_entries(url))
            self.events.put(("loaded", items))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def remove_selected(self):
        if self.busy:
            return
        ids = {int(x) for x in self.tree.selection()}
        self.tracks = [x for i, x in enumerate(self.tracks) if i not in ids]
        self.render_tracks()

    def render_tracks(self):
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(self.tracks):
            self.tree.insert("", "end", iid=str(i), values=(item["title"], item.get("state", "待機中")))
        self.progress_text.set("0 / " + str(len(self.tracks)))

    def show_preview(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        track = self.tracks[int(selection[0])]
        self.preview_name.configure(text=track["title"][:80])
        self.thumb.configure(image="", text="♪")
        self.thumbnail_image = None
        url = track.get("thumbnail")
        if url:
            threading.Thread(target=self.image_worker, args=(url, track["url"]), daemon=True).start()

    def image_worker(self, url, source_url):
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                content = response.read(2_000_000)
            img = Image.open(io.BytesIO(content))
            img.thumbnail((148, 86))
            self.events.put(("image", (source_url, img.copy())))
        except Exception:
            pass

    def start_download(self):
        if self.busy or not self.tracks:
            messagebox.showinfo("ダウンロード", "先に曲を追加してください")
            return
        folder = Path(self.folder.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("保存先", str(exc))
            return
        self.set_busy(True)
        self.progress["value"] = 0
        fmt = self.format.get().lower()
        batch = [dict(t) for t in self.tracks]
        threading.Thread(target=self.download_worker, args=(batch, str(folder), fmt), daemon=True).start()

    def download_worker(self, items, folder, fmt):
        ff = ffmpeg_path()
        for idx, track in enumerate(items):
            self.events.put(("item", (idx, "ダウンロード中")))
            self.events.put(("counter", (idx, len(items))))
            def hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    if total:
                        self.events.put(("progress", 100 * d.get("downloaded_bytes", 0) / total))
                elif d.get("status") == "finished":
                    self.events.put(("status", "音声変換中…"))
            opts = {"format": "bestaudio/best", "outtmpl": str(Path(folder) / "%(title).180B [%(id)s].%(ext)s"),
                    "noplaylist": True, "quiet": True, "no_warnings": True,
                    "progress_hooks": [hook],
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": fmt, "preferredquality": "192"}]}
            if ff:
                opts["ffmpeg_location"] = ff
            try:
                with yt_dlp.YoutubeDL(opts) as dl:
                    dl.download([track["url"]])
                result = "成功"
                self.events.put(("item", (idx, "完了")))
            except Exception as exc:
                result = "失敗: " + str(exc)[:170]
                self.events.put(("item", (idx, "失敗")))
            self.events.put(("history", {"date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "title": track["title"], "url": track["url"],
                                        "format": fmt.upper(), "result": result}))
            self.events.put(("progress", 0))
        self.events.put(("complete", len(items)))

    def refresh_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        for row in self.history:
            self.history_tree.insert("", "end", values=(row.get("date", ""), row.get("title", ""),
                                                           row.get("format", ""), row.get("result", "")))

    def clear_history(self):
        if not messagebox.askyesno("確認", "ダウンロード履歴を削除しますか？（音声ファイルは削除しません）"):
            return
        self.history.clear()
        try:
            save_history(self.history)
        except OSError as exc:
            messagebox.showerror("履歴保存", str(exc))
        self.refresh_history()

    def poll_events(self):
        try:
            for _ in range(100):
                name, payload = self.events.get_nowait()
                if name == "loaded":
                    existing = {t["url"] for t in self.tracks}
                    for item in payload:
                        if item["url"] not in existing:
                            self.tracks.append(item)
                            existing.add(item["url"])
                    self.render_tracks()
                    self.set_busy(False)
                    self.status.set(f"{len(self.tracks)}曲をリストに追加しました")
                    self.url.set("")
                elif name == "error":
                    self.set_busy(False)
                    self.status.set("取得エラー: " + payload[:220])
                elif name == "image":
                    url, img = payload
                    selected = self.tree.selection()
                    if selected and self.tracks[int(selected[0])]["url"] == url:
                        self.thumbnail_image = ImageTk.PhotoImage(img)
                        self.thumb.configure(image=self.thumbnail_image, text="")
                elif name == "item":
                    idx, state = payload
                    if idx < len(self.tracks):
                        self.tracks[idx]["state"] = state
                        if self.tree.exists(str(idx)):
                            self.tree.set(str(idx), "state", state)
                elif name == "counter":
                    current, total = payload
                    self.progress_text.set(f"{current + 1} / {total}")
                    self.status.set(f"{current + 1}曲目を処理中…")
                elif name == "progress":
                    self.progress["value"] = payload
                elif name == "status":
                    self.status.set(payload)
                elif name == "history":
                    self.history.insert(0, payload)
                    self.history = self.history[:500]
                    try:
                        save_history(self.history)
                    except OSError as exc:
                        self.status.set("履歴を保存できません: " + str(exc))
                    self.refresh_history()
                elif name == "complete":
                    self.set_busy(False)
                    self.progress["value"] = 100
                    self.status.set(f"{payload}曲の処理が終了しました（詳細は履歴をご確認ください）")
        except queue.Empty:
            pass
        self.after(120, self.poll_events)


if __name__ == "__main__":
    Application().mainloop()
