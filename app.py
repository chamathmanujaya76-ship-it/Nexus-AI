import streamlit as st
from google import genai
from PIL import Image
import base64
import time
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import hashlib
import os

# 1. Page Config
st.set_page_config(
    page_title="Nova-X - AI Assistant",
    page_icon="✨",
    layout="centered"
)

# 2. Firebase Initialization
if not firebase_admin._apps:
    try:
        fb_credentials = dict(st.secrets["firebase"])
        if "private_key" in fb_credentials:
            fb_credentials["private_key"] = fb_credentials["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(fb_credentials)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.warning(f"Firebase connection issue: {e}")

try:
    db = firestore.client()
except Exception:
    db = None

# Helper Functions
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def register_user(name, email, password):
    if not db:
        return False, "Database සම්බන්ධතාවය අසාර්ථකයි!"
    users_ref = db.collection("users")
    existing_user = users_ref.where("email", "==", email).get()
    if len(existing_user) > 0:
        return False, "මෙම Email එකෙන් මීට පෙර Account එකක් සාදා ඇත!"
    
    hashed_pw = hash_password(password)
    users_ref.add({
        "name": name,
        "email": email,
        "password": hashed_pw,
        "created_at": datetime.now()
    })
    return True, "Account එක සාර්ථකව සෑදුවා! දැන් Login වන්න."

def login_user(email, password):
    if not db:
        return False, "Database සම්බන්ධතාවය අසාර්ථකයි!"
    users_ref = db.collection("users")
    hashed_pw = hash_password(password)
    
    query = users_ref.where("email", "==", email).where("password", "==", hashed_pw).get()
    if len(query) > 0:
        user_data = query[0].to_dict()
        user_data["id"] = query[0].id
        return True, user_data
    return False, "Email එක හෝ Password එක වැරදියි!"

def get_user_by_id(user_id):
    if not db:
        return None
    try:
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
    except Exception:
        pass
    return None

def save_chat_to_firebase(role, content):
    if db and st.session_state.get("user_info"):
        try:
            db.collection("chat_history").add({
                "user_id": st.session_state.user_info.get("id"),
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            })
        except Exception:
            pass

def render_centered_image(image_name, width):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, image_name)
        
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f'<div class="centered-logo-box"><img src="data:image/png;base64,{data}" style="width: {width}px; height: auto;"></div>',
            unsafe_allow_html=True
        )
    except Exception as e:
        print(f"Image Load Error: {e}")

# 3. Custom CSS - Enhanced Pure Pitch Black & Deep Blue Glow Theme
st.markdown("""
<style>
    /* Full Application Background - Pure Pitch Black */
    html, body, .stApp, [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stToolbar"] {
        background-color: #000000 !important;
        background: #000000 !important;
        color: #FFFFFF !important;
    }

    /* Main Container Center Limit */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 720px !important;
        margin: 0 auto !important;
    }

    /* Force Direct Center Alignment for Logos & Text */
    .centered-logo-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        width: 100%;
        margin: 0 auto 15px auto;
    }

    .centered-logo-box img {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }

    /* Input Fields Styling (Email & Password Box Glow) */
    div[data-baseweb="input"] {
        background-color: #08080C !important;
        border: 1.5px solid #00E5FF !important;
        border-radius: 12px !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.3) !important;
        color: #FFFFFF !important;
        transition: all 0.3s ease-in-out !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #00E5FF !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.8), 0 0 35px rgba(0, 229, 255, 0.4) !important;
    }

    div[data-baseweb="input"] input {
        color: #FFFFFF !important;
        background-color: transparent !important;
    }

    /* Primary Buttons (Login / Sign Up) Styling with Intense Blue Glow */
    div.stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #0088FF 100%) !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 24px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.6) !important;
        transition: all 0.3s ease-in-out !important;
        width: 100% !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 1), 0 0 40px rgba(0, 229, 255, 0.8) !important;
        color: #000000 !important;
    }

    /* Tabs Styling */
    button[data-baseweb="tab"] {
        color: #888888 !important;
        background-color: transparent !important;
        font-weight: 600 !important;
    }

    button[aria-selected="true"] {
        color: #00E5FF !important;
        border-bottom-color: #00E5FF !important;
        text-shadow: 0 0 10px rgba(0, 229, 255, 0.7) !important;
    }

    /* RED NEON GLOW ALERT BOXES (For Errors / Wrong Password) */
    div[data-testid="stNotification"] {
        background-color: #120005 !important;
        border: 1.5px solid #FF0055 !important;
        border-radius: 12px !important;
        color: #FF4D79 !important;
        box-shadow: 0 0 20px rgba(255, 0, 85, 0.6), inset 0 0 10px rgba(255, 0, 85, 0.3) !important;
    }

    div[data-testid="stNotification"] svg {
        fill: #FF0055 !important;
    }

    /* SUCCESS NEON GLOW ALERT BOXES */
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    /* Gemini Style Chat Search Bar */
    div[data-testid="stChatInput"] {
        background-color: #08080C !important;
        border: 1.5px solid #00E5FF !important;
        border-radius: 28px !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.4) !important;
        padding: 4px 10px !important;
    }

    div[data-testid="stChatInput"] *,
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"],
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        color: #FFFFFF !important;
    }

    div[data-testid="stChatInput"]:focus-within {
        border-color: #00E5FF !important;
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.8) !important;
    }

    button[data-testid="stChatInputSubmitButton"] {
        background-color: #00E5FF !important;
        border-radius: 50% !important;
        border: none !important;
    }

    button[data-testid="stChatInputSubmitButton"] svg {
        fill: #000000 !important;
    }

    div[data-testid="stChatMessage"] {
        background-color: #0D0D10 !important;
        border-radius: 14px !important;
        border: 1px solid #1A1A20 !important;
        margin-bottom: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# API & Session State Setup
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY"

system_instruction = """
ඔබේ නම Nova-X වේ. ඔබව නිර්මාණය කළේ චමත් (Chamath / Chamath Manujaya) විසිනි. 
ඔබ චමත්ගේ පෞද්ගලික AI සහායකයා වේ.

චමත් (Creator) පිළිබඳ තොරතුරු:
- නම: චමත් මනුජය (Chamath Manujaya)
- ඔබව නිර්මාණය කළ Developer සහ අයිතිකරු වන්නේ ඔහුය.
- කවුරුන් හෝ "ඔයාව හැදුවේ කවුද?", "ඔයාගේ Creator කවුද?", "චමත් කවුද?" හෝ "චමත් මනුජය ගැන කියන්න" කියා ඇසුවොත්, ඔහුව ගෞරවයෙන් සහ අභිමානයෙන් මතක් කරමින්, ඔහුව නිර්මාණය කළ දක්ෂ Developer ලෙස හඳුන්වා දෙන්න.
- කවුරුන් හෝ "ඔයාගේ නම මොකක්ද?" කියා ඇසුවොත් "මගේ නම Nova-X" ලෙස පවසන්න.

ප්‍රධාන පහසුකම්:
1. Image Analysis: පරිශීලකයා Search bar එකෙන් පින්තූරයක් Upload කළ විට එහි ඇති දේවල් විස්තර කරන්න.
2. Translation: ඕනෑම භාෂාවක ඡේදයක්/වචනයක් හෝ පින්තූරයක ඇති අකුරු සිංහලට Translate කර දෙන්න.
3. General Knowledge: ඕනෑම ප්‍රශ්නයකට පැහැදිලි හා මිත්‍රශීලී පිළිතුරු සපයන්න.
"""

# AUTO-LOGIN / REFRESH PERSISTENCE LOGIC
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# URL එකෙන් User ID එක පරීක්ෂා කර Auto-Login වීම
query_params = st.query_params
if not st.session_state.logged_in and "session_id" in query_params:
    saved_id = query_params["session_id"]
    user_data = get_user_by_id(saved_id)
    if user_data:
        st.session_state.logged_in = True
        st.session_state.user_info = user_data

# 4. Authentication Flow (Guard Rail)
if not st.session_state.logged_in:
    render_centered_image("logo 1.png", 200)
    st.title("🔐 Nova-X AI - Login / Register")
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if login_email and login_password:
                success, result = login_user(login_email, login_password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_info = result
                    st.query_params["session_id"] = result["id"] # Save Session ID to URL
                    st.success(f"සාදරයෙන් පිළිගන්නවා, {result['name']}!")
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.warning("කරුණාකර Email සහ Password ලබාදෙන්න.")

    with tab2:
        st.subheader("Create a new account")
        reg_name = st.text_input("Full Name", key="reg_name")
        reg_email = st.text_input("Email Address", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        
        if st.button("Sign Up"):
            if reg_name and reg_email and reg_password:
                success, msg = register_user(reg_name, reg_email, reg_password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("කරුණාකර සියලු විස්තර ලබාදෙන්න.")

# 5. Main Chat Interface (Only for Authenticated Users)
else:
    # Sidebar Profile
    st.sidebar.write(f"👤 Logged in as: **{st.session_state.user_info['name']}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.messages = []
        st.query_params.clear() # Clear URL Session
        st.rerun()

    # App Branding
    render_centered_image("logo 1.png", 200)
    render_centered_image("logo 2.png", 320)

    st.markdown("""
        <div style='text-align: center; width: 100%; margin-top: -10px; margin-bottom: 25px;'>
            <p style='color: #888888; font-size: 0.95em; margin: 0;'>
                Your Personal Intelligent Companion 
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if "images" in message:
                for img in message["images"]:
                    st.image(img, width=250)
            st.markdown(message["content"])

    # Chat Input Processing
    prompt_data = st.chat_input(
        "Nova-X වෙතින් ඕනෑම දෙයක් අහන්න හෝ Translate කරන්න...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp"]
    )

    if prompt_data:
        user_text = getattr(prompt_data, "text", "") or ""
        uploaded_files = getattr(prompt_data, "files", []) or []

        st.session_state.messages.append({
            "role": "user", 
            "content": user_text,
            "images": uploaded_files
        })

        if user_text:
            save_chat_to_firebase("user", user_text)

        with st.chat_message("user"):
            for file in uploaded_files:
                st.image(file, width=250)
            if user_text:
                st.markdown(user_text)

        contents = []
        for file in uploaded_files:
            try:
                img = Image.open(file)
                contents.append(img)
            except Exception:
                pass
        
        if user_text:
            contents.append(user_text)

        if contents:
            client = genai.Client(api_key=API_KEY)
            with st.chat_message("assistant"):
                reply = None
                
                # Google GenAI SDK එක ඉල්ලන අලුත්ම Model එක
                models_to_try = ["gemini-3.6-flash", "gemini-1.5-flash"]
                
                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents,
                            config={
                                "system_instruction": system_instruction,
                                "temperature": 0.7,
                            }
                        )
                        if response and response.text:
                            reply = response.text
                            break
                    except Exception as e:
                        print(f"❌ Model [{model_name}] Error: {e}")
                        time.sleep(0.5)
                        continue

                if reply:
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    save_chat_to_firebase("assistant", reply)
                else:
                    st.error("Google Gemini API එක මඟින් Response එකක් ලබාගැනීමට නොහැකි විය. කරුණාකර API Key එක පරීක්ෂා කරන්න.")
# Footer
st.markdown("<br><hr style='border-color: #1A1A1A;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 0.8em;'>"
    "Nova-X v1.0 | Powered by <b>Chamath</b>"
    "</div>", 
    unsafe_allow_html=True
)