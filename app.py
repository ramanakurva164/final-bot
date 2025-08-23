import streamlit as st
import json
import time
import os
from dotenv import load_dotenv
from supabase import create_client
from supabase.client import Client
from test_inference import get_model_reply

# ----------------- CONFIG -----------------
load_dotenv()
st.set_page_config(page_title="Agent Ramana (Mistral API)", page_icon="🤖", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Hugging Face Token
hf_token = st.secrets.get("HF_TOKEN")
if not hf_token:
    st.error("❌ Please set your Hugging Face token in Streamlit secrets or environment variables.")
    st.stop()


# ----------------- CSS -----------------
def local_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: white; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; color: white; }
        h1, h2, h3, h4, h5, h6 { color: #00BFFF; }
        button { background-color: #00BFFF !important; color: white !important; border-radius: 10px !important; border: none !important; }
        .stRadio label, .stSelectbox label { color: white !important; }
        .stChatMessage { border-radius: 12px; padding: 10px; margin: 5px 0; }
        .stMarkdown { color: white !important; }
        </style>
    """, unsafe_allow_html=True)

local_css()


# ----------------- CHAT HISTORY -----------------
def save_history():
    with open("chat_history.json", "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists("chat_history.json"):
        with open("chat_history.json", "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)


# ----------------- SUPABASE AUTH -----------------
def login(email, password):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return result
    except Exception as e:
        return {"error": str(e)}

def signup(email, password):
    try:
        result = supabase.auth.sign_up({"email": email, "password": password})
        return result
    except Exception as e:
        return {"error": str(e)}

def logout():
    supabase.auth.sign_out()
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]
        del st.session_state["username"]


# ----------------- MAIN APP -----------------
if "authenticated" not in st.session_state:
    st.title("🔐 Login to Agent Ramana")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            result = login(email, password)
            if "user" in result and result.user is not None:
                st.session_state["authenticated"] = True
                st.session_state["username"] = email
                st.success("✅ Logged in successfully!")
                st.experimental_rerun()
            else:
                st.error(f"❌ Login failed: {result.get('error')}")

    with tab2:
        email = st.text_input("New Email", key="signup_email")
        password = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            result = signup(email, password)
            if "user" in result and result.user is not None:
                st.success("✅ Account created! Please login.")
            else:
                st.error(f"❌ Signup failed: {result.get('error')}")

else:
    # Sidebar Navigation
    st.sidebar.title("📌 Navigation")
    page = st.sidebar.radio("Go to:", ["💬 Chatbot", "👤 Profile"])

    if page == "👤 Profile":
        st.title("👤 User Profile")
        st.markdown(f"""
        <div style="background:#161b22; padding:20px; border-radius:12px; color:white;">
          <h3>Welcome 👋</h3>
          <p><b>Email:</b> {st.session_state['username']}</p>
          <p><b>Status:</b> Active</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔐 Logout"):
            logout()
            st.experimental_rerun()

    elif page == "💬 Chatbot":
        st.title("🤖 Agent Ramana (Mistral API)")

        if "messages" not in st.session_state:
            load_history()
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hey, I'm Ramana (Mistral powered via API). How can I help you today? 😊"}
            ]

        MODEL_ID = st.sidebar.selectbox(
            "Choose Model",
            [
                "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
                "mistralai/Mistral-7B-Instruct-v0.3:featherless-ai",
                "Qwen/Qwen2.5-72B-Instruct:featherless-ai"
            ]
        )

        if st.sidebar.button("Download Chat History"):
            chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            st.download_button("Download Chat", chat_text, file_name="chat.txt")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_input := st.chat_input("Say something to Ramana..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                try:
                    full_reply = get_model_reply(st.session_state.messages, hf_token, MODEL_ID)
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
