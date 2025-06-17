import streamlit as st
import PyPDF2
from docx import Document
import pandas as pd
import re

st.set_page_config(page_title="Resume Parser", layout="wide")

class ResumeParser:
    def __init__(self):
        self.email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        self.phone_pattern = r'(\+?\d{1,4}[\s-]?)?\(?\d{3,5}\)?[\s-]?\d{3,5}[\s-]?\d{3,5}'
        self.education_keywords = [
            "phd", "ph.d", "doctorate", "mba", "master", "m.sc", "mtech", "ms",
            "bachelor", "b.sc", "btech", "be", "bs", "ba", "b.com", "bca", "bba",
            "mca", "10th", "12th", "ssc", "hsc", "intermediate", "graduation", "post graduation"
        ]
        self.skill_keywords = [
            "python", "sql", "excel", "r", "java", "c++", "tableau", "power bi",
            "machine learning", "deep learning", "aws", "azure", "gcp", "flask",
            "django", "html", "css", "javascript", "spark", "hadoop", "pandas",
            "numpy", "scikit-learn", "matplotlib", "seaborn", "tensorflow", "keras"
        ]

    def extract_text(self, file, filename):
        try:
            if filename.endswith('.pdf'):
                reader = PyPDF2.PdfReader(file)
                return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            elif filename.endswith(('.docx', '.doc')):
                doc = Document(file)
                return "\n".join([p.text for p in doc.paragraphs])
        except:
            return ""
        return ""

    def extract_email(self, text):
        matches = re.findall(self.email_pattern, text)
        return matches[0] if matches else "N/A"

    def extract_phone(self, text):
        matches = re.findall(self.phone_pattern, text)
        flat_numbers = [''.join(m).strip() for m in matches]
        flat_numbers = [re.sub(r'\D', '', num) for num in flat_numbers if 10 <= len(re.sub(r'\D', '', num)) <= 15]
        return flat_numbers[0] if flat_numbers else "N/A"

    def extract_name(self, text):
        lines = text.strip().split("\n")
        for line in lines[:5]:
            if line.strip() and len(line.strip().split()) <= 4 and '@' not in line and not any(char.isdigit() for char in line):
                return line.strip()
        return "Unknown"

    def extract_experience(self, text):
        matches = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', text.lower())
        return max(map(int, matches)) if matches else 0

    def extract_education(self, text):
        text_lower = text.lower()
        found = [edu for edu in self.education_keywords if edu in text_lower]
        return list(set(found)) if found else []

    def extract_skills(self, text):
        text_lower = text.lower()
        found = [skill for skill in self.skill_keywords if re.search(r'\b' + re.escape(skill) + r'\b', text_lower)]
        return list(set(found)) if found else []

    def parse(self, file, filename):
        text = self.extract_text(file, filename)
        return {
            "name": self.extract_name(text),
            "email": self.extract_email(text),
            "phone": self.extract_phone(text),
            "experience": self.extract_experience(text),
            "skills": self.extract_skills(text),
            "education": self.extract_education(text),
            "filename": filename
        }

# Streamlit UI
st.title("📄 Resume Parser App")
uploaded_files = st.file_uploader("Upload Resumes (.pdf/.docx)", type=["pdf", "docx"], accept_multiple_files=True)

parser = ResumeParser()
parsed_data = []

if uploaded_files:
    for file in uploaded_files:
        parsed = parser.parse(file, file.name)
        parsed_data.append(parsed)

    df = pd.DataFrame(parsed_data)
    st.subheader("🧾 Parsed Resume Data")
    st.dataframe(df)

    st.subheader("🔍 Ask a Question")
    query = st.text_input("E.g., experience greater than 5, show emails, show education")

    if query:
        query = query.lower()
        if "experience greater than" in query:
            num = int(re.findall(r'\d+', query)[0])
            result = df[df["experience"] > num]
            st.write(result)
            st.success(f"{len(result)} person(s) have more than {num} years of experience.")
        elif "experience less than" in query:
            num = int(re.findall(r'\d+', query)[0])
            result = df[df["experience"] < num]
            st.write(result)
            st.success(f"{len(result)} person(s) have less than {num} years of experience.")
        elif "average experience" in query:
            avg = df["experience"].mean()
            st.success(f"Average experience is {avg:.2f} years.")
        elif "skills" in query:
            st.dataframe(df[["name", "skills"]])
        elif "education" in query:
            st.dataframe(df[["name", "education"]])
        elif "email" in query:
            st.dataframe(df[["name", "email"]])
        elif "phone" in query:
            st.dataframe(df[["name", "phone"]])
        else:
            st.warning("Try questions like: 'experience greater than 5', 'show skills', 'show education'")
