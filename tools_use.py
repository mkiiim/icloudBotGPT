import json
import os
from openai import OpenAI
from termcolor import colored

from tools_def import my_tools

from enum import Enum, auto
from enums_llms import *

from chat_functionality import *
from config import *

def transform_function_toAnthropic(OpenAI_tool):
    new_tool = {
        "name": OpenAI_tool["function"]["name"],
        "description": OpenAI_tool["function"]["description"],
        "input_schema": {
            "type": "object",
            "properties": OpenAI_tool["function"]["parameters"]["properties"],
            "required": OpenAI_tool["function"]["parameters"]["required"],
        }
    }
    return new_tool


def transform_tools(OpenAI_tools, transform_function):
    my_tools_transformed = []

    # Parse the JSON list of OpenAI_tools
    tools_list = OpenAI_tools
    
    # Apply the transformation function to each tool
    for tool in tools_list:
        transformed_tool = transform_function(tool)
        my_tools_transformed.append(transformed_tool)
    
    return my_tools_transformed

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

    client_chat = AnthropicLLMObject()
    client_chat_completion = client_chat.completion(messages)
    assistant_message = client_chat_completion
    messages.append(
        {'role': 'assistant', 'content': assistant_message}
        )

    client_tools = OpenaiLLMObject()
    client_tools_completion = client_tools.completion(messages, tools=my_tools)
    assistant_tools = client_tools_completion.message.tool_calls

    tool_calls = assistant_tools
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




