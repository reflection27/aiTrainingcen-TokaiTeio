import urllib.request
import zipfile
import os

url = 'https://github.com/godotengine/godot/releases/download/4.6.2-stable/Godot_v4.6.2-stable_win64.exe.zip'
zip_path = 'godot_tmp.zip'
dest_dir = 'plugins/godot/Godot_v4.6.2-stable_win64.exe'
os.makedirs(dest_dir, exist_ok=True)
print('  下载中（约 100MB）...')
urllib.request.urlretrieve(url, zip_path)
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(dest_dir)
os.remove(zip_path)
print('  Godot 下载完成')
