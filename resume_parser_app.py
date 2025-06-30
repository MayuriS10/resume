import streamlit as st
import os
import re
import json
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd
from collections import defaultdict
import tempfile

# Set page config
st.set_page_config(
    page_title="Resume Parser",
    page_icon="📄",
    layout="wide"
)

# Initialize session state for storing resume data
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = []

class ResumeParser:
    ...  # [Same as before; omitted for brevity]

# Initialize parser
parser = ResumeParser()

# Streamlit App
st.title("📄 Resume Parser & Analyzer")
st.markdown("Upload resumes and analyze them with natural language queries.")

menu = st.sidebar.radio("Navigate", ["Upload & Parse", "Query Data", "Analytics"])

if menu == "Upload & Parse":
    uploaded_files = st.file_uploader("Upload Resume Files", type=["pdf", "doc", "docx"], accept_multiple_files=True)

    if uploaded_files and st.button("Parse Resumes"):
        progress = st.progress(0)
        for i, file in enumerate(uploaded_files):
            file_bytes = file.read()
            parsed_data = parser.parse_resume(file_bytes, file.name)
            if parsed_data:
                st.session_state.resume_data.append(parsed_data)
            progress.progress((i + 1) / len(uploaded_files))
        st.success("Parsing Complete!")

    if st.button("Clear All Data"):
        st.session_state.resume_data = []
        st.info("All parsed data has been cleared.")

elif menu == "Query Data":
    if not st.session_state.resume_data:
        st.warning("No resume data available. Please upload files first.")
    else:
        query = st.text_input("Ask a question about the resumes:", placeholder="e.g. How many people have more than 5 years of experience?")

        def process_query(query):
            data = st.session_state.resume_data
            query = query.lower()
            try:
                if "experience greater than" in query:
                    n = int(re.search(r'(\d+)', query).group())
                    count = sum(1 for d in data if d['experience_years'] > n)
                    return f"{count} resumes with more than {n} years of experience"
                elif "experience less than" in query:
                    n = int(re.search(r'(\d+)', query).group())
                    count = sum(1 for d in data if d['experience_years'] < n)
                    return f"{count} resumes with less than {n} years of experience"
                elif "average experience" in query:
                    avg = sum(d['experience_years'] for d in data) / len(data)
                    return f"Average experience is {avg:.2f} years"
                elif "python" in query or "sql" in query or "power bi" in query:
                    skill = query.split()[-1].lower()
                    count = sum(1 for d in data if skill in map(str.lower, d['skills']))
                    return f"{count} resumes mention the skill: {skill}"
                elif "education" in query:
                    edu_count = defaultdict(int)
                    for d in data:
                        for e in d['education']:
                            edu_count[e] += 1
                    return ", ".join([f"{k}: {v}" for k, v in edu_count.items()]) or "No education info found."
                elif "total" in query or "how many" in query:
                    return f"{len(data)} total resumes uploaded"
                else:
                    return "Unsupported query. Try asking about experience, skills, or education."
            except Exception as e:
                return f"Error: {e}"

        if query:
            result = process_query(query)
            st.write("**Result:**", result)

elif menu == "Analytics":
    if not st.session_state.resume_data:
        st.warning("No resume data available. Please upload files first.")
    else:
        df = pd.DataFrame(st.session_state.resume_data)

        st.subheader("Experience Distribution")
        exp_df = df['experience_years'].value_counts().sort_index()
        st.bar_chart(exp_df)

        st.subheader("Top Skills")
        all_skills = sum(df['skills'].tolist(), [])
        skill_series = pd.Series(all_skills)
        top_skills = skill_series.value_counts().head(10)
        st.bar_chart(top_skills)

        st.subheader("Education Distribution")
        all_edu = sum(df['education'].tolist(), [])
        edu_series = pd.Series(all_edu)
        edu_counts = edu_series.value_counts()
        st.bar_chart(edu_counts)

        st.metric("Total Resumes", len(df))
        st.metric("Avg Experience", f"{df['experience_years'].mean():.1f} yrs")
        
if __name__ == "__main__":
    main()
