import os
import shutil
import pwd
import grp
import time
from config import ROOT_SAVE_DIR, USER_NAME

def segreguj_stare_nagrania_loop():
    while True:
        try:
            uid = pwd.getpwnam(USER_NAME).pw_uid
            gid = grp.getgrnam(USER_NAME).gr_gid
            
            if os.path.exists(ROOT_SAVE_DIR):
                for camera_folder in os.listdir(ROOT_SAVE_DIR):
                    full_path = os.path.join(ROOT_SAVE_DIR, camera_folder)
                    if not os.path.isdir(full_path): continue

                    for nazwa_pliku in os.listdir(full_path):
                        if nazwa_pliku.startswith("motion_") and nazwa_pliku.endswith((".mp4", ".webm")):
                            parts = nazwa_pliku.split("_")
                            if len(parts) < 3: continue

                            data = parts[1]
                            godzina = parts[2][:2]

                            folder_dzien = os.path.join(full_path, data)
                            folder_godzina = os.path.join(folder_dzien, godzina)
                            
                            os.makedirs(folder_godzina, exist_ok=True)
                            os.chown(folder_dzien, uid, gid)
                            os.chown(folder_godzina, uid, gid)

                            src = os.path.join(full_path, nazwa_pliku)
                            dst = os.path.join(folder_godzina, nazwa_pliku)
                            try:
                                shutil.move(src, dst)
                                os.chown(dst, uid, gid)
                            except Exception:
                                pass
        except Exception:
            pass
        time.sleep(5)
