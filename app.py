import streamlit as st
import json
import time
import os
from dotenv import load_dotenv
from test_inference import get_model_reply
from st_login_form import login_form, logout

# Load .env file
load_dotenv()

# Streamlit page settings
st.set_page_config(page_title="Agent Ramana (Mistral API)", page_icon="🤖", layout="wide")

# Hugging Face token
hf_token = st.secrets.get("HF_TOKEN")
if not hf_token:
    st.error("❌ Please set your Hugging Face token in Streamlit secrets or environment variables.")
    st.stop()

# --- Supabase Login Form ---
supabase_connection = login_form()

# --- Message Persistence ---
def save_history():
    with open("chat_history.json", "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists("chat_history.json"):
        with open("chat_history.json", "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)

# --- After Authentication ---
if st.session_state.get("authenticated"):
    username = st.session_state.get("username", "guest")
    

    # Sidebar Navigation
    st.sidebar.title("📌 Navigation")
    page = st.sidebar.radio("Go to:", ["💬 Chatbot", "👤 Profile"])

    # --- Profile Page ---
    if page == "👤 Profile":
        st.title("👤 User Profile")
        st.markdown(f"""
        <div style="background:#1e1e2f; padding:20px; border-radius:12px; color:white;">
          <h3>Welcome 👋</h3>
          <p><b>name:</b>  {username}</p>
          <p><b>Status</b> : Active</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔐 Logout"):
            logout()
            st.experimental_rerun()

    # --- Chatbot Page ---
    elif page == "💬 Chatbot":
        st.title("🤖 Agent Ramana (Mistral API)")

        # --- Initialize Messages ---
        if "messages" not in st.session_state:
            load_history()
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hey, I'm Ramana (Mistral powered via API). How can I help you today? 😊"}
            ]

        # --- Sidebar: Model Selection ---
        MODEL_ID = st.sidebar.selectbox(
            "Choose Model",
            [
                "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
                "deepseek-ai/DeepSeek-V3-0324:featherless-ai",
                "meta-llama/Meta-Llama-3.1-8B-Instruct:featherless-ai"
            ]
        )

        # --- Sidebar: Export Chat ---
        if st.sidebar.button("Download Chat History"):
            chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            st.download_button("Download Chat", chat_text, file_name="chat.txt")

        # --- Display Chat History ---
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # --- Chat Input ---
        if user_input := st.chat_input("Say something to Ramana..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                try:
                    full_reply = get_model_reply(st.session_state.messages, hf_token, MODEL_ID)

                    # Typing effect
                    typed_text = ""
                    for char in full_reply:
                        typed_text += char
                        placeholder.markdown(typed_text + "▌")
                        time.sleep(0.005)
                    placeholder.markdown(typed_text)

                    st.session_state.messages.append({"role": "assistant", "content": full_reply})
                    save_history()
                except Exception as e:
                    st.error(f"API Error: {e}")

# --- If Not Authenticated ---
else:
    st.error("❌ Please log in to access the chatbot.")
