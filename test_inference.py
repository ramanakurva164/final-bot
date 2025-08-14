import requests

API_URL = "https://router.huggingface.co/v1/chat/completions"

def get_model_reply(messages, hf_token, model_id):
    """
    Sends conversation history to Hugging Face API and returns the assistant's reply.
    """
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.7,
        "top_p": 0.95
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
