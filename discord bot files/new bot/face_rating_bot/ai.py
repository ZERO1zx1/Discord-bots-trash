import json
import re
import asyncio
from openai import AsyncOpenAI, OpenAIError
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def analyze_face(image_url: str, retries: int = 3) -> dict:
    """Analyze face with retry logic and improved error handling"""
    prompt = """You are an entertainment face reviewer.
Analyze this image.
Return ONLY JSON. No other text.

{
 "overall":8.4,
 "jawline":8.8,
 "eyes":8.1,
 "cheekbones":8.5,
 "symmetry":8.3,
 "skin":8.9,
 "summary":"...",
 "advice":"1. ... 2. ... 3. ..."
}

Scores between 1-10.
Summary: short overall description.
Advice: 3 specific things the person can improve or enhance about their facial appearance, like skincare, grooming, expression, etc. Be positive and constructive.
Do not identify the person. Do not infer sensitive traits. Treat the scores as subjective entertainment feedback."""

    for attempt in range(retries):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]}
                    ],
                    max_tokens=400,
                    temperature=0.7
                ),
                timeout=30.0
            )

            raw = response.choices[0].message.content
            if not raw:
                raise Exception(f"AI хоосон хариу өгсөн. Шалтгаан: {response.choices[0].finish_reason}")

            # Improved JSON extraction
            json_block = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL)
            json_str = json_block.group(1).strip() if json_block else raw.strip()
            
            # Validate JSON structure
            result = json.loads(json_str)
            
            # Ensure all required fields exist
            required_fields = ["overall", "jawline", "eyes", "cheekbones", "symmetry", "skin", "summary", "advice"]
            for field in required_fields:
                if field not in result:
                    result[field] = 0 if field != "summary" and field != "advice" else ""
            
            # Validate score ranges
            for score_field in ["overall", "jawline", "eyes", "cheekbones", "symmetry", "skin"]:
                score = float(result.get(score_field, 0))
                if score < 1 or score > 10:
                    result[score_field] = max(1, min(10, score))
            
            return result

        except asyncio.TimeoutError:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise Exception("⏱️ AI сервер хариу өгөхөд хэтэрхий удаа байна. Дахин оролдоно уу.")
        
        except json.JSONDecodeError as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise Exception(f"❌ AI-ийн хариулт JSON биш байна.\nХүлээн авсан: {raw[:200]}...")
        
        except OpenAIError as e:
            if "rate_limit" in str(e).lower():
                if attempt < retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                raise Exception("⚠️ API rate limit хүрсэн. Хэсэг хугацаа хүлээнэ үү.")
            raise Exception(f"🔴 OpenAI API алдаа: {str(e)[:100]}")
        
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise Exception(f"❌ Үнэлэлт амжилтгүй: {str(e)[:150]}")
    
    raise Exception("❌ Олон удаа оролдсон ч амжилтгүй болсон.")
