import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIG & CSS ---
st.set_page_config(
    page_title="Task Planner",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
    .stButton button { height: 3.5em; font-weight: bold; }
    .stDeployButton { visibility: hidden; }
    /* Checkbox scaling for mobile */
    .stCheckbox { transform: scale(1.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS CONNECTION ---
# We use a specific TTL (Time To Live) of 0 to ensure we always fetch fresh data
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Read the main sheet (Tasks)
        df_tasks = conn.read(worksheet="Tasks", ttl=0)
        # Ensure correct columns exist if sheet is new
        expected_cols = ["Category", "Task", "Created_At", "Target_Date", "Status"]
        if df_tasks.empty or not all(col in df_tasks.columns for col in expected_cols):
            df_tasks = pd.DataFrame(columns=expected_cols)

        # Read the categories sheet
        try:
            df_cats = conn.read(worksheet="Categories", ttl=0)
            categories = df_cats['Category_Name'].dropna().tolist()
        except:
            # Fallback if Categories sheet doesn't exist yet
            categories = ["NCE", "Personal Life", "Papers"]
            
        return df_tasks, categories
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

def save_data(df_tasks, category_list):
    # Update Tasks Sheet
    conn.update(worksheet="Tasks", data=df_tasks)
    
    # Update Categories Sheet
    df_cats = pd.DataFrame({'Category_Name': category_list})
    conn.update(worksheet="Categories", data=df_cats)
    
    # Clear cache so next read is fresh
    st.cache_data.clear()

def check_urgency(target_date_str, status):
    if status == 'Completed' or pd.isna(target_date_str) or str(target_date_str).strip() == "":
        return False
    try:
        target = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
        today = datetime.now().date()
        days_remaining = (target - today).days
        return days_remaining <= 1
    except:
        return False

# Load Data on App Start
df, category_list = load_data()


# --- 3. SIDEBAR ---
st.sidebar.title("🗂️ Workspaces")

# A. Workspace List
radio_options = {} 
if not df.empty:
    for cat in category_list:
        # Filter Pending Tasks
        pending_tasks = df[(df['Category'] == cat) & (df['Status'] != 'Completed')]
        
        # Calculate Urgency
        u_count = 0
        for _, row in pending_tasks.iterrows():
            if check_urgency(row['Target_Date'], row['Status']):
                u_count += 1
                
        p_count = len(pending_tasks)
        icon = "✅" if p_count == 0 else "⬜"
        
        label = f"{icon} {cat} (U:{u_count} / P:{p_count})"
        radio_options[label] = cat

if radio_options:
    selected_label = st.sidebar.radio("Go to:", list(radio_options.keys()), label_visibility="collapsed")
    current_category = radio_options[selected_label]
else:
    current_category = "General" # Fallback

st.sidebar.markdown("---")

# B. Add Workspace
if "show_add_cat" not in st.session_state:
    st.session_state.show_add_cat = False

if st.sidebar.button("➕ New Workspace", use_container_width=True):
    st.session_state.show_add_cat = not st.session_state.show_add_cat

if st.session_state.show_add_cat:
    with st.sidebar.container():
        new_cat_name = st.text_input("Name:", key="new_cat_input")
        if st.button("Save", use_container_width=True):
            if new_cat_name and new_cat_name not in category_list:
                category_list.append(new_cat_name)
                save_data(df, category_list) # Save both to keep sync
                st.session_state.show_add_cat = False
                st.rerun()

# C. Delete Workspace
with st.sidebar.expander("⚙️ Manage Workspaces"):
    cat_to_delete = st.selectbox("Delete:", ["Select..."] + category_list)
    if st.button("Delete Selected", use_container_width=True):
        if cat_to_delete != "Select...":
            category_list.remove(cat_to_delete)
            save_data(df, category_list)
            st.rerun()


# --- 4. MAIN INTERFACE ---
st.title(f"{current_category}")

# A. Task Input
with st.container():
    col_in, col_btn = st.columns([0.85, 0.15])
    new_task = st.text_input("New Task", placeholder="Type specific task...", label_visibility="collapsed")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        days_followup = st.number_input("Follow-up in (days):", min_value=0, value=0, help="0 = No deadline")
    with c2:
        st.write("") 
        st.write("") 
        add_btn = st.button("➕ Add", use_container_width=True, type="primary")

    if add_btn and new_task:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if days_followup > 0:
            target_date = (datetime.now() + timedelta(days=days_followup)).strftime("%Y-%m-%d")
        else:
            target_date = None 
            
        new_entry = pd.DataFrame([{
            "Category": current_category,
            "Task": new_task,
            "Created_At": timestamp,
            "Target_Date": target_date,
            "Status": "Pending"
        }])
        
        df = pd.concat([df, new_entry], ignore_index=True)
        save_data(df, category_list)
        st.rerun()

st.markdown("---")

# B. Task List
cat_tasks = df[df['Category'] == current_category].copy()

# Sort Logic
cat_tasks['is_urgent_sort'] = cat_tasks.apply(lambda x: check_urgency(x['Target_Date'], x['Status']), axis=1)
cat_tasks = cat_tasks.sort_values(by=['Status', 'is_urgent_sort', 'Created_At'], ascending=[True, False, False])

if not cat_tasks.empty:
    for index, row in cat_tasks.iterrows():
        is_urgent = check_urgency(row['Target_Date'], row['Status'])
        
        if row['Status'] == 'Completed':
            opacity = "0.5"
            check_icon = "↩️" 
            urgency_badge = ""
            task_text = f"~~{row['Task']}~~"
        else:
            opacity = "1.0"
            check_icon = "✅" 
            task_text = f"**{row['Task']}**"
            
            if is_urgent:
                urgency_badge = "🔴 **URGENT**"
            elif row['Target_Date']:
                urgency_badge = f"🗓️ Due: {row['Target_Date']}"
            else:
                urgency_badge = ""

        # Render Card
        with st.container():
            c1, c2 = st.columns([5, 1.5])
            
            with c1:
                if urgency_badge:
                    if "URGENT" in urgency_badge:
                        st.markdown(f":red[{urgency_badge}]")
                    else:
                        st.caption(urgency_badge)
                
                st.markdown(task_text)
                st.caption(f"Created: {row['Created_At']}")
            
            with c2:
                # We must match the Original DataFrame Index to delete/update correctly
                # 'index' here is the index in cat_tasks, but we need the index in 'df'
                original_index = index 
                
                if st.button(check_icon, key=f"done_{original_index}", use_container_width=True):
                    new_status = "Pending" if row['Status'] == 'Completed' else "Completed"
                    df.at[original_index, 'Status'] = new_status
                    save_data(df, category_list)
                    st.rerun()
                
                if st.button("🗑️", key=f"del_{original_index}", use_container_width=True):
                    df = df.drop(original_index)
                    save_data(df, category_list)
                    st.rerun()
            
            st.divider()
else:
    st.info("No tasks in this workspace.")