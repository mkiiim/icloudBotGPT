from openai import OpenAI
from anthropic import Anthropic
from config import *
from tools_use import *
import time
import uuid
import yaml
import httpx
from tenacity import retry, wait_random_exponential, stop_after_attempt

from abc import ABC, abstractmethod

from enum import Enum, auto
from enums_llms import *

import sqlite3

import base64
from heic2png import HEIC2PNG
from PIL import Image


# Change model and parameters as needed
# Going forward, create a LLM completion object for each LLMN model you want to use. This will allow you to use multiple models in the same script.
class LLMObject(ABC):
    def __init__(self, model_name, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, tools=None):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.conversation = []

        self.uuid = uuid.uuid4()
        if tools is None:
            self.name = f"{__class__.__name__}_{self.uuid}"
            self.tools = []
        else:
            self.name = f"{__class__.__name__}_tools_{self.uuid}"
            self.tools = tools

    def build_prompt_conversation(self, thread_messages):
        self.conversation = []

        # Because of ChatGPT's limit on the amount of content you upload, this only retrieves the last {THREAD_MSG_LIMIT} text messages sent between you and a recipient
        message_quant = len(thread_messages)

        # determine the range messages to process
        # if the conversation history between you and the recipient is less than {THREAD_MSG_LIMIT}, then it just uploads the entire thing
        messages_to_process = thread_messages if message_quant <= THREAD_MSG_LIMIT else thread_messages[-THREAD_MSG_LIMIT:]

        for thread_message in messages_to_process:
            if thread_message[5]:
                conversation_message = {
                    "role": "assistant",
                    "content": thread_message[1]
                }
                self.conversation.append(conversation_message)
            
            else:    
                # content - text for this thread_message
                content_text = []
                text_message = {
                    "type": "text",
                    "text": f"{thread_message[0]} says:{thread_message[1]}"
                }
                content_text.append(text_message)
                content_all = content_text

                # content - attachments for this thread_message
                content_attachments = []
                if thread_message[8]:
                    content_attachments = self.process_attachments(thread_message)
                    content_all = content_text + content_attachments if content_attachments else content_text

                # conversation
                conversation_message = {
                    "role": "user",
                    "content": content_all
                }
                self.conversation.append(conversation_message) 
                
        return self.conversation

    def build_prompt_response(self, system_prompt="You are a helpful assistant. Provide a response to the user(s)."):
        updated_conversation = []
        updated_conversation.append(
            {
                "role": "system",
                "content": system_prompt
            }
        )
        updated_conversation.extend(self.conversation)
        self.conversation = updated_conversation

    def build_prompt_response_tools(self, system_prompt="Analyze the message thread but do not generate a response to the user. Generate only the analysis."):
        
        # the most recemt message is the highest index. remove messages preceeding the most recent assistant message.
        tools_conversation = self.conversation
        tools_conversation = tools_conversation[::-1]
        for i, message in enumerate(tools_conversation):
            if message["role"] == "assistant":
                tools_conversation = tools_conversation[i::-1]
                break

        updated_conversation_tools = []
        updated_conversation_tools.append(
            {
                "role": "system",
                "content": system_prompt
            }
        )

        updated_conversation_tools.extend(tools_conversation)
        self.conversation = updated_conversation_tools

    def process_attachments(self, thread_message):
        content_attachments = []
        attachments = get_attachments(list_of_message_ids=[thread_message[7]]) # only passing the one message ID
        for attachment in attachments:

            # retrieve attachment filename from the record
            attachment_filename = attachment[2]
            attachment_filename_expanded, attachment_filename_path, attachment_filename_basename, attachment_filename_stem, attachment_filename_extension = get_filename_components(attachment_filename)

            print(f"\nAttachment filename: {attachment_filename}")

            # check if file exists
            if not os.path.exists(attachment_filename_expanded):
                print(f"Attachment file does not exist: {attachment_filename}")
                continue

            # convert HEIC to PNG if necessary
            if attachment_filename_extension.lower() == '.heic':
                attachment_filename = heic_to_png(attachment_filename_expanded)
            attachment_filename_expanded, attachment_filename_path, attachment_filename_basename, attachment_filename_stem, attachment_filename_extension = get_filename_components(attachment_filename)

            # check valid file type
            if attachment_filename_extension.lower() not in ['.png', '.jpg', '.jpeg', '.gif']:
                print(f"Attachment file is not a valid image: {attachment_filename_extension}")
                continue

            # check and resize file if necessary
            attachment_filename = resize_file_to_fit(attachment_filename_expanded)
            attachment_filename_expanded, attachment_filename_path, attachment_filename_basename, attachment_filename_stem, attachment_filename_extension = get_filename_components(attachment_filename)

            # convert image to base64
            attachment_encode = encode_image(attachment_filename)
            attachment_type = attachment_filename.split('.')[-1]
            
            # call the format_attachment method (specific to the LLMObject provider class)
            attachment = self.format_attachment(attachment_type, attachment_encode)
            
            content_attachments.append(attachment)
            print(f"Attachment file processed: {attachment_filename}\n")

        return content_attachments

    @abstractmethod
    def format_attachment(self, attachment_type, attachment_encode):
        pass

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    @abstractmethod
    def completion(self, for_completion):
        pass

class OpenaiLLMObject(LLMObject):
    def __init__(self, model_name=GPT_MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, tools=None):
        super().__init__(model_name, max_tokens, temperature, tools)
        self.client = OpenAI(api_key=APIKEY_OPENAI)

        self.uuid = uuid.uuid4()
        if tools is None:
            self.name = f"{__class__.__name__}_{self.uuid}"
            self.tools = []
        else:
            self.name = f"{__class__.__name__}_tools_{self.uuid}"
            self.tools = tools

    def format_attachment(self, attachment_type, attachment_encode):
        formatted_attachment = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{attachment_type};base64,{attachment_encode}"
            }
        }
        return formatted_attachment

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def completion(self, tools=None):
        # imessage_id and attachment will be invalid in the message_history object. Remove it.
        for m in self.conversation:
            m.pop('imessage_id', None)
            m.pop('attachment', None)

        try:
            print(f"\n{self.name}")
            self.response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.conversation,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                tools=tools,
                # tool_choice=tool_choice,
                )
            
            print(f"{self.response.usage}")
            return self.response
        except openai.APIError as e:
            #Handle API error here, e.g. retry or log
            print(f"OpenAI API returned an API Error: {e}")
            pass
        except openai.APIConnectionError as e:
            #Handle connection error here
            print(f"Failed to connect to OpenAI API: {e}")
            pass
        except openai.RateLimitError as e:
            #Handle rate limit error (we recommend using exponential backoff)
            print(f"OpenAI API request exceeded rate limit: {e}")
            pass
        except Exception as e:
            # Handle unexpected errors
            print(f"An unexpected OpenAI error occurred: {e}")
            # Optionally, return None or a custom message indicating failure
            return None


class AnthropicLLMObject(LLMObject):
    def __init__(self, model_name=ANTHROPIC_MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, tools=None):
        super().__init__(model_name, max_tokens, temperature, tools)
        self.client = Anthropic(api_key=APIKEY_ANTHROPIC)

        self.uuid = uuid.uuid4()
        if tools is None:
            self.name = f"{__class__.__name__}_{self.uuid}"
            self.tools = []
        else:
            self.name = f"{__class__.__name__}_tools_{self.uuid}"
            self.tools = tools

    def format_attachment(self, attachment_type, attachment_encode):
        formatted_attachment = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": f"image/{attachment_type}",
                "data": attachment_encode
            }
        }
        return formatted_attachment

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def completion(self, tools=None):
        # imessage_id and attachment will be invalid in the message_history object. Remove it.
        for m in self.conversation:
            m.pop('imessage_id', None)
            m.pop('attachment', None)

        # System prompt must be top level parameter
        system = self.conversation[0]['content']
        self.conversation = self.conversation[1:]

        # First message must be the role of the user
        while self.conversation[0]['role'] != 'user':
            self.conversation = self.conversation[1:]

       # remove consecutive roles of the same type by concatenating the messages and then removing the prior message
        for i in range(1, len(self.conversation)):
            if self.conversation[i]['role'] == self.conversation[i-1]['role']:
                if self.conversation[i]['role'] == 'user':
                    self.conversation[i]['content'][0]['text'] = self.conversation[i-1]['content'][0]['text'] + "\n" + self.conversation[i]['content'][0]['text']
                else:
                    self.conversation[i]['content'] = self.conversation[i-1]['content'] + "\n" + self.conversation[i]['content']
                self.conversation[i-1]['content'] = ''

        # remove empty messages
        self.conversation = [m for m in self.conversation if m['content'] != '']

        # tools stuff
        if tools is None: 
            tools = []
        else:
            tools = transform_tools(tools, transform_function_toAnthropic)

        try:
            print(f"\n{self.name}")
            self.response = self.client.messages.create(
                model=self.model_name,
                messages=self.conversation,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system = system,
                tools=tools,
                )
            
            print(f"{self.response.usage}")
            return self.response
        except anthropic.APIError as e:
            #Handle API error here, e.g. retry or log
            print(f"Anthropic API returned an API Error: {e}")
            pass
        except anthropic.APIConnectionError as e:
            #Handle connection error here
            print(f"Failed to connect to Anthropic API: {e}")
            pass
        except anthropic.RateLimitError as e:
            #Handle rate limit error (we recommend using exponential backoff)
            print(f"Anthropic API request exceeded rate limit: {e}")
            pass
        except Exception as e:
            # Handle unexpected errors
            print(f"An unexpected Anthropic error occurred: {e}")
            # Optionally, return None or a custom message indicating failure
            return None

class OpenaiDalleObject():
    def __init__(self, model_name="dall-e-3", description = "", size = "1024x1024", quality = "standard"):
        
        self.client = OpenAI(api_key=APIKEY_OPENAI)
        
        self.model_name = model_name
        self.description = description
        self.size = size
        self.quality = quality
        
        self.uuid = uuid.uuid4()
        self.name = f"{__class__.__name__}_{self.uuid}"
        
    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def completion(self, **kwargs):

        self.model = kwargs.get('model', 'dall-e-3')  # Default to 'dall-e-3' if not provided
        self.prompt = kwargs.get('description', '')  # Default to empty string if not provided
        self.size = kwargs.get('size', '1024x1024')  # Default to '1024x1024' if not provided
        self.size = '1024x1024'
        self.quality = kwargs.get('quality', 'standard')  # Default to 'standard' if not provided

        try:
            print(f"\n{self.name}")
            self.response = self.client.images.generate(
                model=self.model_name,
                prompt = self.prompt,
                size = self.size,
                quality = self.quality
            )
            
            # print(f"{self.response.usage}")
            return self.response
        except openai.APIError as e:
            #Handle API error here, e.g. retry or log
            print(f"OpenAI API returned an API Error: {e}")
            pass
        except openai.APIConnectionError as e:
            #Handle connection error here
            print(f"Failed to connect to OpenAI API: {e}")
            pass
        except openai.RateLimitError as e:
            #Handle rate limit error (we recommend using exponential backoff)
            print(f"OpenAI API request exceeded rate limit: {e}")
            pass
        except Exception as e:
            # Handle unexpected errors
            print(f"An unexpected OpenAI error occurred: {e}")
            # Optionally, return None or a custom message indicating failure
            return None


# def ChatGPT_assistant(prompt_instructions, message_history):
#     assistant = client_chat.beta.assistants.create(
#         model="gpt-4o",
#         name = "{os.getenv('USER')}_assistant",
#         instructions = prompt_instructions,
#         # max_tokens=1000,
#         temperature=0.2)
    
#     # NOTE that message_history is 0-indexed oldest to newest, but when messages are retrieved
#     # from client.beta.threads.messages.list, they are 0-indexed newest to oldest

#     # imessage_id and attachment will be invalid in the message_history object. Remove it.
#     for m in message_history:
#         m.pop('imessage_id', None)
#         m.pop('attachment', None)
    
#     # create thread object
#     thread = client_chat.beta.threads.create(
#         messages=message_history,
#     )

#     # create the run object
#     run = client_chat.beta.threads.runs.create(
#         thread_id = thread.id,
#         assistant_id = assistant.id,
#         model="gpt-4o",
#     )

#     # check for run completion in a loop. *** TODO *** Need to account for cancelled_at and failed_at
#     while run.completed_at is None:
#         run = client_chat.beta.threads.runs.retrieve(
#             run_id=run.id,
#             thread_id=thread.id,
#             # assistant_id=assistant.id
#         )
#         time.sleep(1)

#     # get the reply from threads.messages.list
#     reply = client_chat.beta.threads.messages.list(
#         thread_id=thread.id,
#     )

#     return reply.data[0].content[0].text.value

def load_prompts(file_path):
    with open(file_path, 'r') as file:
        prompts = yaml.safe_load(file)
    return prompts['prompts']

def build_prompt(conversation, system_prompt="You are a helpful assistant. Provide a response to the user(s)."):
    updated_conversation = []
    updated_conversation.append({"role": "assistant", "content": system_prompt})
    updated_conversation.extend(conversation)
    return updated_conversation

def build_prompt_analysis(conversation, system_prompt="Analyze the message thread but do not generate a response to the user. Generate only the analysis."):
    updated_conversation = []
    updated_conversation.append({"role": "assistant", "content": system_prompt})
    updated_conversation.extend(conversation)
    return updated_conversation

def get_attachments(list_of_message_ids) -> list:

    # build the SQL query
    placeholders = ', '.join('?' for _ in list_of_message_ids)
    sql_query = (
        "SELECT "
        "message_attachment_join.message_id, "
        "message_attachment_join.attachment_id, "
        "attachment.filename "
        "FROM attachment "
        "JOIN message_attachment_join ON attachment.ROWID = message_attachment_join.attachment_id "
        f"WHERE message_attachment_join.message_id IN ({placeholders})"
    )

    conn = sqlite3.connect(MESSAGE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql_query, list_of_message_ids)
    results = cursor.fetchall()
    conn.close()

    return results


def get_filename_components(attachment_filename):
    attachment_filename_expanded = os.path.expanduser(attachment_filename)
    attachment_filename_path = os.path.dirname(attachment_filename_expanded)
    attachment_filename_basename = os.path.basename(attachment_filename_expanded)
    attachment_filename_stem = os.path.splitext(attachment_filename_basename)[0]
    attachment_filename_extension = os.path.splitext(attachment_filename_basename)[1]
    return attachment_filename_expanded, attachment_filename_path, attachment_filename_basename, attachment_filename_stem, attachment_filename_extension

def heic_to_png(heic_file_path):
    attachment_filename_path, attachment_filename_stem = os.path.split(heic_file_path)
    png_file_path = os.path.join(attachment_filename_path, attachment_filename_stem + '.png')
    
    # only if png doesn't already exist
    if not os.path.exists(png_file_path):
        heic2png = HEIC2PNG(heic_file_path, quality=90)
        heic2png.save()
    
    return png_file_path

def encode_image(image_path):
  full_path = os.path.expanduser(image_path)
  with open(full_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def resize_file_to_fit(file_path, size_limit = FILE_SIZE_LIMIT):
    # Decompose file path into components
    attachment_filename_expanded, attachment_filename_path, attachment_filename_basename, attachment_filename_stem, attachment_filename_extension = get_filename_components(file_path)
    
    # Check file size
    file_size = os.path.getsize(file_path)
    attachment_filename_resized = attachment_filename_path + '/' + attachment_filename_stem + '_resized_for_AI' + attachment_filename_extension
    image = Image.open(file_path)

    # Check if resized_for_AI file already exists
    if os.path.exists(attachment_filename_resized) and os.path.getsize(attachment_filename_resized) < size_limit:
        return attachment_filename_resized

    # keep resizing until file size is within limit
    while file_size > size_limit:
        print(f"Attachment file is too large: {file_size} bytes, resizing ...")
        
        # Resize as ratio of actual file_size to size_limit
        resize_ratio = size_limit / file_size
        original_width, original_height = image.size
        new_width = int(original_width * resize_ratio)
        new_height = int(original_height * resize_ratio)
        resized_image = image.resize((new_width, new_height))
        resized_image.save(attachment_filename_resized)
        file_size = os.path.getsize(attachment_filename_resized)
        image = Image.open(attachment_filename_resized)

        # Update file_path to point to the resized file
        file_path = attachment_filename_resized

        print(f"Attachment file resized to: {file_size} bytes")
    return file_path