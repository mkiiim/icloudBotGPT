import openai
import anthropic
import os
import json

# *Your* username, the one to which this bot will be subservient
# This user will need to have an account on the same machine as the bot
# in order to more easily facilitate access the documents and application data
# (e.g. calendars, notes, etc.) for this user. This will more easily
# allow for "personalized context" that the bot can use to generate more
# relevant responses.
USERNAME = "<your_username>"

# OpenAI
APIKEY_OPENAI = os.getenv('APIKEY_OPENAI')
GPT_MODEL = "gpt-4o"
DALL_E_MODEL = "dall-e-3"
EMBEDDING_ENGINE = "text-embedding-ada-002"
EMBEDDING_DIMENSION = 1536
MAX_TOKENS_PER_FILE = 128

# Anthropic
APIKEY_ANTHROPIC = os.getenv('APIKEY_ANTHROPIC')
ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"

# LLMObject
MAX_TOKENS = 1000
TEMPERATURE = 0.2

# Path to the iMessage database
MESSAGE_DB_PATH = f"/Users/{os.getenv('USER')}/Library/Messages/chat.db"
PROMPTS_FILE = f"/Users/{os.getenv('USER')}/Projects/icloudBotGPT/prompts.yml"

# File to store last message processed
FILEPATH_LAST_MSG_ID = f"/Users/{os.getenv('USER')}/Projects/icloudBotGPT/last_msg_ID"

# Path to send_imessage.scpt
script_path = f"/Users/{os.getenv('USER')}/Projects/icloudBotGPT/send_iMessage.scpt"

# Define the check interval (in seconds) to check for new messages
CHECK_INTERVAL = 10

# Define the limit of messages to process in one go (also defines the context window)
THREAD_MSG_LIMIT = 10

# Use completion for default chat functionality. Set this to true to use beta assistants
USE_ASSISTANT = False

# file size limit for attachments, in bytes
FILE_SIZE_LIMIT = 3 * 1024 * 1024

# Root directory for file access
ROOT_DIR = f"/Users/{os.getenv('USER')}/"