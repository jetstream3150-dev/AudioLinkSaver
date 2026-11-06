import os,sys,shutil,subprocess,tempfile
from pathlib import Path
import imageio_ffmpeg
root=Path(__file__).resolve().parent
ff=Path(imageio_ffmpeg.get_ffmpeg_exe())
if not ff.is_file():raise RuntimeError("FFmpeg missing")
with tempfile.TemporaryDirectory() as temp:
 target=Path(temp)/"ffmpeg.exe"
 shutil.copy2(ff,target)
 cmd=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onefile","--windowed","--name","AudioLinkSaver","--collect-all","yt_dlp","--add-binary",f"{target}{os.pathsep}.",str(root/"app.py")]
 subprocess.check_call(cmd,cwd=root)
print("Created dist/AudioLinkSaver.exe")
