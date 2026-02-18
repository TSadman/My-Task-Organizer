import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. CONFIGURATION & CSS ---
st.set_page_config(
    page_title="Task Planner",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="expanded" 
)

# Custom CSS for Mobile Touch Targets & Dark Mode adjustments
st.markdown("""
    <style>
    /* Bigger buttons for mobile */
    .stButton button { height: 3.5em; font-weight: bold; }
    /* Hide Deploy Button */
    .stDeployButton { visibility: hidden; }
    /* Adjust checkbox size */
    .stCheckbox { transform: scale(1.2); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA FUNCTIONS ---
TASK_FILE = 'tasks.csv'
CAT_FILE = 'categories.csv'

def load_data():
    # Load Tasks
    if os.path.exists(TASK_FILE):
        df_tasks = pd.read_csv(TASK_FILE)
        if 'Target_Date' not in df_tasks.columns:
            df_tasks['Target_Date'] = None
    else:
        df_tasks = pd.DataFrame(columns=["Category", "Task", "Created_At", "Target_Date", "Status"])
    
    # Load Categories
    if os.path.exists(CAT_FILE):
        df_cats = pd.read_csv(CAT_FILE)
        categories = df_cats['Category_Name'].tolist()
    else:
        categories = ["NCE", "Personal Life", "Papers"]
        pd.DataFrame({'Category_Name': categories}).to_csv(CAT_FILE, index=False)
        
    return df_tasks, categories

def save_tasks(df):
    df.to_csv(TASK_FILE, index=False)

def save_categories(cat_list):
    pd.DataFrame({'Category_Name': cat_list}).to_csv(CAT_FILE, index=False)

def check_urgency(target_date_str, status):
    """Returns True if task is pending AND due within 1 day."""
    if status == 'Completed' or pd.isna(target_date_str) or str(target_date_str).strip() == "":
        return False
    try:
        target = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
        today = datetime.now().date()
        days_remaining = (target - today).days
        return days_remaining <= 1
    except:
        return False

# Load Data
df, category_list = load_data()


# --- 4. SIDEBAR NAVIGATION ---
st.sidebar.title("🗂️ Workspaces")

# A. Workspace List with Stats
radio_options = {} 
for cat in category_list:
    pending_tasks = df[(df['Category'] == cat) & (df['Status'] != 'Completed')]
    
    # Calculate Urgency Count
    u_count = 0
    for _, row in pending_tasks.iterrows():
        if check_urgency(row['Target_Date'], row['Status']):
            u_count += 1
            
    p_count = len(pending_tasks)
    
    # Icons: Checkmark if empty, Box if busy
    icon = "✅" if p_count == 0 else "⬜"
    
    # Label formatting
    label = f"{icon} {cat} (U:{u_count} / P:{p_count})"
    radio_options[label] = cat

# B. Selector
if radio_options:
    selected_label = st.sidebar.radio("Go to:", list(radio_options.keys()), label_visibility="collapsed")
    current_category = radio_options[selected_label]
else:
    current_category = "No Categories"

st.sidebar.markdown("---")

# C. Add New Workspace
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
                save_categories(category_list)
                st.session_state.show_add_cat = False
                st.rerun()

# D. Delete Workspace
with st.sidebar.expander("⚙️ Manage Workspaces"):
    cat_to_delete = st.selectbox("Delete:", ["Select..."] + category_list)
    if st.button("Delete Selected", use_container_width=True):
        if cat_to_delete != "Select...":
            category_list.remove(cat_to_delete)
            save_categories(category_list)
            st.rerun()


# --- 5. MAIN INTERFACE ---
st.title(f"{current_category}")

# A. Task Input
with st.container():
    col_in, col_btn = st.columns([0.85, 0.15]) # Input | Add
    new_task = st.text_input("New Task", placeholder="Type specific task...", label_visibility="collapsed")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        # Follow-up days (0 = None)
        days_followup = st.number_input("Follow-up in (days):", min_value=0, value=0, help="0 = No deadline")
    with c2:
        st.write("") # Spacer
        st.write("") # Spacer
        add_btn = st.button("➕ Add", use_container_width=True, type="primary")

    if add_btn and new_task:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Calculate Target Date
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
        save_tasks(df)
        st.rerun()

st.markdown("---")

# B. Task List
# Filter tasks
cat_tasks = df[df['Category'] == current_category].copy()

# Sort Logic: Urgent -> Pending -> Date Created
cat_tasks['is_urgent_sort'] = cat_tasks.apply(lambda x: check_urgency(x['Target_Date'], x['Status']), axis=1)
cat_tasks = cat_tasks.sort_values(by=['Status', 'is_urgent_sort', 'Created_At'], ascending=[True, False, False])

if not cat_tasks.empty:
    for index, row in cat_tasks.iterrows():
        
        is_urgent = check_urgency(row['Target_Date'], row['Status'])
        
        # Styling based on status
        if row['Status'] == 'Completed':
            opacity = "0.5"
            check_icon = "↩️" # Undo symbol
            urgency_badge = ""
            task_text = f"~~{row['Task']}~~"
        else:
            opacity = "1.0"
            check_icon = "✅" # Complete symbol
            task_text = f"**{row['Task']}**"
            
            if is_urgent:
                urgency_badge = "🔴 **URGENT**"
            elif row['Target_Date']:
                urgency_badge = f"🗓️ Due: {row['Target_Date']}"
            else:
                urgency_badge = ""

        # Render Card
        with st.container():
            # Use columns: [Text Area] [Action Buttons]
            c1, c2 = st.columns([5, 1.5])
            
            with c1:
                # Badge line
                if urgency_badge:
                    if "URGENT" in urgency_badge:
                        st.markdown(f":red[{urgency_badge}]")
                    else:
                        st.caption(urgency_badge)
                
                # Main Text
                st.markdown(task_text)
                st.caption(f"Created: {row['Created_At']}")
            
            with c2:
                # Stack buttons vertically
                if st.button(check_icon, key=f"done_{index}", use_container_width=True):
                    new_status = "Pending" if row['Status'] == 'Completed' else "Completed"
                    df.at[index, 'Status'] = new_status
                    save_tasks(df)
                    st.rerun()
                
                if st.button("🗑️", key=f"del_{index}", use_container_width=True):
                    df = df.drop(index)
                    save_tasks(df)
                    st.rerun()
            
            st.divider()

else:
    st.info("No tasks in this workspace.")