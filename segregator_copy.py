import os
import shutil
import time
import pwd
import grp

# Foldery do obserwacji
foldery = [
    "/mnt/dysk/recording/camBrama",
    "/mnt/dysk/recording/camFurtka"
]

# Dane użytkownika
user_name = "filip"
uid = pwd.getpwnam(user_name).pw_uid
gid = grp.getgrnam(user_name).gr_gid

def segreguj():
    for folder in foldery:
        for nazwa_pliku in os.listdir(folder):
            if nazwa_pliku.startswith("motion_") and nazwa_pliku.endswith(".mp4"):
                parts = nazwa_pliku.split("_")
                if len(parts) != 3:
                    continue

                data = parts[1]           # np. 20260201
                godzina = parts[2][:2]    # np. 13 z 132118

                # Tworzymy foldery: dzień/godzina w tym samym katalogu
                folder_dzien = os.path.join(folder, data)
                folder_godzina = os.path.join(folder_dzien, godzina)
                os.makedirs(folder_godzina, exist_ok=True)

                # Ustawiamy właściciela folderu na filip
                os.chown(folder_dzien, uid, gid)
                os.chown(folder_godzina, uid, gid)

                # Przenosimy plik
                src = os.path.join(folder, nazwa_pliku)
                dst = os.path.join(folder_godzina, nazwa_pliku)
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    print(f"Błąd przy przenoszeniu {nazwa_pliku}: {e}")

if __name__ == "__main__":
    while True:
        segreguj()
        time.sleep(5)  # sprawdzaj co 5 sekund
