from openai import OpenAI
from config import *
import yaml

client = OpenAI(APIKEY_OPENAI)

# Change "model" to whatever your desired model is. Such as GPT-4 if available
# Adjust temperature to either increase or decrease the randomness of ChatGPT's responses. 0.0-2.0
# Adjust max_tokens to increase or decrease the length of responses

#Going forward, create a LLM completion object for each LLMN model you want to use. This will allow you to use multiple models in the same script.
def ChatGPT_completion(conversation):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=1000,
        temperature=0.2)
        
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

