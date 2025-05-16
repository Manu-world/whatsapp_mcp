import os
import boto3
import json
import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://mail.google.com/"
]
REGION = "eu-central-1"
SECRET_NAME = "google_drive_mcp_secrets"
CREDENTIALS_FILENAME = "credentials.json"
CREDENTIALS_BACKUP_DIR = os.path.expanduser("~/.gmail-mcp")
CREDENTIALS_BACKUP_PATH = os.path.join(CREDENTIALS_BACKUP_DIR, CREDENTIALS_FILENAME)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------- Helper Functions ----------

def load_secrets():
    try:
        client = boto3.client("secretsmanager", region_name=REGION)
        response = client.get_secret_value(SecretId=SECRET_NAME)
        secret_dict = json.loads(response["SecretString"])
        for key, val in secret_dict.get("ENV_VARS", {}).items():
            os.environ[key] = val
        return secret_dict
    except Exception as e:
        logger.warning(f"Failed to load secrets from AWS: {str(e)}")
        return None

def save_credentials_json(creds: Credentials, path: str):
    with open(path, 'w') as token_file:
        token_file.write(creds.to_json())
    logger.info(f"Credentials saved to {path}")

def save_user_credentials(creds: Credentials, user_number="1234"):
    # user_filename = f"{user_number}.multi.json"
    # save_credentials_json(creds, user_filename)
    add_active_user(user_number)

def backup_credentials(creds: Credentials):
    os.makedirs(CREDENTIALS_BACKUP_DIR, exist_ok=True)
    save_credentials_json(creds, CREDENTIALS_BACKUP_PATH)

# ---------- Auth Flow Logic ----------

def get_drive_service(user_number="undefined"):
    try:
        service = get_production_drive_service(user_number)
        logger.info("✅ Authenticated via production credentials")
        return service
    except Exception as e:
        logger.warning(f"Prod auth failed: {str(e)}")
        logger.info("⚠️ Falling back to local auth")
        try:
            return get_local_drive_service(user_number)
        except Exception as local_e:
            logger.error(f"Local auth also failed: {str(local_e)}")
            raise Exception("🔥 All authentication methods failed") from local_e

def get_production_drive_service(user_number):
    SECRETS = load_secrets()
    if not SECRETS:
        raise Exception("❌ Failed to load secrets from AWS Secrets Manager")

    creds = None
    if 'token_json' in SECRETS:
        creds = Credentials.from_authorized_user_info(json.loads(SECRETS['token_json']), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cred_data = SECRETS['credentials_json']
            cred_str = json.dumps(cred_data) if isinstance(cred_data, dict) else cred_data

            temp_cred_path = 'temp_credentials.json'
            with open(temp_cred_path, 'w') as f:
                f.write(cred_str)

            try:
                flow = InstalledAppFlow.from_client_secrets_file(temp_cred_path, SCOPES)
                creds = flow.run_local_server(port=0)
            finally:
                os.remove(temp_cred_path)

        # Save updated token to AWS
        SECRETS['token_json'] = creds.to_json()
        boto3.client("secretsmanager", region_name=REGION).update_secret(
            SecretId=SECRET_NAME,
            SecretString=json.dumps(SECRETS)
        )

    # Also save locally for debugging/ops
    save_credentials_json(creds, CREDENTIALS_FILENAME)
    save_user_credentials(creds, user_number)
    backup_credentials(creds)

    return build('drive', 'v3', credentials=creds)

def get_local_drive_service(user_number):
    creds = None

    if os.path.exists(CREDENTIALS_FILENAME):
        with open(CREDENTIALS_FILENAME, 'r') as token_file:
            creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('gcp-oauth.keys.json'):
                raise FileNotFoundError("Missing 'gcp-oauth.keys.json' for local auth.")
            flow = InstalledAppFlow.from_client_secrets_file('gcp-oauth.keys.json', SCOPES)
            creds = flow.run_local_server(port=0)

        save_credentials_json(creds, CREDENTIALS_FILENAME)
        save_user_credentials(creds, user_number)
        backup_credentials(creds)

    return build('drive', 'v3', credentials=creds)

def is_production_environment():
    return os.environ.get('ENVIRONMENT', 'development').lower() == 'production'




# ---------- Active User Tracking ----------
def add_active_user(user_number: str):
    user_number = user_number.strip().replace("+", "")
    try:
        # # Prevent duplicates
        # if not is_user_active(user_number):
            with open("active_user.txt", 'w') as f:
                f.write(f"{user_number}\n")
            logger.info(f"Added active user: {user_number}")
        # else:
        #     logger.debug(f"User {user_number} already in active list.")
    except Exception as e:
        logger.error(f"Failed to add active user {user_number}: {e}")

def is_user_active(user_number: str) -> bool:
    user_number = user_number.strip().replace("+", "")
    try:
        with open("active_user.txt", 'r') as f:
            active_users = {line.strip() for line in f if line.strip()}
        return user_number in active_users
    except Exception as e:
        logger.error(f"Failed to check active user {user_number}: {e}")
        return False

# print("is user active:", is_user_active("23354105547"))
# def main():
#     message_payload={"message": "hey hi", "number": "33541055472"}
    
#     is_authenticated=check_and_clean_files(user_number=message_payload.get("number"))
#     print(is_authenticated, ":is authenticated")
#     if not is_authenticated:
#         get_drive_service(user_number=message_payload.get("number"))
#         return
        
#     print(message_payload.get("message", "empty"))
#     return message_payload.get("message", "empty")


# main()