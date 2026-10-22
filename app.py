import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq


load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
CONTACTS_FILE = os.getenv("CONTACTS_FILE", "config/contacts.json")


def load_contacts():
    contacts_path = Path(CONTACTS_FILE)
    if not contacts_path.exists():
        st.error(f"Contacts file not found: {CONTACTS_FILE}")
        return []

    try:
        with contacts_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        st.error(f"Could not load contacts: {error}")
        return []

CONTACTS = load_contacts()


SYSTEM_PROMPT = """You are OfficeBuddy, a concise workplace email assistant. Help employees draft professional emails to their manager or HR.

YOUR FLOW:
Step 1 — Identify the request type from the user's message:
  - LEAVE: sick leave, casual leave, emergency leave, day off
  - PERMISSION: stepping out, late arrival, leaving early, short absence
  - REQUIREMENT: hardware, software, access card, server access, tools, equipment

Step 2 — Ask ONLY what you need, one question at a time, maximum 3 questions total:
  - LEAVE → ask: (1) which date(s)?, (2) brief reason if not already given
  - PERMISSION → ask: (1) which date?, (2) exact time window (e.g. 2 PM to 4 PM)?
  - REQUIREMENT → ask: (1) exactly what item/access is needed?, (2) brief business reason if not given

Step 3 — Once you have enough info, output the draft in this EXACT format on its own line:
READY:{"subject":"<subject line>","body":"<full email body>","category":"leave|permission|requirement"}

RULES FOR THE EMAIL BODY:
- Write in first person
- Professional but warm tone
- No salutation (no "Dear X") — the app adds that
- No sign-off placeholder — the app adds that
- For leave: clearly state out-of-office for the full day(s) on the given date(s)
- For permission: state stepping away on that date during those exact hours
- For requirement: state the specific item needed and the business justification
- Keep it concise — 3 to 5 sentences max

If the user asks to change or improve the draft after seeing it, update accordingly and output a new READY: block.

Never ask for the manager's name or email — that is handled separately.
Do not use markdown, headers, or bullet points in your replies. Keep responses short and friendly."""


st.set_page_config(
    page_title="OfficeBuddy",
    page_icon="💼",
    layout="centered"
)

st.markdown("""
<style>
    .main { max-width: 720px; margin: 0 auto; }
    .stChatMessage { border-radius: 12px; }

    div[data-testid="column"] .stButton > button {
        width: 100%;
        text-align: left;
        padding: 10px 14px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        background: white;
        font-size: 13px;
        line-height: 1.4;
        height: auto;
    }
    div[data-testid="column"] .stButton > button:hover {
        border-color: #4A90D9;
        background: #f0f6ff;
    }

    .selected-contact {
        background: #f0f6ff;
        border: 1.5px solid #4A90D9 !important;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 13px;
        margin-bottom: 8px;
    }

    .status-success {
        background: #e6f4ea;
        color: #1e6e34;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
    }
    .status-error {
        background: #fce8e6;
        color: #a50e0e;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 13px;
    }

    .section-label {
        font-size: 12px;
        font-weight: 600;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .divider { border-top: 1px solid #eee; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "email_draft" not in st.session_state: st.session_state.email_draft = None
if "selected_contact" not in st.session_state: st.session_state.selected_contact = None
if "show_cc" not in st.session_state: st.session_state.show_cc = False
if "email_sent" not in st.session_state: st.session_state.email_sent = False
if "greeted" not in st.session_state: st.session_state.greeted = False


@st.cache_resource
def get_client(api_key):
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY is missing. Add it in the .env file.")
        st.stop()
    return Groq(api_key=GROQ_API_KEY)


def ask_groq(history):
    client = get_client(GROQ_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.2,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


def parse_draft(text):
    if "READY:" not in text:
        return None, text
    idx = text.index("READY:")
    visible = text[:idx].strip()
    raw = text[idx + 6:].strip().splitlines()[0]
    try:
        draft = json.loads(raw)
        return draft, visible
    except Exception:
        return None, text


def send_email(to_email, cc_email, subject, body, contact_name):
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        raise ValueError("Sender email credentials are missing. Add them in the .env file.")

    full_body = body
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    recipients = [to_email]
    if cc_email:
        msg["Cc"] = cc_email
        recipients.append(cc_email)
    msg.attach(MIMEText(full_body, "plain"))
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
    server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
    server.quit()


st.markdown("## 💼 OfficeBuddy")
st.markdown("<p style='color:#888; font-size:14px; margin-top:-10px;'>Your workplace email assistant</p>", unsafe_allow_html=True)
st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

if not st.session_state.greeted:
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": "Hi! I'm OfficeBuddy 👋 Tell me what you need and I'll draft the email for you.\n\nFor example:\n— \"I want to take leave this Friday\"\n— \"I need to step out from 2 PM to 4 PM tomorrow\"\n— \"I need a second monitor for my desk\""
    })
    st.session_state.greeted = True

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"], avatar="💼" if msg["role"] == "assistant" else "🧑"):
        st.write(msg["content"])

if not st.session_state.email_sent:
    user_text = st.chat_input("Type your request here…")
    if user_text:
        st.session_state.chat_history.append({"role": "user", "content": user_text})
        with st.chat_message("user", avatar="🧑"):
            st.write(user_text)

        with st.chat_message("assistant", avatar="💼"):
            with st.spinner("Thinking…"):
                reply = ask_groq(st.session_state.chat_history)

            draft, visible_reply = parse_draft(reply)

            if visible_reply:
                st.write(visible_reply)

            if draft:
                st.session_state.email_draft = draft
                if not visible_reply:
                    st.write("I've drafted the email for you. Review and send it below.")

            st.session_state.chat_history.append({"role": "assistant", "content": reply})


if st.session_state.email_draft and not st.session_state.email_sent:
    draft = st.session_state.email_draft

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### ✉️ Email Draft")

    st.markdown("<div class='section-label'>Send to</div>", unsafe_allow_html=True)

    if st.session_state.selected_contact:
        c = st.session_state.selected_contact
        st.markdown(
            f"<div class='selected-contact'>✓ <strong>{c['name']}</strong> · {c['role']}<br>"
            f"<span style='color:#888; font-size:12px;'>{c['email']}</span></div>",
            unsafe_allow_html=True
        )
        if st.button("Change recipient", key="change_contact"):
            st.session_state.selected_contact = None
            st.rerun()
    else:
        cols = st.columns(3)
        for i, contact in enumerate(CONTACTS):
            with cols[i % 3]:
                if st.button(
                    f"**{contact['name']}**\n{contact['role']}",
                    key=f"contact_{i}"
                ):
                    st.session_state.selected_contact = contact
                    st.rerun()

    cc_toggle_label = "− Hide CC" if st.session_state.show_cc else "+ Add CC"
    if st.button(cc_toggle_label, key="toggle_cc"):
        st.session_state.show_cc = not st.session_state.show_cc
        st.rerun()

    cc_email = ""
    if st.session_state.show_cc:
        cc_email = st.text_input("CC email address", placeholder="colleague@company.com", key="cc_email_input")

    st.markdown("<div class='section-label' style='margin-top:12px;'>Subject</div>", unsafe_allow_html=True)
    subject = st.text_input(
        label="subject",
        value=draft.get("subject", ""),
        label_visibility="collapsed",
        key="subject_input"
    )

    st.markdown("<div class='section-label'>Body — edit freely before sending</div>", unsafe_allow_html=True)
    contact_name = st.session_state.selected_contact["name"] if st.session_state.selected_contact else "there"
    preview_body = f"Hi {contact_name},\n\n{draft.get('body', '')}\n\nThank you."
    body = st.text_area(
        label="body",
        value=preview_body,
        height=200,
        label_visibility="collapsed",
        key="body_input"
    )

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("🗑 Discard draft", use_container_width=True):
            st.session_state.email_draft = None
            st.session_state.selected_contact = None
            st.session_state.show_cc = False
            st.chat_input
            st.rerun()

    with col2:
        send_disabled = st.session_state.selected_contact is None
        if st.button(
            " Send email" if not send_disabled else " Select a recipient first",
            type="primary",
            disabled=send_disabled,
            use_container_width=True
        ):
            to_email = st.session_state.selected_contact["email"]
            cc = cc_email if st.session_state.show_cc else ""
            try:
                send_email(
                    to_email=to_email,
                    cc_email=cc,
                    subject=subject,
                    body=body,
                    contact_name=contact_name
                )
                st.session_state.email_sent = True
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"✅ Email sent to **{contact_name}** ({to_email}). You're all set!"
                })
                st.rerun()
            except Exception as e:
                st.markdown(
                    f"<div class='status-error'>⚠️ Could not send: {e}</div>",
                    unsafe_allow_html=True
                )


if st.session_state.email_sent:
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='status-success'>✅ Email sent successfully!</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Start a new request"):
        for key in ["chat_history", "email_draft", "selected_contact", "show_cc", "email_sent", "greeted"]:
            del st.session_state[key]
        st.rerun()
