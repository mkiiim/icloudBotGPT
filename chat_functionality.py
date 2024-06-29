from openai import OpenAI
from config import *
import time
import yaml
import httpx

# OpenAI client for chat
client_chat = OpenAI(api_key=APIKEY_OPENAI)

# Change model and parameters as needed
# Going forward, create a LLM completion object for each LLMN model you want to use. This will allow you to use multiple models in the same script.

def ChatGPT_completion(client, for_completion):
    # imessage_id and attachment will be invalid in the message_history object. Remove it.
    for m in for_completion:
        m.pop('imessage_id', None)
        m.pop('attachment', None)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=for_completion,
            max_tokens=1000,
            temperature=0.2,
            tools=None)
        # response.raise_for_status()  # Raises an error for 4xx/5xx responses
        return response.choices[0].message.content
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
        print(f"An unexpected error occurred: {e}")
        # Optionally, return None or a custom message indicating failure
        return None

def ChatGPT_assistant(prompt_instructions, message_history):
    assistant = client.beta.assistants.create(
        model="gpt-4o",
        name = "{os.getenv('USER')}_assistant",
        instructions = prompt_instructions,
        # max_tokens=1000,
        temperature=0.2)
    
    # NOTE that message_history is 0-indexed oldest to newest, but when messages are retrieved
    # from client.beta.threads.messages.list, they are 0-indexed newest to oldest

    # imessage_id and attachment will be invalid in the message_history object. Remove it.
    for m in message_history:
        m.pop('imessage_id', None)
        m.pop('attachment', None)
    
    # create thread object
    thread = client.beta.threads.create(
        messages=message_history,
    )

    # create the run object
    run = client.beta.threads.runs.create(
        thread_id = thread.id,
        assistant_id = assistant.id,
        model="gpt-4o",
    )

    # check for run completion in a loop. *** TODO *** Need to account for cancelled_at and failed_at
    while run.completed_at is None:
        run = client.beta.threads.runs.retrieve(
            run_id=run.id,
            thread_id=thread.id,
            # assistant_id=assistant.id
        )
        time.sleep(1)

    # get the reply from threads.messages.list
    reply = client.beta.threads.messages.list(
        thread_id=thread.id,
    )

    return reply.data[0].content[0].text.value

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

