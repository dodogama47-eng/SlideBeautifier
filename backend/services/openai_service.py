from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()


class OpenAIService:

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        self.client = OpenAI(api_key=api_key)

    def generate_slide_plan(self, content_text: str) -> str:
        response = self.client.responses.create(
            model="gpt-5.6-sol",
            input=f"""
You are an AI PowerPoint layout assistant.

The user uploaded a content PowerPoint.
Extract the key ideas and create a clean slide plan.

Return in this format:

Slide 1:
Title:
Bullets:
- 
- 

Slide 2:
Title:
Bullets:
- 
- 

Content:
{content_text}
"""
        )

        return response.output_text