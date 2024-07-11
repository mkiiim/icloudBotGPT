my_tools = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generates an image or diagram based on the user's need, or the user's request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the image or diagram should be about and should contain.",
                    },
                    "style": {
                        "type": "string",
                        "description": "The style of the image or diagram e.g. realistic, cartoon, technical, a map, etc.",
                    },
                    "size": {
                        "type": "string",
                        "description": "The size and orientation of the image or diagram, e.g. 800x600, 16:9, etc.",
                    },
                    "format": {
                        "type": "string",
                        "description": "The format of the image or diagram, e.g. PNG, JPEG, SVG, etc.",
                    }
                },
                "required": ["content", "style", "size", "format"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Creates a reminder for the specific user",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_created": {
                        "type": "string",
                        "description": "The date the user requested the reminder",
                    },
                    "date_due": {
                        "type": "string",
                        "description": "The due date of the reminder",
                    },
                    "reminder_details": {
                        "type": "string",
                        "description": "The details of the reminder, e.g. 'Buy groceries at 5pm'",
                    }
                },
                "required": ["date_created", "date_due", "reminder_details"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "determine_location",
            "description": "Determines location details of ambiguous or unspecified locations, based on context, history, and clue details in the conversation",
            "parameters": {
                "type": "object",
                "properties": {
                    # "coordinates": {
                    #     "type": "string",
                    #     "description": "The coordinates of the location, e.g. 37.7749° N, 122.4194° W",
                    # },
                    "address": {
                        "type": "string",
                        "description": "An address of the reference near/at the location",
                    },
                    "landmark": {
                        "type": "string",
                        "description": "A reference landmark or notable feature near/at the location",
                    },
                    "city": {
                        "type": "integer",
                        "description": "A reference city and/or neighbourhood near/at the location",
                    },
                    "state": {
                        "type": "integer",
                        "description": "The state, province, or region near/at the location",
                    },
                    "country": {
                        "type": "integer",
                        "description": "The country near/at the location",
                    },
                    "direction": {
                        "type": "integer",
                        "description": "The direction, in degrees relative to N, of the reference relative to the location",
                    },
                    "distance": {
                        "type": "integer",
                        "description": "The distance, in meters (m), of the reference relative to the location",
                    },
                },
                "required": ["landmark", "city", "state", "country"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                },
                "required": ["location", "format"],
            },
        }
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_n_day_weather_forecast",
    #         "description": "Get an N-day weather forecast",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "location": {
    #                     "type": "string",
    #                     "description": "The city and state, e.g. San Francisco, CA",
    #                 },
    #                 "format": {
    #                     "type": "string",
    #                     "enum": ["celsius", "fahrenheit"],
    #                     "description": "The temperature unit to use. Infer this from the users location.",
    #                 },
    #                 "num_days": {
    #                     "type": "integer",
    #                     "description": "The number of days to forecast",
    #                 }
    #             },
    #             "required": ["location", "format", "num_days"]
    #         },
    #     }
    # },
]