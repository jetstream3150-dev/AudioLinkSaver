import os,sys,threading,queue
from pathlib import Path
from urllib.parse import urlparse
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp

class App(tk.Tk):
 def __init__(self):
  super().__init__()
  self.title("Audio Link Saver 1.0")
  self.geometry("680x440")
  self.configure(bg="#121a2a")
  self.url=tk.StringVar()
  self.folder=tk.StringVar(value=str(Path.home()/"Music"))
  self.format=tk.StringVar(value="MP3")
  self.status=tk.StringVar(value="URLを貼り付けてください")
  self.events=queue.Queue()
  self.running=False
  self.make_ui()
  self.after(120,self.poll)
 def make_ui(self):
  style=ttk.Style()
  style.theme_use("clam")
  style.configure("Main.TFrame",background="#121a2a")
  style.configure("Main.TLabel",background="#121a2a",foreground="#f4f7ff",font=("Yu Gothic UI",11))
  style.configure("Title.TLabel",background="#121a2a",foreground="white",font=("Yu Gothic UI",22,"bold"))
  frame=ttk.Frame(self,padding=26,style="Main.TFrame");frame.pack(fill="both",expand=True)
  ttk.Label(frame,text="♪ Audio Link Saver",style="Title.TLabel").pack(anchor="w",pady=(0,20))
  ttk.Label(frame,text="動画・音声のURL",style="Main.TLabel").pack(anchor="w")
  row=ttk.Frame(frame,style="Main.TFrame");row.pack(fill="x",pady=(5,14))
  ttk.Entry(row,textvariable=self.url).pack(side="left",fill="x",expand=True)
  ttk.Button(row,text="貼り付け",command=self.paste).pack(side="left",padx=(6,0))
  ttk.Label(frame,text="保存先フォルダー",style="Main.TLabel").pack(anchor="w")
  row=ttk.Frame(frame,style="Main.TFrame");row.pack(fill="x",pady=(5,14))
  ttk.Entry(row,textvariable=self.folder).pack(side="left",fill="x",expand=True)
  ttk.Button(row,text="参照",command=self.browse).pack(side="left",padx=(6,0))
  ttk.Label(frame,text="保存形式",style="Main.TLabel").pack(anchor="w")
  ttk.Combobox(frame,textvariable=self.format,values=["MP3","M4A","WAV"],state="readonly",width=15).pack(anchor="w",pady=(5,14))
  self.progress=ttk.Progressbar(frame,maximum=100);self.progress.pack(fill="x")
  ttk.Label(frame,textvariable=self.status,style="Main.TLabel",wraplength=570).pack(anchor="w",pady=10)
  self.button=ttk.Button(frame,text="音声を保存",command=self.start);self.button.pack(fill="x",ipady=7)
  ttk.Label(frame,text="保存が許可された音源だけに使用してください。",style="Main.TLabel").pack(anchor="w",pady=12)
 def paste(self):
  try:self.url.set(self.clipboard_get().strip())
  except tk.TclError:messagebox.showwarning("貼り付け","クリップボードにテキストがありません。")
 def browse(self):
  selected=filedialog.askdirectory(initialdir=self.folder.get())
  if selected:self.folder.set(selected)
 def start(self):
  if self.running:return
  url=self.url.get().strip()
  parsed=urlparse(url)
  if parsed.scheme not in ("http","https") or not parsed.netloc:
   messagebox.showerror("URLエラー","有効なURLを入力してください。");return
  folder=Path(self.folder.get())
  try:folder.mkdir(exist_ok=True,parents=True)
  except OSError as e:messagebox.showerror("保存先エラー",str(e));return
  self.running=True
  self.button.configure(state="disabled")
  self.progress["value"]=0
  self.status.set("処理中…")
  threading.Thread(target=self.worker,args=(url,str(folder),self.format.get().lower()),daemon=True).start()
 def worker(self,url,folder,fmt):
  try:
   root=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
   ff=str(root) if (root/"ffmpeg.exe").exists() else None
   def hook(d):
    if d.get("status")=="downloading":
     total=d.get("total_bytes") or d.get("total_bytes_estimate")
     if total:self.events.put(("progress",100*d.get("downloaded_bytes",0)/total))
    elif d.get("status")=="finished":self.events.put(("status","音声を変換しています…"))
   options={"format":"bestaudio/best","outtmpl":str(Path(folder)/"%(title).180B [%(id)s].%(ext)s"),
    "noplaylist":True,"progress_hooks":[hook],"quiet":True,"no_warnings":True,
    "postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":fmt,"preferredquality":"192"}]}
   if ff:options["ffmpeg_location"]=ff
   with yt_dlp.YoutubeDL(options) as downloader:downloader.download([url])
   self.events.put(("done","保存が完了しました！"))
  except Exception as e:self.events.put(("error",str(e)))
 def poll(self):
  try:
   while True:
    name,val=self.events.get_nowait()
    if name=="progress":self.progress["value"]=val
    elif name=="status":self.status.set(val)
    else:
     self.running=False;self.button.configure(state="normal")
     self.status.set(val if name=="done" else "エラー: "+val[:350])
     if name=="done":self.progress["value"]=100
  except queue.Empty:pass
  self.after(120,self.poll)
if __name__=="__main__":App().mainloop()
