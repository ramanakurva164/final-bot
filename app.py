import streamlit as st
import json
import time
import os
from dotenv import load_dotenv
from test_inference import get_model_reply
from st_login_form import login_form

# Load .env file
load_dotenv()

# Streamlit page settings
st.set_page_config(page_title="Agent Ramana (Mistral API)", page_icon="🤖", layout="wide")

# Hugging Face token
hf_token = st.secrets.get("HF_TOKEN")
if not hf_token:
    st.error("❌ Please set your Hugging Face token in Streamlit secrets or environment variables.")
    st.stop()

# --- Hide Default Logout Button from st-login-form ---
st.markdown("""
    <style>
    button[kind="secondary"] {
        display: none !important;  /* Hide the default logout button */
    }
    </style>
""", unsafe_allow_html=True)

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

    # --- Custom Top Navbar with Logout ---
    st.markdown(f"""
        <style>
        .top-nav {{
            position: fixed;
            top: 10px;
            right: 20px;
            background-color: #1E1E1E;
            padding: 6px 14px;
            border-radius: 8px;
            z-index: 100;
            display: flex;
            align-items: center;
        }}
        .top-nav span {{
            margin-right: 10px;
            color: #fff;
            font-weight: 500;
        }}
        .top-nav button {{
            background-color: #FF4B4B;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
        }}
        .top-nav button:hover {{
            background-color: #cc0000;
        }}
        </style>
        <div class="top-nav">
            <span>👋 {username}</span>
            <form action="" method="post">
                <button type="submit" name="logout">🚪 Logout</button>
            </form>
        </div>
    """, unsafe_allow_html=True)

    # --- Handle Logout ---
    if st.query_params.get("logout"):
        st.session_state.clear()
        st.rerun()

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

    # --- File Upload ---
    uploaded_file = st.file_uploader("Upload a file to discuss", type=["pdf", "txt"])
    if uploaded_file:
        try:
            file_text = uploaded_file.read().decode("utf-8", errors="ignore")
            st.session_state.messages.append({"role": "system", "content": f"File content:\n{file_text}"})
            st.success("✅ File content loaded into conversation context.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

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
