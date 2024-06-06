from libs.imessage_reader import fetch_data
import sqlite3
import time
import os
import subprocess
# import openai
from chat_functionality import *
from config import *
import imessage


# Setup for OpenAI API key and other constants
# openai.api_key = APIKEY_OPENAI

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
    fs = fetch_data.FetchData(DB_PATH)
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
        (row_id, is_from_me, handle_id, chat_id)"""
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

def build_prompt_conversation(thread_messages):
    
    conversation = []

    # Because of ChatGPT's limit on the amount of content you upload, this only retrieves the last {msg_limit} text messages sent between you and a recipient
    message_quant = len(thread_messages)
    msg_limit = 20
    if message_quant <= msg_limit:
        for message in thread_messages:
            if message[5]:
                conversation.append({"role": "assistant", "content": message[1]})
            else:
                conversation.append({"role": "user", "imessage_id": f"{message[0]}", "content": f"{message[0]} says:{message[1]}"}) # this also adds ID of the sender (important in the case of group chats)
        return conversation
    # if the conversation history between you and the recipient is less than {msg_limit}, then it just uploads the entire thing
    else:
        for message in thread_messages[-(msg_limit)::]:
            if message[5]:
                conversation.append({"role": "assistant", "content": message[1]})
            else:
                conversation.append({"role": "user", "imessage_id": f"{message[0]}", "content": f"{message[0]} says:{message[1]}"}) # this also adds ID of the sender (important in the case of group chats)
        return conversation

def get_thread_messages(thread, new_messages):
    thread_messages = []
    if thread[3] is None: # If the message is not part of a group chat
        thread_messages = [text for text in new_messages if ((text[0] == thread[2]) and (text[6] is None))]
    else: # If the message is part of a group chat
        thread_messages = [text for text in new_messages if text[6] == thread[3]]
    return thread_messages

def get_thread_recipients(message):
    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql_query, list_of_message_ids)
    results = cursor.fetchall()
    conn.close()

    return results
    
def process_plugins(thread_messages):
    pass

# check for macOS version to determine whether to use AppleScript or Shortcuts
def check_macos_version():
    version = os.system("sw_vers -productVersion")
    if version >= 12:
        return True
    else:
        return False

# AppleScript to send an iMessage
def send_imessage(phone_number, message):
    subprocess.run(["osascript", script_path, phone_number, message])

def main():

# Main loop
    last_processed_id = get_last_processed_id()
    prompts = load_prompts('prompts.yaml')

    while True:
        try:

            # get the last 1000 messages from the database
            all_messages = []
            all_messages = get_new_messages(1, 1000)

            # get the last 200 new messages from the database
            new_messages = get_new_messages(last_processed_id, 200)
            
            # how many response queues are there? (i.e., how many different threads are there?)
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
                thread_messages = get_thread_messages(thread, new_messages)        

                # get all recipients in the thread
                thread_recipients = get_thread_recipients(thread_messages[-1][7])        

                # build conversation object for this thread
                conversation = build_prompt_conversation(thread_messages)

                # # analyze the thread
                # thread_instructions = []
                # thread_instructions = analyze_thread(thread_messages)

                # # call the plugins required for this thread
                # conversation = []
                # conversation = process_plugins(thread_messages)

                # telemetry
                print(f"\n\tthread: {thread_index+1} of {len(response_queue)}")
                print(f"\t\tthread_messages: {len(thread_messages)}")
                # print(f"\t\tthread_instructions: {len(thread_instructions)}")
                print(f"\t\tconversation: {len(conversation)}")

                # Build the prompt to develop instructions for replying to the conversation
                # completion_instructions = build_prompt_analysis(conversation, prompts['prompt_analysis'])

                # Uses completion_instructions to get a list of instructional steps ChatGPT would take to respond to the person's text message
                # new_message = completed_assistant(thread_messages[-1][1], conversation)
                # new_instructions = ChatGPT_completion(completion_instructions).choices[0].message.content

                # Build the prompt to complete the conversation
                completion_reply = build_prompt_response(conversation, "")

                # Uses completion_reply function to get ChatGPT response to the person's text message
                # new_message = completed_assistant(thread_messages[-1][1], conversation)
                new_message = ChatGPT_completion(prompts['prompt_response'],completion_reply)

                # Print to console
                print(f"\t\tThread info: {thread}")
                # print(f"\t\t\tResponse: {new_instructions}")
                print(f"\t\t\tResponse: {new_message}")

                # Send the message via Shortcuts - if macOS Monterey 12+                   
                # Send the message via subprocess - if only AppleScript is available
                if check_macos_version:
                    imessage.send(thread_recipients, new_message)
                else:
                    if thread[3] is None:
                        send_imessage(thread[2], new_message)

                # Update the last processed message ID
                last_processed_id = thread[0]
                update_last_processed_id(last_processed_id)

            # Wait for a specified interval before checking for new messages
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()