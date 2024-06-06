import asyncio
from openai import OpenAI
from config import *
import yaml

client = OpenAI(api_key=APIKEY_OPENAI)

# Change model and parameters as needed
# Going forward, create a LLM completion object for each LLMN model you want to use. This will allow you to use multiple models in the same script.
async def ChatGPT_completion(conversation):
    print(f"*** started completing {str(conversation[0])[:60]}...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=1000,
        temperature=0.7)

    print(f"*** finished completing {str(conversation[0])[:60]}...")        
    return response



def load_prompts(file_path):
    with open(file_path, 'r') as file:
        prompts = yaml.safe_load(file)
    return prompts['prompts']

def build_prompt(conversation, system_prompt="You are a helpful assistant. Provide a response to the user(s)."):
    completion = []
    completion.append({"role": "system", "content": system_prompt})
    completion.extend(conversation)
    return completion

def build_prompt_response(conversation, system_prompt="You are a helpful assistant. Provide a response to the user(s)."):
    completion = []
    completion.append({"role": "system", "content": system_prompt})
    completion.extend(conversation)
    return completion

def build_prompt_analysis(conversation, system_prompt="Analyze the message thread but do not generate a response to the user. Generate only the analysis."):
    completion = []
    completion.append({"role": "system", "content": system_prompt})
    completion.extend(conversation)
    return completion

