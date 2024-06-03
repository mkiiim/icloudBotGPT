# icloudBotGPT
 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

 ## Purpose
 This little project was borne out of the ongoing inconvenience of having so many individualized apps for chatbots. I had already experimented with creating a web-based (gradio) app and an iOS app through which you could access any API accessible remote or local LLM chatbot. But what that really pointed to was having the convenience of being able to use the already existing iMessage app and interface to chat with the bot, instead of having to navigate to, yet another, separate app or browser tab.

 Further capabilities are under consideration / development, like being able to deal with multi-modal input (in this case, probably through attachments) and also, what I'll describe as, workflow automation like being able to ask the chatbot to know about, act on, and create notes and calendar appointments. And, in the future, potentially opening up the ability for the chatbot to use documents and files local to it (i.e., on the local machine and account's filesystem or cloud filesystems and datastores) for RAG.

 As an experiment and proof of concept it's a success. But ultimately I expect that AI capabilities will be even more seamlessly built into the OSs and apps we already use today such that the need to use a separate app/interface will become less and less common. 

 I find that (application) context switching is one of the last user experience hurdles when it comes to seamlessly integrating computing into our everyday workflow. We have, of course, become use to it as computers have traditionally provided the tools (in the form of applications) that aided us in our day to day activities. But as AI continues to embed itself in applications, OS, and hardware (think CoPilot integrated at the PC hardware and Windows OS level), we'll see an evolution where AI provides integration and glue that blurs the boundaries between the atomic steps which require the use of, and a context switch to, specialized applications/tools. 

 ## How it works
 The program polls the iMessage database at `/Users/{username}/Library/Messages/chat.db` for messages. After some processing of messages into "threads", determining which threads expect a reply, and adding these threads to a "response queue", messages in individual threads are then packaged into a (user configurable) prompt for the chatbot and sent to the chatbot API for completion (a response). Once a completion is received from the chatbot API, it is packaged as a payload which, depending on macOS version, either Shortcut or AppleScript will use in a custom automation as the body of an iMessage reply to the apporopriate party(s) in the thread. This is repeated per thread in the the response queue.

 This project works by dedicating an old spare macmini that I have to host an Apple icloud account through which the chat bot is able to access iMessage.

 Chatting with the bot is possible via the iMessage app that you can find on macOS, iOS, and ipadOS. It is also possible to address the bot on any phone capable of plain SMS messaging, with some limitations, provided you have the luxury to dedicate a mobile network enabled device (i.e., cell phone), cell phone number, and dataplan to the bot. To be clear, a cell phone and plan is not required if operating strictly within an Apple environment and participants.

 Unfortunately, but probably for reasons well understood (i.e., preventing automated spam bot proliferation, privacy and security concerns), public iMessage API's are virtually non-existant. In order for the bot to access iMessage functionality, Shortcuts and/or Applescript automation needs to be leveraged. Shortcuts is only available on macOS 12 (Monterey) or above and enables the fullest functionality (group chats and multi-modal[WIP]).

 The bot can also participate in group chats but this capability requires automation that only Shortcuts can provide. For older macOS versions on which automation is enabled by AppleScript, I've not been able to figure out or find a way to send replies to the whole chat group, just individuals.

 ## Requirements
 - a dedicated mac running macOS (preferrably v12, Monterey or above) signed into an iCloud account. Note: I can confirm that it does work on a macmini 2012 (officially supported only through to v11, Catalina) running Monterey on the bare metal via OpenCoreLegacyPatcher. I have also experimented with a VM on proxmox hyper-visor but ran into the known issues and difficulties with being able to run iMessage on non-bare-metal Apple hardware. YMMV.
 - python (developed on 3.9+)
 - OpenAI API key (in the future I intend to support other chatbots including local LLMs)

 ## Installation - WIP
 ### Hardware
 - ...
 
 ### OS and icloud
 - ...

 ### Automation - AppleScript and Shortcuts
 - ...
 
 ### Python environment
 - ...

 ### Program Configuration
 - ...

 ## Future Features in Progress
 not necessarily in this order:
 - multi-modality
 - OS calendar and notes integration / automation
 - filesystem and datastore RAG
 - async / thread

 ## Acknowledgements
 - [imessage_reader](https://github.com/niftycode/imessage_reader) for providing the library which underpins the method by which iMessage database is accessed. A fork of the repoistory and modifications were made to access some additional tables/fields.
 - [py-imessage-shortcuts](https://github.com/kevinschaich/py-imessage-shortcuts) for the shortcut which enables iMessage automation
