import json
import os
from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored

from tools_def import tools

from chat_functionality import *
from config import *

# separate OpenAI client for tools
client_tools = OpenAI(api_key=APIKEY_OPENAI)

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def ChatGPT_completion_tools(client, messages, tools=None, tool_choice=None, model=GPT_MODEL):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e

def pretty_print_conversation(messages):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }
    
    for message in messages:
        if message["role"] == "system":
            print(colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "user":
            print(colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and message.get("function_call"):
            print(colored(f"assistant: {message['function_call']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and not message.get("function_call"):
            print(colored(f"assistant: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "function":
            print(colored(f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))

def build_prompt_response_tools(conversation):
    
    # the most recemt message is the highest index. remove messages preceeding the most recent assistant message.
    conversation = conversation[::-1]
    for i, message in enumerate(conversation):
        if message["role"] == "assistant":
            conversation = conversation[i::-1]
            break

    completion = []
    completion.append(
        {
            "role": "system",
            "content": (
                "Based on the chat, based on implicit and explcit requests, and based on the information in the chat history,"
                "break down where tools can be used."
                "Based on the content of the conversation,"
                "what information can be used for each tool that is used."
                # "ONLY output the name of the tools that are needed, in order."
                "Multiple tools can be used."
                "The same tool can be used more than once, for example, to generate multiple images;"
                "Or to determine multiple locations, for example, the starting point, current location, and the destination."
                "The output of one tool can provide input to another."
                "Do not ask for clarification if a user request is ambiguous."
            )
        }
    )

    completion.extend(conversation)
    return completion

def demo():
    messages = []
    messages.append(
        {
            "role": "system",
            "content": (
                "Based on the chat, based on the request, based on the information in the chat,"
                "break down where the tool can be used and what available information can be used for each tool."
                # "ONLY output the name of the tools that are needed, in order."
                "Multiple tools can be used."
                "The same tool can be used more than once, for example, to generate multiple images;"
                "Or to determine multiple locations, for example, the starting point, current location, and the destination."
                "Be careful of the order in which you use the tools and avoid circular dependencies."
                "The output of one tool can provide input to another."
                "Do not ask for clarification if a user request is ambiguous."
                "Make use of the information that's available in the chat history."
            )
        }
    )
    messages.append(
        {
            "role": "user",
            "content":
            (
                "The last notable landmark was the skateboarding ramp by Parry Sound's famous railway bridge, 5 days ago,"
                "Then I got lost in nearby woods heading approximately north west."
                "I can't carry everything that I have with me so I have to decide what to keep based on weather."
                "I've been wandering for 5 days and really want to find my way home."
                "Jane Doe is also lost. She says that she can see the CN tower about 50km's to the South."
            )
        }
    )

    chat_response = ChatGPT_completion_tools(
        client_tools, messages, tools=tools
    )
    assistant_message = chat_response.choices[0].message
    messages.append(assistant_message)

    tool_calls = assistant_message.tool_calls
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        print(f"\nFunction: {function_name}\nArguments: {function_args}\n")

    

    print(assistant_message)

def generate_image(client, **kwargs):
    try:
        model = kwargs.get('model', 'dall-e-3')  # Default to 'dall-e-3' if not provided
        prompt = kwargs.get('description', '')  # Default to empty string if not provided
        size = kwargs.get('size', '1024x1024')  # Default to '1024x1024' if not provided
        quality = kwargs.get('quality', 'standard')  # Default to 'standard' if not provided
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size='1024x1024',
            quality=quality,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion generate_image response")
        print(f"Exception: {e}")
        return e

if __name__ == "__main__":
    demo()




