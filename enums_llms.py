from enum import Enum, auto

class OpMode(Enum):
    completion = auto()
    tools = auto()

class OpenAIModels(Enum):
    GPT3_5 = "gpt-3.5-turbo"
    GPT4O = "gpt-4o"

    def __str__(self):
        return self.value

class AnthropicModels(Enum):
    CLAUDE3_5 = "claude-3-5-sonnet-20240620"

    def __str__(self):
        return self.value


class GoogleModels(Enum):
    BERT = "bert"
    T5 = "t5"
    FLAN = "flan"

    def __str__(self):
        return self.value


class HuggingFaceModels(Enum):
    GPT2 = "gpt-2"
    BART = "bart"
    T5 = "t5"

    def __str__(self):
        return self.value


class LLMProvider():
    OPENAI = OpenAIModels
    ANTHROPIC = AnthropicModels
    GOOGLE = GoogleModels
    HUGGINGFACE = HuggingFaceModels


if __name__ == "__main__":
    # Correctly access and print the nested enum values outside the class definition
    print(LLMProvider.OPENAI) # output: 'OpenAIModels'
    print(LLMProvider.ANTHROPIC.CLAUDE3_5) # output: 'claude-3-5-sonnet-20240620'
    print(LLMProvider.GOOGLE.BERT) # output: 'bert'