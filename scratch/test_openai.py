import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"Using API Key: {api_key[:15]}...{api_key[-15:] if api_key else ''}")
    
    client = AsyncOpenAI(api_key=api_key)
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=["Hello, GigBridge!"]
        )
        print("Success! Embedding length:", len(response.data[0].embedding))
    except Exception as e:
        print("Error calling OpenAI API:", e)

if __name__ == "__main__":
    asyncio.run(main())
