import asyncio
import sys
sys.path.append("/home/clar/Downloads/lexis")
from lexis.config.settings import get_settings
from lexis.services.ai_service import AIService

async def main():
    api_key = get_settings().gemini_api_key
    if not api_key:
        print("NO API KEY")
        return
    service = AIService(api_key)
    try:
        data = service.generate_word_data("Xanax")
        import json
        print("--- GENERATED EXAMPLES LIST ---")
        print(json.dumps(data.get("example_sentences"), indent=2, ensure_ascii=False))
        print("--------------------------")
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    asyncio.run(main())
