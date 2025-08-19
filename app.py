import streamlit as st
import json
import time
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# --- External modules you already have ---
from test_inference import get_model_reply
from st_login_form import login_form, logout

# ==============================
# Boot & Config
# ==============================
load_dotenv()
st.set_page_config(page_title="Agent Ramana (Mistral API)", page_icon="🤖", layout="wide")

# --- CSS: style secondary buttons (logout, etc.) ---
st.markdown(
    """
    <style>
    button[kind="secondary"] {
        background-color: #ff4b4b !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 10px 20px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        transition: 0.3s ease-in-out;
        width:100px;
    }
    button[kind="secondary"]:hover {
        background-color: #e60000 !important;
        transform: scale(1.05);
    }
    /* Chat bubbles */
    .user-msg {background:#0e1117; color:#fff; padding:12px 14px; border-radius:14px;}
    .assistant-msg {background:#111827; color:#e5e7eb; padding:12px 14px; border-radius:14px;}
    .sys-msg {background:#1f2937; color:#cbd5e1; padding:12px 14px; border-radius:14px; font-style:italic;}
    .chat-title {font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================
# Secrets / Tokens
# ==============================
hf_token = st.secrets.get("HF_TOKEN")
if not hf_token:
    st.error("❌ Please set your Hugging Face token in Streamlit secrets or environment variables.")
    st.stop()

# ==============================
# Persistence Helpers
# ==============================
HISTORY_FILE = "chat_history.json"


def _serialize_conversations(conversations: dict) -> dict:
    """Ensure everything is JSON-serializable (it already is by design)."""
    return conversations


def save_all_conversations():
    data = {
        "conversations": _serialize_conversations(st.session_state.conversations),
        "active_chat": st.session_state.active_chat,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_all_conversations():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state.conversations = data.get("conversations", {})
            st.session_state.active_chat = data.get("active_chat")
        except Exception as e:
            st.warning(f"Couldn't load saved chats: {e}")


# ==============================
# Session Setup
# ==============================
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.conversations = {}
    st.session_state.active_chat = None
    load_all_conversations()

# ==============================
# Auth (Supabase form you already have)
# ==============================
supabase_connection = login_form()

# ==============================
# Utilities
# ==============================
DEFAULT_ASSISTANT_MSG = "Hey, I'm Ramana (Mistral powered via API). How can I help you today? 😊"

MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
    "deepseek-ai/DeepSeek-V3-0324:featherless-ai",
    "meta-llama/Meta-Llama-3.1-8B-Instruct:featherless-ai",
]


def ensure_active_chat():
    """Make sure there is an active chat; create one if missing."""
    if not st.session_state.active_chat or st.session_state.active_chat not in st.session_state.conversations:
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {
            "title": "New Chat",
            "created": datetime.utcnow().isoformat() + "Z",
            "messages": [
                {"role": "assistant", "content": DEFAULT_ASSISTANT_MSG}
            ],
        }
        st.session_state.active_chat = new_id
        save_all_conversations()


def set_title_from_first_user_msg(chat_id: str):
    msgs = st.session_state.conversations[chat_id]["messages"]
    # Find first user message
    first_user = next((m for m in msgs if m.get("role") == "user" and m.get("content")), None)
    if first_user:
        text = first_user["content"].strip().splitlines()[0]
        title = text[:30] + ("…" if len(text) > 30 else "")
        st.session_state.conversations[chat_id]["title"] = title or "New Chat"


# ==============================
# App (Only for authenticated users)
# ==============================
if st.session_state.get("authenticated"):
    username = st.session_state.get("username", "guest")
    st.sidebar.success(f"✅ Welcome {username} 👋")

    # --- Model selection ---
    MODEL_ID = st.sidebar.selectbox("Choose Model", MODELS, index=0)

    # --- New Chat / Delete / Clear All Controls ---
    cols = st.sidebar.columns(3)
    if cols[0].button("➕ New Chat"):
        # Create a completely fresh chat and switch to it
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {
            "title": "New Chat",
            "created": datetime.utcnow().isoformat() + "Z",
            "messages": [
                {"role": "assistant", "content": DEFAULT_ASSISTANT_MSG}
            ],
        }
        st.session_state.active_chat = new_id
        save_all_conversations()
        st.experimental_rerun()

    if cols[1].button("🗑️ Delete Chat") and st.session_state.active_chat:
        # Remove current conversation entirely
        st.session_state.conversations.pop(st.session_state.active_chat, None)
        st.session_state.active_chat = None
        save_all_conversations()
        st.experimental_rerun()

    if cols[2].button("🧹 Clear All"):
        # Nukes everything, including history file
        st.session_state.conversations = {}
        st.session_state.active_chat = None
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.experimental_rerun()

    # --- Chat list (history) ---
    st.sidebar.markdown("### 💬 Chat History")
    if not st.session_state.conversations:
        ensure_active_chat()

    # Sort chats by created time (newest first)
    def _created(chat):
        try:
            return chat.get("created", "")
        except Exception:
            return ""

    sorted_items = sorted(
        st.session_state.conversations.items(),
        key=lambda kv: _created(kv[1]),
        reverse=True,
    )

    # Display as radio list for selection
    options = [chat_id for chat_id, _ in sorted_items]
    labels = [chat["title"] for _, chat in sorted_items]
    if options:
        selected_idx = st.sidebar.radio(
            label="Select a chat",
            options=list(range(len(options))),
            format_func=lambda i: labels[i],
            index=0 if st.session_state.active_chat == options[0] else next((i for i, cid in enumerate(options) if cid == st.session_state.active_chat), 0),
        )
        chosen_chat_id = options[selected_idx]
        if chosen_chat_id != st.session_state.active_chat:
            st.session_state.active_chat = chosen_chat_id
            save_all_conversations()
            st.experimental_rerun()

    # --- Export current chat ---
    st.sidebar.markdown("---")
    if st.session_state.active_chat:
        cur = st.session_state.conversations[st.session_state.active_chat]
        txt = "\n".join([f"{m['role']}: {m['content']}" for m in cur["messages"]])
        st.sidebar.download_button("⬇️ Download Chat (.txt)", data=txt, file_name="chat.txt")
        st.sidebar.download_button(
            "⬇️ Download Chat (.json)",
            data=json.dumps(cur, ensure_ascii=False, indent=2),
            file_name="chat.json",
        )

    st.sidebar.markdown("---")
    logout()

    # --- Main area ---
    ensure_active_chat()

    # Optional: file upload (adds content as a system message)
    uploaded_file = st.file_uploader("Upload a file to discuss", type=["pdf", "txt"])
    if uploaded_file:
        try:
            file_text = uploaded_file.read().decode("utf-8", errors="ignore")
            st.session_state.conversations[st.session_state.active_chat]["messages"].append(
                {"role": "system", "content": f"File content:\n{file_text}"}
            )
            st.success("✅ File content loaded into conversation context.")
            save_all_conversations()
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # --- Render chat messages ---
    messages = st.session_state.conversations[st.session_state.active_chat]["messages"]

    for msg in messages:
        role = msg.get("role", "assistant")
        with st.chat_message(role):
            if role == "user":
                st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
            elif role == "system":
                st.markdown(f"<div class='sys-msg'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='assistant-msg'>{msg['content']}</div>", unsafe_allow_html=True)

    # --- Chat input & model call ---
    user_input = st.chat_input("Say something to Ramana…")
    if user_input:
        # Append user msg
        messages.append({"role": "user", "content": user_input})

        # Auto-title new chats from first user message
        if st.session_state.conversations[st.session_state.active_chat]["title"] == "New Chat":
            set_title_from_first_user_msg(st.session_state.active_chat)

        # Display user bubble immediately
        with st.chat_message("user"):
            st.markdown(f"<div class='user-msg'>{user_input}</div>", unsafe_allow_html=True)

        # Assistant streaming reply
        with st.chat_message("assistant"):
            placeholder = st.empty()
            try:
                # Use your get_model_reply(messages, token, model_id)
                full_reply = get_model_reply(messages, hf_token, MODEL_ID)

                # Typing effect
                typed = ""
                for ch in full_reply:
                    typed += ch
                    placeholder.markdown(f"<div class='assistant-msg'>{typed}▌</div>", unsafe_allow_html=True)
                    time.sleep(0.005)
                placeholder.markdown(f"<div class='assistant-msg'>{typed}</div>", unsafe_allow_html=True)

                messages.append({"role": "assistant", "content": full_reply})
                save_all_conversations()
            except Exception as e:
                st.error(f"API Error: {e}")

else:
    st.error("❌ Please log in to access the chatbot.")
