import openai
from app.core.config import settings

openai.api_key = settings.openai_api_key

def build_prompt(history: list[dict], user_message: str) -> str:
    """
    # Build the prompt using the history and the user's message
    """
    lines = []
    for entry in history:
        # Verify if the entry has both user and bot messages
        if "user" in entry and "bot" in entry:
            lines.append(f"Usuario: {entry['user']}\nBot: {entry['bot']}")
        elif "bot" in entry:  # Only bot messages 
            lines.append(entry["bot"])

    # Add the user's message
    lines.append(f"Usuario: {user_message}\nBot:")
    return "\n".join(lines)

def validate_history(history: list[dict]) -> bool:
    """
    Validate if the history has the required format
    """
    for entry in history:
        if not isinstance(entry, dict):
            return False
        
        if "bot" not in entry and "user" not in entry:
            return False
    
    return True

def generate_response(prompt: str):
    """
    Generate a response from the OpenAI API
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"