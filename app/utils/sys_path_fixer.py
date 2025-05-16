import sys
import os
import glob
import logging

from app.core.auth import is_user_active

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def fix_sys_path(levels_up=4):
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * levels_up)))



def check_and_clean_files(user_number="12345"):
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

    # Then use that as your base for any file you need
    user_number_ = f'{user_number.replace("+", "")}.json'
    user_file = os.path.join(ROOT_DIR, user_number_)
    credentials_file = os.path.join(ROOT_DIR, 'credentials.json')
    gmail_creds = os.path.join(os.path.expanduser('~'), '.gmail-mcp', 'credentials.json')

    print("Looking for:")
    print("user_file:", user_file)
    print("credentials_file:", credentials_file)


    # was .isfile
    if os.path.exists(credentials_file) and is_user_active(user_number):
        print("user is the current authenticated user..")
        return True


    # Start cleaning up
    def safe_delete(filepath):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError as e:
            logging.warning(f"Failed to delete {filepath}: {e}")

    # Remove all *.multi.json files
    for file in glob.glob(os.path.join(".", '*.multi.json')):
        safe_delete(file)

    # Remove credentials
    safe_delete(credentials_file)
    safe_delete(gmail_creds)

    return False

# print(f"check {check_and_clean_files('233541055472')}")
