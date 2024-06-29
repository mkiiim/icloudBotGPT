from libs.imessage_reader import fetch_data
import sqlite3
import time
import os
import subprocess
import base64

from chat_functionality import *
from tools_use import *
from tools_def import tools
from config import *

import re
import json

import imessage

from heic2png import HEIC2PNG
from PIL import Image

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
    """ identify the unique groups of message senders / chat groups in the new messages
        that are not from the assistant and return a list of tuples with the following format:
        (row_id, is_from_me, handle_id, chat_id)
        where row_id is the first message of each group of messages from the same conversation
    """
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
        print(handle_ids_list)
    else:
        print("No chat found for the given message ROWID.")
        # handle_ids_list = []

    # Close the connection
    conn.close()

    return handle_ids_list

def build_prompt_conversation(thread_messages):
    
    conversation = []

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
            conversation.append(conversation_message)
        
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
                content_attachments = process_attachments(thread_message)
                content_all = content_text + content_attachments if content_attachments else content_text

            # conversation
            conversation_message = {
                "role": "user",
                "content": content_all
            }
            conversation.append(conversation_message) 
            
    return conversation

def process_attachments(thread_message):
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
        attachment = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{attachment_type};base64,{attachment_encode}"
            }
        }
        content_attachments.append(attachment)
        print(f"Attachment file processed: {attachment_filename}\n")

    return content_attachments

def get_filename_components(attachment_filename):
    attachment_filename_expanded = os.path.expanduser(attachment_filename)
    attachment_filename_path = os.path.dirname(attachment_filename_expanded)
    attachment_filename_basename = os.path.basename(attachment_filename_expanded)
    attachment_filename_stem = os.path.splitext(attachment_filename_basename)[0]
    attachment_filename_extension = os.path.splitext(attachment_filename_basename)[1]
    return attachment_filename_expanded, attachment_filename_path, attachment_filename_basename, attachment_filename_stem, attachment_filename_extension

def encode_image(image_path):
  full_path = os.path.expanduser(image_path)
  with open(full_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def heic_to_png(heic_file_path):
    attachment_filename_path, attachment_filename_stem = os.path.split(heic_file_path)
    png_file_path = os.path.join(attachment_filename_path, attachment_filename_stem + '.png')
    
    # only if png doesn't already exist
    if not os.path.exists(png_file_path):
        heic2png = HEIC2PNG(heic_file_path, quality=90)
        heic2png.save()
    
    return png_file_path

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
    
def process_plugins(thread_messages):
    pass

import re
import json

import re

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

    while True:
        try:

            # get the last 1000 messages from the database
            all_messages = []
            all_messages = get_new_messages(1, 1000)

            # get the last 200 new messages from the database (which can be made up of multiple conversations i.e., threads)
            new_messages = get_new_messages(last_processed_id, 200)
            
            # queue of the first message of each thread (i.e., length = how many conversation threads there are)
            response_queue = update_response_queue(new_messages)
            
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

                # get all recipients in the thread
                thread_recipients = get_thread_recipients(thread_messages[-1][7])        

                # build conversation object for this thread
                conversation = build_prompt_conversation(thread_messages)

                # telemetry
                print(f"\nthread: {thread_index+1} of {len(response_queue)}")
                print(f"thread_messages: {len(thread_messages)}")
                print(f"conversation: {len(conversation)}")

                # Build the prompt to complete the conversation - not for use with assistants
                # completion_reply = build_prompt_response(conversation, prompts['prompt_response'])
                completion_reply = build_prompt_response(conversation, prompts['prompt_response'])
                completion_reply_tools = build_prompt_response_tools(conversation)

                # Uses completion_reply function to get ChatGPT response to the person's text message
                new_message = ChatGPT_completion(client_chat, completion_reply)

                # Print to console
                print(f"Thread info: {thread}")
                print(f"Response: {new_message}")

                # Send the response via iMessage
                send_imessage(thread_recipients, thread, remove_json_like_objects(new_message))

                # invoke tools functions
                tools_message = ChatGPT_completion_tools(client_tools, completion_reply_tools, tools)  
                tool_calls = tools_message.choices[0].message.tool_calls

                # Process the tool calls
                new_message_image = None
                if tool_calls:
                    print(f"\nReponse of Tool calls. No. of calls: {len(tool_calls)}")
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)                    

                        if function_name == "generate_image":
                            response_generate_image = generate_image(client_tools, **function_args)
                            new_message_image = response_generate_image.data[0].url
                        else:
                            # For now, just print
                            print (f"\nFunction: {function_name}\nArguments: {function_args}\n")

                        # # If the function returns a response, append it to the completion_reply
                        # function_response = function_name(
                        #     **function_args
                        # )
                        # if function_response:
                        #     completion_reply.append(
                        #         {
                        #             "role": "tool",
                        #             "tool_call_id": tool_call.id,
                        #             "name": function_name,
                        #             "content": function_response
                        #         }
                        #     )

                # # Print to console
                # print(f"Thread info: {thread}")
                # print(f"Response: {new_message}")

                # # Send the response via iMessage
                # send_imessage(thread_recipients, thread, new_message)

                if new_message_image:
                    print(f"Response Image: {new_message_image}")
                    send_imessage(thread_recipients, thread, new_message_image)

                # Update the last processed message ID
                last_processed_id = thread[0]
                update_last_processed_id(last_processed_id)

            # Wait for a specified interval before checking for new messages
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()