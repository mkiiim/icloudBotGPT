from openai import OpenAI
from config import *
import time
import yaml

client = OpenAI(api_key=APIKEY_OPENAI)

# Change model and parameters as needed
# Going forward, create a LLM completion object for each LLMN model you want to use. This will allow you to use multiple models in the same script.
def ChatGPT_completion(prompt_instructions, message_history):
    assistant = client.beta.assistants.create(
        model="gpt-4o",
        name = "{os.getenv('USER')}_assistant",
        instructions = prompt_instructions,
        # max_tokens=1000,
        temperature=0.2)
    
    # imessage_id will be invalid in the message_history object. Remove it.
    for m in message_history:
        m.pop('imessage_id', None)

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
    # completion.append({"role": "assistant", "content": system_prompt})
    completion.extend(conversation)
    return completion

def build_prompt_analysis(conversation, system_prompt="Analyze the message thread but do not generate a response to the user. Generate only the analysis."):
    completion = []
    completion.append({"role": "assistant", "content": system_prompt})
    completion.extend(conversation)
    return completion

