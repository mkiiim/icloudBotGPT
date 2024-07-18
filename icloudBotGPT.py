from libs.imessage_reader import fetch_data

import time
import os
import subprocess

from chat_functionality import *
from tools_use import *
from tools_def import my_tools
from config import *

import re
import json

import imessage


# Get the last processed message ID from a file
def get_last_processed_id(file_path=FILEPATH_LAST_MSG_ID):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                content = file.read().strip()
                if content:
                    return int(content)
    except ValueError:
        pass
    return 0

# Update the last processed message ID in a file
def update_last_processed_id(last_id, file_path=FILEPATH_LAST_MSG_ID):
    with open(file_path, 'w') as file:
        file.write(str(last_id))

def get_new_messages(last_id, limit):
    fs = fetch_data.FetchData(MESSAGE_DB_PATH)
    messages = fs.get_messages()
    new_messages = []
    for message in messages:
        if int(message[7]) > int(last_id):
            new_messages.append(message)
    # Return the last {limit} messages
    return new_messages[-limit:]

def update_response_queue(new_messages):
    # identify the unique groups of message senders / chat groups in the new messages
    # that are not from the assistant and return a list of tuples with the following format:
    # (row_id, is_from_me, handle_id, chat_id)
    # where row_id is the first message of each group of messages from the same conversation

    response_queue = []
    for message in new_messages:
        row_id = message[7]
        is_from_me = message[5]
        handle_id = message[0]
        chat_id = message[6]
        if (handle_id and not chat_id) or (handle_id and chat_id) or (not handle_id and chat_id):
            response_queue.append((row_id, is_from_me, handle_id, chat_id))

    # remove duplicates where key is (handle_id and chat_id)
    seen = {}
    new_response_queue = []
    for item in response_queue[::-1]:
        if (item[2], item[3]) not in seen:
            new_response_queue.append(item)
            seen[(item[2], item[3])] = True
    response_queue = new_response_queue[::-1]

    # remove duplicates where key is (chat_id)
    seen = {}
    new_response_queue = []
    for item in response_queue[::-1]:
        if item[3] not in seen or item[3] is None:
            new_response_queue.append(item)
            seen[item[3]] = True
    response_queue = new_response_queue[::-1]

    # remove any records where is_from_me is 1
    for i in range(len(response_queue)-1, -1, -1):
        if response_queue[i][1] == 1:
            response_queue.pop(i)

    return response_queue

def get_thread_messages(thread, all_messages):
    thread_messages = []
    if thread[3] is None: # If the message is not part of a group chat
        thread_messages = [single_message for single_message in all_messages if ((single_message[0] == thread[2]) and (single_message[6] is None))]
    else: # If the message is part of a group chat
        thread_messages = [single_message for single_message in all_messages if single_message[6] == thread[3]]
    return thread_messages

def get_thread_recipients(message):
    conn = sqlite3.connect(MESSAGE_DB_PATH)
    cursor = conn.cursor()
    
    # Retrieve the chat_id from the chat_message_join table using the constant message ROWID
    cursor.execute("""
        SELECT chat_id 
        FROM chat_message_join 
        WHERE message_id = ?
    """, (message,))
    result = cursor.fetchone()

    if result:
        chat_ROWID = result[0]

        # Execute the query to get handle IDs from the handle table
        cursor.execute("""
            SELECT handle.id 
            FROM chat_handle_join 
            JOIN handle ON chat_handle_join.handle_id = handle.ROWID 
            WHERE chat_handle_join.chat_id = ?
        """, (chat_ROWID,))
        handle_ids = cursor.fetchall()

        # Convert the list of tuples to a list of strings (or whatever type the id is)
        handle_ids_list = [row[0] for row in handle_ids]

        # Print the list of handle IDs
        print(f"\nthread participant(s):\n{handle_ids_list}")
    else:
        print("No chat found for the given message ROWID.")
        # handle_ids_list = []

    # Close the connection
    conn.close()

    return handle_ids_list

def analyze_thread(thread_messages):
    # determine how many contiguous messages at the end of the thread are not from the assistant,
    # order old to new
    last_messages = []
    for i in range(len(thread_messages)-1, -1, -1):
        if thread_messages[i][5] == 0:
            last_messages.append(thread_messages[i])
        else:
            break
    # reorder the list from old to new
    last_messages = last_messages[::-1]

    # determine if there are any messages with attachments in last_messages

    # create a list of message ids from last_messages
    list_of_message_ids = [message[7] for message in last_messages]
    list_of_attachments = get_attachments(list_of_message_ids)

def process_plugins(thread_messages):
    pass

def remove_json_like_objects(text):
    # Regular expression pattern to match `{"` followed by any characters (non-greedy) and ending with `"}`.
    # The pattern uses `\"` to match double quotes literally and `.*?` for non-greedy matching of any characters.
    pattern = r'\{\".*?"\}'
    
    # Use re.sub() to replace all occurrences of the pattern with an empty string.
    modified_text = re.sub(pattern, '', text)
    
    return modified_text


# check for macOS version to determine whether to use AppleScript or Shortcuts
def check_macos_version():
    version = os.system("sw_vers -productVersion")
    if version >= 12:
        return True
    else:
        return False

# AppleScript to send an iMessage
def send_via_applescript(phone_number, message):
    subprocess.run(["osascript", script_path, phone_number, message])

# Send an iMessage using either AppleScript or Shortcuts
def send_imessage(thread_recipients, thread, new_message):
    if check_macos_version:
        imessage.send(thread_recipients, new_message)
    else:
        if thread[3] is None:
            send_via_applescript(thread[2], new_message)

# Main loop
def main():

    last_processed_id = get_last_processed_id()
    prompts = load_prompts('prompts.yaml')
    response_queue_finished = True

    while True:
        try:

            # get the last 1000 messages from the database
            all_messages = []
            all_messages = get_new_messages(1, 1000)

            # get the last 200 new messages from the database (which can be made up of multiple conversations i.e., threads)
            new_messages = get_new_messages(last_processed_id, 200)
            
            # queue of the first message of each thread (i.e., length = how many conversation threads there are)
            response_queue = update_response_queue(new_messages)

            if response_queue_finished == True:
                response_queue_finished = False
            else:
                lines_up = 6  # Number of lines to move up
                print(f"\033[{lines_up}F", end="")

            # telemetry
            timestamp = time.localtime()
            formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", timestamp)
            print(f"\n{formatted_time}")
            print(f"\nall_messages: {len(all_messages)}")
            print(f"new_messages: {len(new_messages)} since last processed message row ID: {last_processed_id}")
            print(f"response_queue: {len(response_queue)}")

            # for each "thread" in the response queue, get a history of relevant messages in the last 1000 messages,
            # build the conversation message object as context from which to get the response from ChatGPT,
            # and send the reply message from ChatGPT out via iMessage
            for thread_index, thread in enumerate(response_queue):

                # get all messsages in the thread
                thread_messages = get_thread_messages(thread, all_messages)  

                # telemetry
                print(f"\nthread: {thread_index+1} of {len(response_queue)}")
                print(f"thread_messages: {len(thread_messages)}")
                # print(f"conversation: {len(conversation)}")      

                # get all recipients in the thread
                thread_recipients = get_thread_recipients(thread_messages[-1][7])        

                # Thread info
                print(f"\nthread info: {thread}")

                # chat client objects - instantiate at the top of program
                client_chat = OpenaiLLMObject()
                # client_chat = AnthropicLLMObject()
    
                # build conversation object for this thread
                client_chat.build_prompt_conversation(thread_messages)

                # Build the prompt to complete the conversation - not for use with assistants
                client_chat.build_prompt_response(prompts['prompt_response'])

                # Uses completion method to get Claude's response to the person's text message
                client_chat_completion = client_chat.completion() # root completion method, but should not need to be used
                new_message = client_chat.new_message

                # Print to console
                print(f"\nResponse from {client_chat.name}:\n{new_message}")

                # Send the response via iMessage
                send_imessage(thread_recipients, thread, remove_json_like_objects(new_message))

                # tools client objects - instantiate at the top of program
                client_tools = OpenaiLLMObject(tools=my_tools)
                # client_tools = AnthropicLLMObject(tools=my_tools)

                client_tools.build_prompt_conversation(thread_messages)
                client_tools.build_prompt_response_tools(prompts['prompt_response_tools'])
                
                # Tools
                client_tools_completion = client_tools.completion(tools=my_tools) 
                print(f"\nResponse from {client_tools.name} message:\n{client_tools.tool_messages}")
                print(json.dumps(client_tools.tool_calls, indent = 4)) if client_tools.tool_calls else None
                
                # Process the tool calls - clear responses
                new_message_image = None
                
                # Process the tool calls
                if client_tools.tool_calls:
                    print(f"\nResponse of {client_tools.name} Tool calls.\nNo. of calls: {len(client_tools.tool_calls)}")
                    for i, tool in enumerate(client_tools.tool_calls):
                        function_name = tool['name']
                        function_args = tool['arguments']                
                        print(f"\nFunction {i+1}: {function_name}")
                        print(json.dumps(function_args, indent=4))

                        # Tool actions go here - only generate_image for now.
                        if function_name == "generate_image":
                            
                            # image client objects - instantiate at the top of program
                            client_image = OpenaiDalleObject()
                            
                            client_image_completion = client_image.completion(**function_args)
                            new_message_image = client_image_completion.data[0].url

                            # delete the instance of the client_image
                            del client_image

                        else:
                            pass

                # Send the Image URL via iMessage
                if new_message_image:
                    print(f"Response Image: {new_message_image}")
                    send_imessage(thread_recipients, thread, new_message_image)

                # Update the last processed message ID
                last_processed_id = thread[0]
                update_last_processed_id(last_processed_id)

                # delete the instance of the client_chat and client_tools
                del client_chat
                del client_tools

                response_queue_finished = True

            # Wait for a specified interval before checking for new messages
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()