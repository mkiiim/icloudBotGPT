import openai
import os

APIKEY_OPENAI = os.getenv('APIKEY_OPENAI')
openai.api_key = APIKEY_OPENAI

DB_PATH = f"/Users/{os.getenv('USER')}/Library/Messages/chat.db"
PROMPTS_FILE = f"/Users/{os.getenv('USER')}/Projects/cloudBotGPT/prompts.yml"

# File to store last message processed
FILEPATH_LAST_MSG_ID = f"/Users/{os.getenv('USER')}/Projects/cloudBotGPT/last_msg_ID"

# Add a path to the directory where send_imessage.scpt is stored. This is most likely in the same directory as the rest of the downloaded files
# script_path = "/Path/to/directory/send_iMessage.scpt"
script_path = f"/Users/{os.getenv('USER')}/Projects/cloudBotGPT/send_iMessage.scpt"

# Change to False if you want the program to automatically send text messages without you looking it over
# require_approval = True
require_approval = False

# Paste the phone number you want to text with here as a string!
phone_number = "+11234567890"

# Paste the email you want to text with here as a string!
BOT_EMAIL = "cloudBotGPT@icloud.com"  # Replace with the bot's iCloud email address

# Define the check interval (in seconds) to check for new messages
CHECK_INTERVAL = 10