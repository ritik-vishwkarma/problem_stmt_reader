import streamlit as st
import pandas as pd
import re
import json
import pyperclip

# Set up the app's title and layout with a collapsed sidebar
st.set_page_config(
    layout="wide", 
    page_title="SIH Problem Statement Dashboard",
    initial_sidebar_state="collapsed"
)

# Main title of the application
st.title("💡 Smart India Hackathon 2025 Problem Statements")

# 1. Load your scraped data
try:
    df = pd.read_csv("sih_problem_statements_formatted.csv")
    
    # Bug fix: Convert PS Number to string to enable search functionality
    df['PS Number'] = df['PS Number'].astype(str)

    # Clean up the Description column for better searchability
    df['Description_Cleaned'] = df['Description'].str.replace('**', '', regex=False).str.replace('\n', ' ', regex=False)

    # Add Status/Notes columns if not present
    if 'Status' not in df.columns:
        df['Status'] = "Not Reviewed"
    if 'Notes' not in df.columns:
        df['Notes'] = ""
except FileNotFoundError:
    st.error("Error: The 'sih_problem_statements_formatted.csv' file was not found.")
    st.stop()

# 2. Create the filter sidebar with search bar at the top
st.sidebar.header("🔍 Filter & Search")
search_query = st.sidebar.text_input("Search by PS Number or Title", "").strip()
st.sidebar.markdown("---")

categories = ["All"] + sorted(df['Category'].unique().tolist())
organizations = ["All"] + sorted(df['Organization'].unique().tolist())
themes = ["All"] + sorted(df['Theme'].unique().tolist())
departments = ["All"] + sorted(df['Department'].unique().tolist())
statuses = ["All"] + sorted(df['Status'].unique().tolist())

selected_category = st.sidebar.selectbox("Category", categories)
selected_org = st.sidebar.selectbox("Organization", organizations)
selected_theme = st.sidebar.selectbox("Theme", themes)
selected_dept = st.sidebar.selectbox("Department", departments)
selected_status = st.sidebar.selectbox("Status", statuses)

# 3. Filter the DataFrame based on user selections and search query
filtered_df = df.copy()

if selected_category != "All":
    filtered_df = filtered_df[filtered_df['Category'] == selected_category]
if selected_org != "All":
    filtered_df = filtered_df[filtered_df['Organization'] == selected_org]
if selected_theme != "All":
    filtered_df = filtered_df[filtered_df['Theme'] == selected_theme]
if selected_dept != "All":
    filtered_df = filtered_df[filtered_df['Department'] == selected_dept]
if selected_status != "All":
    filtered_df = filtered_df[filtered_df['Status'] == selected_status]

if search_query:
    filtered_df = filtered_df[
        filtered_df['PS Number'].str.contains(search_query, case=False, na=False) |
        filtered_df['Problem Statement Title'].str.contains(search_query, case=False, na=False)
    ]

# Check if any problems are found after filtering
if filtered_df.empty:
    st.warning("No problem statements match the selected filters or search query. Please adjust your search.")
    st.stop()

# Reset index to allow for navigation
filtered_df = filtered_df.reset_index(drop=True)

# 4. Implement a "single page" view with navigation
if 'current_ps_index' not in st.session_state:
    st.session_state.current_ps_index = 0

# Ensure the index doesn't go out of bounds after filtering
if st.session_state.current_ps_index >= len(filtered_df):
    st.session_state.current_ps_index = 0

total_problems = len(filtered_df)
current_index = st.session_state.current_ps_index
current_ps = filtered_df.iloc[current_index]

# --- Progress Tracker (Sidebar) ---
reviewed_count = (df['Status'] != "Not Reviewed").sum()
shortlisted_count = (df['Status'] == "Shortlisted").sum()
rejected_count = (df['Status'] == "Rejected").sum()
see_later_count = (df['Status'] == "See Later").sum()

st.sidebar.markdown("### 📊 Progress Tracker")
st.sidebar.markdown(f"- Reviewed: **{reviewed_count}/{len(df)}**")
st.sidebar.markdown(f"- Shortlisted: **{shortlisted_count}**")
st.sidebar.markdown(f"- Rejected: **{rejected_count}**")
st.sidebar.markdown(f"- See Later: **{see_later_count}**")

st.markdown("---")

# Create navigation buttons (move Next button further right)
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button("⬅️ Previous"):
        if st.session_state.current_ps_index > 0:
            st.session_state.current_ps_index -= 1
            st.rerun()

with col3:
    if st.button("➡️ Next"):
        if st.session_state.current_ps_index < total_problems - 1:
            st.session_state.current_ps_index += 1
            st.rerun()

with col2:
    st.markdown(f"<p style='text-align: center; font-size: 18px;'>Problem {current_index + 1} of {total_problems}</p>", unsafe_allow_html=True)
st.markdown("---")

# 5. Display the current problem statement's details
st.header(current_ps['Problem Statement Title'])

st.subheader("General Information")
st.markdown(f"**PS Number:** {current_ps['PS Number']}")
st.markdown(f"**Organization:** {current_ps['Organization']}")
st.markdown(f"**Department:** {current_ps['Department']}")
st.markdown(f"**Category:** {current_ps['Category']}")
st.markdown(f"**Theme:** {current_ps['Theme']}")

# Editable status selector
current_status = df.loc[df['PS Number'] == current_ps['PS Number'], 'Status'].values[0]
new_status = st.selectbox("Update Status", ["Not Reviewed", "Shortlisted", "Rejected", "See Later"], index=["Not Reviewed", "Shortlisted", "Rejected", "See Later"].index(current_status))
if new_status != current_status:
    df.loc[df['PS Number'] == current_ps['PS Number'], 'Status'] = new_status
    df.to_csv("sih_problem_statements_formatted.csv", index=False)
    st.success(f"Status updated to {new_status}")

st.markdown("---")

# Format Description properly with bold headers and bullet points
st.subheader("Description")
description_text = current_ps['Description']

# Add bold headers for common sections
description_text = re.sub(r"(?i)(Problem Statement)", r"**\1**", description_text)
description_text = re.sub(r"(?i)(Background)", r"**\1**", description_text)
description_text = re.sub(r"(?i)(Expected Solution)", r"**\1**", description_text)

# Convert bullet points (•) into Markdown list dashes (-)
description_text = description_text.replace("•", "\n- ")

# Ensure proper line breaks for readability
description_text = description_text.replace(". ", ".\n")

st.markdown(description_text)

# --- 6. Notes Section (Auto-save + Save Button + Copy Prompt) ---
st.subheader("📝 Your Notes")
current_notes = df.loc[df['PS Number'] == current_ps['PS Number'], 'Notes'].values[0]
current_notes = current_notes if pd.notna(current_notes) else ""

# use a persistent key per PS so state is preserved while navigating
notes_key = f"notes_{current_ps['PS Number']}"
last_saved_key = f"last_saved_{current_ps['PS Number']}"

if last_saved_key not in st.session_state:
    st.session_state[last_saved_key] = current_notes

# Text area with session state key only
new_notes = st.text_area("Write your notes here:", value=current_notes, height=120, key=notes_key)

# Auto-save when content changes from last saved value
if new_notes != st.session_state[last_saved_key]:
    df.loc[df['PS Number'] == current_ps['PS Number'], 'Notes'] = new_notes
    df.to_csv("sih_problem_statements_formatted.csv", index=False)
    st.session_state[last_saved_key] = new_notes
    st.success("Notes auto-saved! 📝")

# Save button and copy prompt button on the same line
col_a, col_b = st.columns([4,0.5])
with col_a:
    if st.button("💾 Save Notes", key=f"save_{current_ps['PS Number']}"):
        df.loc[df['PS Number'] == current_ps['PS Number'], 'Notes'] = new_notes
        df.to_csv("sih_problem_statements_formatted.csv", index=False)
        st.session_state[last_saved_key] = new_notes
        st.success("Notes saved successfully!")

# Prepare improved prompt JSON to be copied
prompt = {
    "Idea_Title": current_ps['Problem Statement Title'],
    "PS_Number": current_ps['PS Number'],
    "Organization": current_ps['Organization'],
    "Theme": current_ps['Theme'],
    "Challenge_Summary": current_ps['Description'],
    "Brainstorm_Objective": "Generate innovative, practical, and high-impact features that will make this solution stand out among 500+ submissions in Smart India Hackathon.",
    "Feature_Guidelines": [
        "At least 3-5 UNIQUE features (technical or functional) that other teams are less likely to think of.",
        "Features should balance innovation with feasibility (doable in SIH timeframe).",
        "Emphasize use of cutting-edge tech (AI/ML, IoT, Blockchain, AR/VR, Cloud, Edge, etc.) relevant to the theme.",
        "Include at least one feature focused on scalability, one on user experience, and one on measurable impact."
    ],
    "PPT_Must_Haves": [
        "Problem Background (data/evidence of importance)",
        "Proposed Solution (clear + innovative angle)",
        "Unique Features (highlighted as differentiators)",
        "Tech Stack (modern & feasible)",
        "Implementation Roadmap (timeline for SIH)",
        "Impact (social, economic, or national level)",
        "Future Scope (scalability and sustainability)"
    ],
    "Output_Format": "Give a structured feature list + PPT outline tailored to this specific problem statement."
}
prompt_json = json.dumps(prompt, ensure_ascii=False, indent=2)

# Copy button with pyperclip (reliable)
with col_b:
    if st.button("📋 Copy Prompt", key=f"copy_{current_ps['PS Number']}"):
        try:
            pyperclip.copy(prompt_json)
            st.toast("Prompt copied to clipboard!")
        except Exception as e:
            st.error(f"Copy failed: {e}")

# --- 7. Export Shortlisted Ideas ---
if st.sidebar.button("⬇️ Export Shortlisted"):
    shortlisted_df = df[df['Status'] == "Shortlisted"]
    if not shortlisted_df.empty:
        st.sidebar.download_button(
            label="Download Shortlisted CSV",
            data=shortlisted_df.to_csv(index=False),
            file_name="shortlisted_ideas.csv",
            mime="text/csv"
        )
    else:
        st.sidebar.warning("No shortlisted ideas found.")