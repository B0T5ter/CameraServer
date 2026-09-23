import os
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
                for current_root, directory_names, file_names in os.walk(ROOT_SAVE_DIR):
                    paths = [current_root]
                    paths.extend(os.path.join(current_root, name) for name in directory_names)
                    paths.extend(os.path.join(current_root, name) for name in file_names)
                    for path in paths:
                        try:
                            os.chown(path, uid, gid)
                        except FileNotFoundError:
                            pass
        except Exception:
            pass
        time.sleep(5)
