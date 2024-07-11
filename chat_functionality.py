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

# OpenAI client for chat
# client_chat = OpenAI(api_key=APIKEY_OPENAI)

# Change model and parameters as needed
# Going forward, create a LLM completion object for each LLMN model you want to use. This will allow you to use multiple models in the same script.
class LLMObject(ABC):
    def __init__(self, model_name, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, tools=None):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.uuid = uuid.uuid4()
        if tools is None:
            self.name = f"{__class__.__name__}_{self.uuid}"
            self.tools = []
        else:
            self.name = f"{__class__.__name__}_tools_{self.uuid}"
            self.tools = tools

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

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def completion(self, for_completion, tools=None):
        # imessage_id and attachment will be invalid in the message_history object. Remove it.
        for m in for_completion:
            m.pop('imessage_id', None)
            m.pop('attachment', None)

        try:
            print(f"\n{self.name}")
            self.response = self.client.chat.completions.create(
                model=self.model_name,
                messages=for_completion,
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

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def completion(self, for_completion, tools=None):
        # imessage_id and attachment will be invalid in the message_history object. Remove it.
        for m in for_completion:
            m.pop('imessage_id', None)
            m.pop('attachment', None)

        # System prompt is top level system parameter
        system = for_completion[0]['content']
        for_completion = for_completion[1:]

        # first message must be the role of the user
        while for_completion[0]['role'] != 'user':
            for_completion = for_completion[1:]

       # remove consecutive roles of the same type by concatenating the messages and then removing the prior message
        for i in range(1, len(for_completion)):
            if for_completion[i]['role'] == for_completion[i-1]['role']:
                for_completion[i]['content'] = for_completion[i-1]['content'] + "\n" + for_completion[i]['content']
                for_completion[i-1]['content'] = ''

        # remove empty messages
        for_completion = [m for m in for_completion if m['content'] != '']

        # tools stuff
        if tools is None: 
            tools = []
        else:
            tools = transform_tools(tools, transform_function_toAnthropic)

        try:
            print(f"\n{self.name}")
            self.response = self.client.messages.create(
                model=self.model_name,
                messages=for_completion,
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
    completion = []
    completion.append({"role": "assistant", "content": system_prompt})
    completion.extend(conversation)
    return completion

def build_prompt_response(conversation, system_prompt="You are a helpful assistant. Provide a response to the user(s)."):
    completion = []
    completion.append({"role": "system", "content": system_prompt})
    completion.extend(conversation)
    return completion

def build_prompt_analysis(conversation, system_prompt="Analyze the message thread but do not generate a response to the user. Generate only the analysis."):
    completion = []
    completion.append({"role": "assistant", "content": system_prompt})
    completion.extend(conversation)
    return completion

