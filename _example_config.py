import openai
import os

# Define you API keys in environment variables and access them here
APIKEY_OPENAI = os.getenv('APIKEY_OPENAI')
openai.api_key = APIKEY_OPENAI

DB_PATH = f"/Users/{os.getenv('USER')}/Library/Messages/chat.db"
PROMPTS_FILE = f"/Users/{os.getenv('USER')}/Projects/icloudBotGPT/prompts.yml"

# File to store last message processed
FILEPATH_LAST_MSG_ID = f"/Users/{os.getenv('USER')}/Projects/icloudBotGPT/last_msg_ID"

# Path to send_imessage.scpt
script_path = f"/Users/{os.getenv('USER')}/Projects/icloudBotGPT/send_iMessage.scpt"

# Define the check interval (in seconds) to check for new messages
CHECK_INTERVAL = 10