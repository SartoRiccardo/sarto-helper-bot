import openai
from retry import retry
import asyncio
from typing import List, Tuple
from config import OPENAI_KEY
openai.api_key = OPENAI_KEY


class PrompTokens:
    def __init__(self, prompt: int = 0, completion: int = 0):
        self.prompt = prompt
        self.completion = completion

    def cost(self) -> float:
        return (self.prompt*0.0015+self.completion*0.002)/1000

    def __add__(self, other):
        if not isinstance(other, PrompTokens):
            return
        self.prompt += other.prompt
        self.completion += other.completion
        return self

    def __sub__(self, other):
        if not isinstance(other, PrompTokens):
            return
        self.prompt -= other.prompt
        self.completion -= other.completion
        return self


async def get_video_titles(thread_title: str) -> Tuple[List[str], PrompTokens]:
    prompt = f"""
    Generate 5 YouTube titles for a video about answers to the following question: {thread_title}
    The title must follow every single one of the rules below. No exceptions.
    1. It must be shorter than 70 characters.
    2. It must not have a number in the title
    3. It must be a single sentence.
    4. It must have no punctuation. Not a single character of punctuation. Any punctuation will make your answer invalid.
    5. Each row of the list must ONLY have the answer.
    6. It must not sound too tryhard-y.
    """[1:-1].replace("    ", "")
    titles, tokens = await request_openai(prompt)
    return [x[3:] for x in titles.split("\n")], tokens


async def get_image_idea(thread_title: str) -> Tuple[str, PrompTokens]:
    prompt = f"""
    What is a catchy image I could use as a thumbnail for a video about answers to the following question: {thread_title}
    1. Only give me one image idea
    2. Don't append additional explanation to it
    3. It must be under 100 characters long.
    4. It must be a common thing.
    """[1:-1].replace("    ", "")
    image_idea, tokens = await request_openai(prompt)
    return (None if len(image_idea) > 100 else image_idea), tokens


async def get_pixabay_prompts(image_idea: str) -> Tuple[List[str], PrompTokens]:
    prompt = f"""
    Generate 5 pixabay queries to look for the following image: {image_idea}
    Only include the queries in the response with no additional unnecessary comments.
    """
    queries, tokens = await request_openai(prompt)
    return [x[3:] for x in queries.split("\n")], tokens


async def get_highlighted_text(thread_title: str) -> Tuple[str, PrompTokens]:
    prompt = f"""
    Rewrite the following sentence: {thread_title}
    You must rewrite it following BOTH of these 2 rules listed below. Breaking even ONE will result in your output being worthless:
    1. It must strictly be 70 characters or less. NEVER say something longer than 70 characters UNDER ANY CIRCUMSTANCE. This includes spaces and punctuation.
    2. It must NOT contain "Reddit"
    Never EVER break the first rule. The first rule is the most important one.
    """[1:-1].replace("    ", "")
    return await request_openai(prompt)


async def get_poll(thread_title: str) -> Tuple[str, PrompTokens]:
    prompt = f"""
    A person has asked this question: {thread_title}
    Rephrase the question, and generate 4 possible responses to the question. At least 3 of the responses must be humorous. Do not give me an explanation for the responses. I only want the responses. Not the explanation. Responses must be strictly less than 36 characters long, and at least 3 words long. Responses longer than 36 characters are invalid, do NOT type them.
    Do not prefix the rephrased question with anything like "Rephrased Question:" or "Question:". I want the question in a single line of text.
    Prefix the answers with an emoji. The emojis must all be different.
    """[1:-1].replace("    ", "")
    return await request_openai(prompt)


@retry(
    exceptions=(openai.error.ServiceUnavailableError, openai.error.RateLimitError),
    tries=5,
    delay=10,
    max_delay=60,
    jitter=(10, 20),
)
async def request_openai(*message_list) -> Tuple[str, PrompTokens]:
    messages = []
    role = "user"
    for msg in message_list:
        messages.append({"role": role, "content": msg})
        role = "assistant" if role == "user" else "user"
    completion = await asyncio.to_thread(
        openai.ChatCompletion.create,
        model="gpt-3.5-turbo",
        messages=messages,
    )
    tokens_used = PrompTokens(completion.usage.prompt_tokens, completion.usage.completion_tokens)
    return completion.choices[0].message.content, tokens_used
