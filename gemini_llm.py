import json
import google.generativeai as genai
from PIL import Image
from lib.config import google_ai_api_key

genai.configure(api_key=google_ai_api_key)
model = genai.GenerativeModel("gemini-1.5-pro")


async def analyze_with_gemini(image_path, message_text):
    prompt = f"""
    Analyze the following crypto-related message and image (if provided):

    Message: {message_text}

    Determine if this is an alpha call for a cryptocurrency. Carefully examine the entire message for the following information:

    1. Token Ticker: Look for symbols like $XXX or similar patterns that represent a token's ticker. This is case sensitive and could be any combination of letters, numbers and casing.
    2. Token Address: This could be a long string of alphanumeric characters, often 32-64 characters long. It might be on Ethereum (starts with 0x), Solana (base58 encoded, often 32-44 characters), or other blockchains. Include the full address if found.
    3. Network: Identify the blockchain network (e.g., Ethereum, Solana, BSC, etc.). If not explicitly stated, try to infer from the context or address format.

    Pay special attention to any strings that look like addresses, even if they're not explicitly labeled as such. They often appear at the end of messages.

    If the token ticker and network are not present, consider this message invalid.
    Else assume it is an alpha call, unless the Message gives you reason to believe otherwise.
    
    Format your response as a JSON object with the following structure:
    {{
        "is_alpha_call": true/false,
        "token_ticker": "XXX",
        "token_address": "full_address_here_if_found",
        "network": "Ethereum/Solana/BSC/etc.",
        "confidence": 0.95,
        "additional_info": "Any other relevant information, including reasons for your decision"
    }}
    
    Ensure all fields are present in the JSON, using null for missing values.
    Return ONLY the JSON object, without any additional text or explanation.
    """

    try:
        if image_path:
            image = Image.open(image_path)
            response = model.generate_content([prompt, image])
        else:
            response = model.generate_content(prompt)

        # Extract the text content from the response
        response_text = response.text

        # Try to parse the JSON directly
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            # If direct parsing fails, try to find and extract the JSON object
            import re

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return result
                except json.JSONDecodeError:
                    print("Error: Invalid JSON in extracted content")
                    return None
            else:
                print("Error: No valid JSON object found in the response")
                return None

    except Exception as e:
        print(f"Error in analyze_with_gemini: {str(e)}")
        return None
