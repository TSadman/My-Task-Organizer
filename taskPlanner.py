import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Task Planner", layout="centered")

# --- CUSTOM CSS FOR MOBILE (S23 FE Optimization) ---
st.markdown("""
    <style>
    /* Force Dark Background */
    .stApp { background-color: #000000; }
    
    /* Make buttons taller for mobile tapping */
    div.stButton > button {
        width: 100%;
        height: 3.5em;
        border-radius: 10px;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    
    /* Task Card Styling */
    .task-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #BB86FC;
        margin-bottom: 15px;
    }
    .urgent-card { border-left: 5px solid #FF4B4B ! evasion; }
    .completed-card { opacity: 0.5; text-decoration: line-through; border-left: 5px solid #4CAF50; }
    
    /* Mobile-first adjustments */
    @media (max-width: 640px) {
        .stMarkdown h1 { font-size: 1.8rem !important; }
    }
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
    return ["Personal", "NCE", "Papers"]

def save_data(df):
    df.to_csv(TASKS_FILE, index=False)

def save_cats(cats):
    pd.DataFrame({"name": cats}).to_csv(CATS_FILE, index=False)

# --- APP LOGIC ---
df = load_data()
categories = load_cats()

# Sidebar: Workspace Management
st.sidebar.title("🗂️ Workspaces")

formatted_cats = []
for cat in categories:
    cat_tasks = df[df['workspace'] == cat]
    urgent_count = len(cat_tasks[(cat_tasks['is_urgent'] == True) & (cat_tasks['completed'] == False)])
    pending_count = len(cat_tasks[cat_tasks['completed'] == False])
    
    label = f"{cat} (U:{urgent_count} / P:{pending_count})"
    if pending_count == 0 and len(cat_tasks) > 0:
        label += " ✅"
    formatted_cats.append(label)

selected_label = st.sidebar.radio("Go to:", formatted_cats)
current_ws = categories[formatted_cats.index(selected_label)]

st.sidebar.markdown("---")
new_cat = st.sidebar.text_input("New Workspace")
if st.sidebar.button("Add Workspace"):
    if new_cat and new_cat not in categories:
        categories.append(new_cat)
        save_cats(categories)
        st.rerun()

if st.sidebar.button("Delete Current Workspace"):
    if len(categories) > 1:
        categories.remove(current_ws)
        df = df[df['workspace'] != current_ws]
        save_cats(categories)
        save_data(df)
        st.rerun()

# --- MAIN UI ---
st.title(f"🚀 {current_ws}")

# Task Input Section
with st.expander("➕ Add New Task", expanded=False):
    t_name = st.text_input("Task Name")
    t_days = st.number_input("Follow-up in X Days", min_value=0, value=3)
    
    if st.button("Create Task"):
        if t_name:
            target = datetime.now() + timedelta(days=t_days)
            is_urgent = t_days <= 1
            new_row = {
                "id": int(datetime.now().timestamp()),
                "workspace": current_ws,
                "task": t_name,
                "target_date": target,
                "is_urgent": is_urgent,
                "completed": False
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.rerun()

# Filtering and Sorting
ws_df = df[df['workspace'] == current_ws].copy()
# Sort: Urgent -> Pending -> Completed
ws_df['sort_val'] = ws_df['completed'].astype(int) * 2 + (~ws_df['is_urgent']).astype(int)
ws_df = ws_df.sort_values('sort_val')

# Display Tasks
for _, row in ws_df.iterrows():
    status_class = "completed-card" if row['completed'] else ("urgent-card" if row['is_urgent'] else "task-card")
    status_text = "🚨 URGENT" if row['is_urgent'] and not row['completed'] else "📅 Pending"
    if row['completed']: status_text = "✅ Done"
    
    with st.container():
        st.markdown(f"""
            <div class="task-card {status_class}">
                <h3 style="margin:0;">{row['task']}</h3>
                <p style="margin:0; font-size:0.8em; color:#BB86FC;">Target: {row['target_date'].strftime('%Y-%m-%d')} | {status_text}</p>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            btn_label = "Undo" if row['completed'] else "Complete"
            if st.button(btn_label, key=f"comp_{row['id']}"):
                df.loc[df['id'] == row['id'], 'completed'] = not row['completed']
                save_data(df)
                st.rerun()
        with col2:
            if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                df = df[df['id'] != row['id']]
                save_data(df)
                st.rerun()
    st.markdown("---")