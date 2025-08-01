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
    def __init__(self):
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.experience_patterns = [
            r'(\d+)[\s\+]*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'experience[:\s]*(\d+)[\s\+]*(?:years?|yrs?)',
            r'(\d+)[\s\+]*(?:years?|yrs?)',
        ]
        self.tech_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'django', 'flask', 'spring', 'html', 'css', 'sql', 'mongodb',
            'postgresql', 'mysql', 'git', 'docker', 'kubernetes', 'aws',
            'azure', 'gcp', 'machine learning', 'data science', 'ai',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn'
        ]
        self.education_levels = [
            'phd', 'ph.d', 'doctorate', 'masters', 'master', 'mba', 'ms', 'ma',
            'bachelor', 'bachelors', 'bs', 'ba', 'btech', 'be', 'diploma'
        ]

    def extract_text_from_pdf(self, file_bytes):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name
            with open(tmp_file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
            os.unlink(tmp_file_path)
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            return ""

    def extract_text_from_docx(self, file_bytes):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name
            doc = Document(tmp_file_path)
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
            os.unlink(tmp_file_path)
            return text
        except Exception as e:
            st.error(f"Error reading DOCX: {e}")
            return ""

    def extract_email(self, text):
        matches = re.findall(self.email_pattern, text)
        return matches[0].strip() if matches else "N/A"

    def extract_phone(self, text):
        text = text.replace('\u202f', ' ').replace('\xa0', ' ')
        pattern = r'(?:(?:\+|00)?(\d{1,3})[\s\-]*)?(\d{10})\b'
        matches = re.findall(pattern, text)
        for match in matches:
            country_code, number = match
            if number:
                return f"+{country_code} {number}" if country_code else number
        return "N/A"

    def extract_name(self, text):
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line.split()) <= 4 and not any(char.isdigit() for char in line):
                if '@' not in line and 'http' not in line.lower():
                    return line
        return "Unknown"

    def extract_experience_years(self, text):
        text_lower = text.lower()
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                try:
                    years = max([int(match) for match in matches if match.isdigit()])
                    return years
                except:
                    continue
        return self.calculate_experience_from_dates(text)

    def calculate_experience_from_dates(self, text):
        date_patterns = [
            r'(\d{4})\s*[-–]\s*(\d{4})',
            r'(\d{4})\s*[-–]\s*(?:present|current)',
            r'(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})/(\d{4})',
        ]
        total_months = 0
        current_year = datetime.now().year
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 2:
                        start_year = int(match[0])
                        end_year = current_year if 'present' in match[1].lower() else int(match[1])
                        total_months += (end_year - start_year) * 12
                except:
                    continue
        return total_months // 12 if total_months > 0 else 0

    def extract_skills(self, text):
        skill_section = ""
        lines = text.splitlines()
        found = False
        for line in lines:
            if any(h in line.lower() for h in ['skills', 'technical skills', 'skill set']):
                found = True
                continue
            if found:
                if line.strip() == "" or any(h in line.lower() for h in ['experience', 'education', 'projects']):
                    break
                skill_section += line + " "
        found_skills = [skill for skill in self.tech_skills if re.search(rf'\b{skill}\b', skill_section.lower())]
        return sorted(list(set(found_skills)))

    def extract_education(self, text):
        education_section = ""
        lines = text.splitlines()
        found = False
        for line in lines:
            if any(h in line.lower() for h in ['education', 'academic background', 'qualification']):
                found = True
                continue
            if found:
                if line.strip() == "" or any(h in line.lower() for h in ['experience', 'skills', 'projects']):
                    break
                education_section += line + " "
        found_degrees = [deg for deg in self.education_levels if deg in education_section.lower()]
        return sorted(list(set(found_degrees)))

    def parse_resume(self, file_bytes, filename):
        if filename.lower().endswith('.pdf'):
            text = self.extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith(('.docx', '.doc')):
            text = self.extract_text_from_docx(file_bytes)
        else:
            return None
        if not text:
            return None
        return {
            'filename': filename,
            'name': self.extract_name(text),
            'email': self.extract_email(text),
            'phone': self.extract_phone(text),
            'experience_years': self.extract_experience_years(text),
            'skills': self.extract_skills(text),
            'education': self.extract_education(text),
            'raw_text': text[:500] + "..." if len(text) > 500 else text
        }

# Initialize parser
parser = ResumeParser()

# Streamlit App Logic
def main():
    st.title("📄 Resume Parser & Analyzer")
    st.markdown("Upload resumes and ask questions about the data!")

    page = st.sidebar.selectbox("Choose a page", ["Upload & Parse", "Query Data", "View Resumes", "Analytics"])

    if page == "Upload & Parse":
        st.header("Upload Resumes")
        uploaded_files = st.file_uploader("Upload resume files", type=["pdf", "docx", "doc"], accept_multiple_files=True)
        if uploaded_files:
            if st.button("Parse Resumes"):
                for file in uploaded_files:
                    parsed = parser.parse_resume(file.read(), file.name)
                    if parsed:
                        st.session_state.resume_data.append(parsed)
                st.success("Resumes parsed and stored.")
        st.info(f"Total resumes stored: {len(st.session_state.resume_data)}")

    elif page == "Query Data":
        st.header("Ask Questions")
        query = st.text_input("Enter your query")
        if query:
            st.write("**Feature under development.**")

    elif page == "View Resumes":
        st.header("View Parsed Resumes")
        if not st.session_state.resume_data:
            st.warning("No resumes uploaded yet.")
            return
        df = pd.DataFrame([{k: v for k, v in r.items() if k != 'raw_text'} for r in st.session_state.resume_data])
        st.dataframe(df)

    elif page == "Analytics":
        st.header("Analytics")
        if not st.session_state.resume_data:
            st.warning("No data to analyze.")
            return

        df = pd.DataFrame(st.session_state.resume_data)
        st.subheader("Experience Distribution")
        st.bar_chart(df['experience_years'].value_counts().sort_index())

        st.subheader("Top Skills")
        all_skills = [skill for r in st.session_state.resume_data for skill in r['skills']]
        skill_counts = pd.Series(all_skills).value_counts().head(10)
        st.bar_chart(skill_counts)

        st.subheader("Education Distribution")
        all_edu = [edu for r in st.session_state.resume_data for edu in r['education']]
        edu_counts = pd.Series(all_edu).value_counts()
        st.bar_chart(edu_counts)

if __name__ == "__main__":
    main()
