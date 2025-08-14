import streamlit as st
import os
import time
from dotenv import load_dotenv
from test_inference import get_model_reply

# Load .env file
load_dotenv()

# Streamlit page settings
st.set_page_config(page_title="Agent Ramana (Mistral API)", page_icon="🤖", layout="wide")

# Hugging Face token
hf_token = os.getenv("HF_TOKEN") or st.secrets.get("HF_TOKEN")
if not hf_token:
    st.error("❌ Please set your Hugging Face token in Streamlit secrets or environment variables.")
    st.stop()

# Chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hey, I'm Ramana (Mistral powered via API). How can I help you today? 😊"}
    ]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if user_input := st.chat_input("Say something to Ramana..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            # Get reply from backend
            full_reply = get_model_reply(st.session_state.messages, hf_token)

            # Typing effect
            typed_text = ""
            for char in full_reply:
                typed_text += char
                placeholder.markdown(typed_text + "▌")
                time.sleep(0.015)
            placeholder.markdown(typed_text)

            st.session_state.messages.append({"role": "assistant", "content": full_reply})
        except Exception as e:
            st.error(f"API Error: {e}")
