import requests

API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai"

def get_model_reply(messages, hf_token):
    """
    Sends conversation history to Hugging Face API and returns the assistant's reply.
    """
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.7,
        "top_p": 0.95
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
