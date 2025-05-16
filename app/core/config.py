import os
import json
import logging
import sys
import boto3
from dotenv import load_dotenv
from twilio.rest import Client


REGION = os.getenv("AWS_REGION","eu-central-1")
SECRET_NAME = "google_drive_mcp_secrets"

def load_secrets_manager(secret_name):
    client = boto3.client("secretsmanager",region_name=REGION)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

def process_secret(secret_name):
    response = load_secrets_manager(secret_name)
    gcp_oauth_raw = response.get("GCP_OAUTH_KEYS")

    if not gcp_oauth_raw:
        raise KeyError("GCP_OAUTH_KEYS not found in secret")

    # Parse the nested JSON string
    gcp_oauth_parsed = json.loads(gcp_oauth_raw)

    # Write to a clean JSON file
    with open("gcp-oauth.keys.json", "w") as f:
        json.dump(gcp_oauth_parsed, f, indent=2)

    print("Saved to gcp-oauth.keys.json")


def apply_env_vars(env_dict):
    for k,v in env_dict.items():
        os.environ[k] = v

def bootstrap_config():
    try:
        env_secrets = "google_drive_mcp_secrets"
        secrets = load_secrets_manager(env_secrets)
        apply_env_vars(secrets.get("ENV_VARS",{}))
        oauth_secret = "gcp-oauth-keys"
        process_secret(oauth_secret)
    except Exception:
        load_dotenv(override=False)

bootstrap_config()

# Configure logging
def setup_logging():
    environment = os.environ.get('ENVIRONMENT', 'development').lower()

    if environment == 'production':
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG


    logger = logging.getLogger()
    logger.setLevel(log_level)

    logger.handlers = []

    if environment == 'production':
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
        )

    stream_handler = logging.StreamHandler(sys.stdout)

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.info(
        f"Logging initialised in new {environment} environment at {log_level} level"
    )

    return logger

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

GOAUTH_REDIRECT_URL=os.getenv("GOAUTH_REDIRECT_URL", "http://localhost:8000")


# OpenAI
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

MCP_CONFIG = {
    "gdrive": {
        "command": "python3",
        "args": ["app/mcp_servers/gdrive/server/drive_mcp_server.py"],
        "transport": "stdio",
    },
    "gmail": {"command": "npx", "args": ["@gongrzhe/server-gmail-autoauth-mcp"]},
}





