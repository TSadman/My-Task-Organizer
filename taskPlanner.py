import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Task Planner", layout="centered")

# --- CUSTOM CSS FOR MOBILE (S23 FE Optimization) ---
st.markdown("""
    <style>
    /* Global Dark Theme Tweaks */
    .stApp { background-color: #000000; }
    
    /* Extra Large Tap Targets for S23 FE */
    div.stButton > button {
        width: 100%;
        height: 3.8em; 
        border-radius: 12px;
        font-weight: bold;
        background-color: #1E1E1E;
        color: #BB86FC;
        border: 1px solid #BB86FC;
        margin-bottom: 5px;
    }
    
    /* Urgent/Action Buttons */
    div.stButton > button:active {
        background-color: #BB86FC !important;
        color: #000000 !important;
    }

    /* Task Card Styling */
    .task-card {
        background-color: #111111;
        padding: 20px;
        border-radius: 15px;
        border-left: 6px solid #BB86FC;
        margin-bottom: 10px;
        box-shadow: 0 4px 15px rgba(187, 134, 252, 0.1);
    }
    .urgent-card { border-left: 6px solid #FF4B4B; }
    .completed-card { opacity: 0.4; text-decoration: line-through; border-left: 6px solid #4CAF50; }
    
    /* Hide Streamlit Header/Footer for cleaner UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- DATA PERSISTENCE ---
TASKS_FILE = "tasks.csv"
CATS_FILE = "categories.csv"

def load_data():
    if os.path.exists(TASKS_FILE):
        df = pd.read_csv(TASKS_FILE)
        df['target_date'] = pd.to_datetime(df['target_date'])
        return df
    return pd.DataFrame(columns=["id", "workspace", "task", "target_date", "is_urgent", "completed"])

def load_cats():
    if os.path.exists(CATS_FILE):
        return pd.read_csv(CATS_FILE)['name'].tolist()
    return ["NCE", "Personal", "Papers"]

def save_all(df, cats):
    df.to_csv(TASKS_FILE, index=False)
    pd.DataFrame({"name": cats}).to_csv(CATS_FILE, index=False)

# --- INITIALIZE STATE ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()
if 'cats' not in st.session_state:
    st.session_state.cats = load_cats()

# --- SIDEBAR: WORKSPACE LOGIC ---
st.sidebar.title("🌑 Workspaces")

formatted_labels = []
for cat in st.session_state.cats:
    ws_tasks = st.session_state.df[st.session_state.df['workspace'] == cat]
    u = len(ws_tasks[(ws_tasks['is_urgent'] == True) & (ws_tasks['completed'] == False)])
    p = len(ws_tasks[ws_tasks['completed'] == False])
    
    check = " ✅" if (p == 0 and len(ws_tasks) > 0) else ""
    formatted_labels.append(f"{cat} (U:{u} / P:{p}){check}")

selected_idx = st.sidebar.radio("Navigate", range(len(formatted_labels)), 
                               format_func=lambda x: formatted_labels[x])
current_ws = st.session_state.cats[selected_idx]

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Manage Workspaces"):
    new_cat = st.text_input("New Name")
    if st.button("Add Workspace"):
        if new_cat and new_cat not in st.session_state.cats:
            st.session_state.cats.append(new_cat)
            save_all(st.session_state.df, st.session_state.cats)
            st.rerun()
    
    if st.button("Delete Current"):
        if len(st.session_state.cats) > 1:
            st.session_state.df = st.session_state.df[st.session_state.df['workspace'] != current_ws]
            st.session_state.cats.remove(current_ws)
            save_all(st.session_state.df, st.session_state.cats)
            st.rerun()

# --- MAIN UI ---
st.title(f"⚡ {current_ws}")

# New Task Entry
with st.expander("➕ NEW TASK", expanded=False):
    t_name = st.text_input("What needs to be done?")
    t_days = st.number_input("Follow-up in (Days)", min_value=0, value=3)
    if st.button("ADD TO LIST"):
        if t_name:
            new_id = int(datetime.now().timestamp())
            target = datetime.now() + timedelta(days=t_days)
            new_row = {
                "id": new_id,
                "workspace": current_ws,
                "task": t_name,
                "target_date": target,
                "is_urgent": t_days <= 1,
                "completed": False
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_all(st.session_state.df, st.session_state.cats)
            st.rerun()

st.markdown("---")

# Task Display & Logic
ws_df = st.session_state.df[st.session_state.df['workspace'] == current_ws].copy()

if not ws_df.empty:
    # Sorting: Urgent -> Pending -> Completed
    ws_df['sort_val'] = ws_df['completed'].astype(int) * 2 + (~ws_df['is_urgent']).astype(int)
    ws_df = ws_df.sort_values('sort_val')

    for _, row in ws_df.iterrows():
        c_class = "completed-card" if row['completed'] else ("urgent-card" if row['is_urgent'] else "task-card")
        due_info = row['target_date'].strftime('%b %d')
        urgency_tag = "🚨 URGENT" if (row['is_urgent'] and not row['completed']) else "📅 Due"
        
        st.markdown(f"""
            <div class="task-card {c_class}">
                <div style="font-size:1.2em; font-weight:bold;">{row['task']}</div>
                <div style="color:#BB86FC; font-size:0.85em;">{urgency_tag}: {due_info}</div>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            label = "UNDO" if row['completed'] else "DONE"
            if st.button(label, key=f"v_{row['id']}"):
                st.session_state.df.loc[st.session_state.df['id'] == row['id'], 'completed'] = not row['completed']
                save_all(st.session_state.df, st.session_state.cats)
                st.rerun()
        with col2:
            if st.button("DELETE", key=f"d_{row['id']}"):
                st.session_state.df = st.session_state.df[st.session_state.df['id'] != row['id']]
                save_all(st.session_state.df, st.session_state.cats)
                st.rerun()
else:
    st.write("No tasks here yet. Relax! ☕")