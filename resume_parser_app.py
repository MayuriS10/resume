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
        # Common patterns for extraction
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.experience_patterns = [
            r'(\d+)[\s\+]*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'experience[:\s]*(\d+)[\s\+]*(?:years?|yrs?)',
            r'(\d+)[\s\+]*(?:years?|yrs?)',
        ]
        
        # Skills keywords
        self.tech_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'django', 'flask', 'spring', 'html', 'css', 'sql', 'mongodb',
            'postgresql', 'mysql', 'git', 'docker', 'kubernetes', 'aws',
            'azure', 'gcp', 'machine learning', 'data science', 'ai',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn'
        ]
        
        # Education keywords
        self.education_levels = [
            'phd', 'ph.d', 'doctorate', 'masters', 'master', 'mba', 'ms', 'ma',
            'bachelor', 'bachelors', 'bs', 'ba', 'btech', 'be', 'diploma'
        ]

    def extract_text_from_pdf(self, file_bytes):
        """Extract text from PDF file bytes"""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            return ""

    def extract_text_from_docx(self, file_bytes):
        """Extract text from DOCX file bytes"""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name
            
            doc = Document(tmp_file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            return text
        except Exception as e:
            st.error(f"Error reading DOCX: {e}")
            return ""

    def extract_email(self, text):
        """Extract email addresses from text"""
        emails = re.findall(self.email_pattern, text, re.IGNORECASE)
        return emails[0] if emails else None

    def extract_phone(self, text):
        """Extract phone numbers from text"""
        phones = re.findall(self.phone_pattern, text)
        return phones[0] if phones else None

    def extract_name(self, text):
        """Extract name (simple heuristic - first line or first few words)"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line.split()) <= 4 and not any(char.isdigit() for char in line):
                if '@' not in line and 'http' not in line.lower():
                    return line
        return "Unknown"

    def extract_experience_years(self, text):
        """Extract years of experience from text"""
        text_lower = text.lower()
        
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                try:
                    years = max([int(match) for match in matches if match.isdigit()])
                    return years
                except:
                    continue
        
        # Try to find experience section and calculate from dates
        experience_years = self.calculate_experience_from_dates(text)
        return experience_years

    def calculate_experience_from_dates(self, text):
        """Calculate experience from date ranges in text"""
        date_patterns = [
            r'(\d{4})\s*[-–]\s*(\d{4})',  # 2020-2023
            r'(\d{4})\s*[-–]\s*(?:present|current)',  # 2020-present
            r'(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})/(\d{4})',  # 01/2020-12/2023
        ]
        
        total_months = 0
        current_year = datetime.now().year
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 2:  # Year-Year format
                        start_year = int(match[0])
                        if 'present' in match[1].lower() or 'current' in match[1].lower():
                            end_year = current_year
                        else:
                            end_year = int(match[1])
                        total_months += (end_year - start_year) * 12
                except:
                    continue
        
        return total_months // 12 if total_months > 0 else 0

    def extract_skills(self, text):
        """Extract technical skills from text"""
        text_lower = text.lower()
        found_skills = []
        
        for skill in self.tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills

    def extract_education(self, text):
        """Extract education information"""
        text_lower = text.lower()
        education_info = []
        
        for level in self.education_levels:
            if level in text_lower:
                education_info.append(level)
        
        return education_info

    def parse_resume(self, file_bytes, filename):
        """Main function to parse resume and extract information"""
        # Extract text based on file type
        if filename.lower().endswith('.pdf'):
            text = self.extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith(('.docx', '.doc')):
            text = self.extract_text_from_docx(file_bytes)
        else:
            return None
        
        if not text:
            return None
        
        # Extract information
        parsed_data = {
            'filename': filename,
            'name': self.extract_name(text),
            'email': self.extract_email(text),
            'phone': self.extract_phone(text),
            'experience_years': self.extract_experience_years(text),
            'skills': self.extract_skills(text),
            'education': self.extract_education(text),
            'raw_text': text[:500] + "..." if len(text) > 500 else text  # Store first 500 chars
        }
        
        return parsed_data

# Initialize parser
parser = ResumeParser()

def process_query(query):
    """Process natural language queries about the resume data"""
    query = query.lower()
    resume_data = st.session_state.resume_data
    
    try:
        if 'experience greater than' in query or 'experience > ' in query:
            numbers = re.findall(r'\d+', query)
            if numbers:
                threshold = int(numbers[0])
                count = sum(1 for resume in resume_data if resume['experience_years'] > threshold)
                return f"{count} persons have experience greater than {threshold} years"
        
        elif 'experience less than' in query or 'experience < ' in query:
            numbers = re.findall(r'\d+', query)
            if numbers:
                threshold = int(numbers[0])
                count = sum(1 for resume in resume_data if resume['experience_years'] < threshold)
                return f"{count} persons have experience less than {threshold} years"
        
        elif 'average experience' in query:
            if resume_data:
                avg_exp = sum(resume['experience_years'] for resume in resume_data) / len(resume_data)
                return f"Average experience is {avg_exp:.1f} years"
            else:
                return "No resume data available"
        
        elif 'skill' in query:
            skill_mentioned = None
            for resume in resume_data:
                for skill in resume['skills']:
                    if skill.lower() in query:
                        skill_mentioned = skill
                        break
                if skill_mentioned:
                    break
            
            if skill_mentioned:
                count = sum(1 for resume in resume_data if skill_mentioned.lower() in [s.lower() for s in resume['skills']])
                return f"{count} persons have {skill_mentioned} skill"
            else:
                return "Skill not found in the query or resume data"
        
        elif 'total count' in query or 'how many resumes' in query:
            return f"Total {len(resume_data)} resumes uploaded"
        
        elif 'education' in query:
            education_counts = defaultdict(int)
            for resume in resume_data:
                for edu in resume['education']:
                    education_counts[edu] += 1
            
            if education_counts:
                edu_summary = ", ".join([f"{edu}: {count}" for edu, count in education_counts.items()])
                return f"Education distribution: {edu_summary}"
            else:
                return "No education data found"
        
        else:
            return "I can help you with queries like: 'How many persons have experience greater than 5 years?', 'What is the average experience?', 'How many people have Python skill?', 'Show education distribution'"
    
    except Exception as e:
        return f"Error processing query: {str(e)}"

# Main Streamlit App
def main():
    st.title("📄 Resume Parser & Analyzer")
    st.markdown("Upload resumes and ask questions about the data!")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Upload & Parse", "Query Data", "View Resumes", "Analytics"])
    
    if page == "Upload & Parse":
        st.header("Upload Resumes")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose resume files",
            type=['pdf', 'docx', 'doc'],
            accept_multiple_files=True,
            help="Upload PDF or Word documents"
        )
        
        if uploaded_files:
            if st.button("Parse Resumes"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                parsed_count = 0
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name}...")
                    
                    # Read file bytes
                    file_bytes = file.read()
                    
                    # Parse the resume
                    parsed_data = parser.parse_resume(file_bytes, file.name)
                    if parsed_data:
                        st.session_state.resume_data.append(parsed_data)
                        parsed_count += 1
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text(f"✅ Successfully parsed {parsed_count} out of {len(uploaded_files)} resumes!")
                st.success(f"Uploaded and parsed {parsed_count} resumes successfully!")
        
        # Display current count
        st.info(f"Currently have {len(st.session_state.resume_data)} resumes in the database")
        
        # Clear data button
        if st.button("Clear All Data", type="secondary"):
            st.session_state.resume_data = []
            st.success("All resume data cleared!")
    
    elif page == "Query Data":
        st.header("Query Resume Data")
        
        if not st.session_state.resume_data:
            st.warning("No resume data available. Please upload resumes first.")
            return
        
        # Query input
        query = st.text_input(
            "Ask a question about the resume data:",
            placeholder="e.g., How many persons have experience greater than 5 years?"
        )
        
        if query:
            answer = process_query(query)
            st.write("**Answer:**", answer)
        
        # Example queries
        st.subheader("Example Queries:")
        example_queries = [
            "How many persons have experience greater than 5 years?",
            "What is the average experience?",
            "How many people have Python skill?",
            "Show education distribution",
            "Total count of resumes"
        ]
        
        for eq in example_queries:
            if st.button(eq, key=f"example_{eq}"):
                answer = process_query(eq)
                st.write("**Answer:**", answer)
    
    elif page == "View Resumes":
        st.header("Resume Database")
        
        if not st.session_state.resume_data:
            st.warning("No resume data available. Please upload resumes first.")
            return
        
        # Create DataFrame for better display
        df_data = []
        for resume in st.session_state.resume_data:
            df_data.append({
                'Name': resume['name'],
                'Email': resume['email'] or 'N/A',
                'Phone': resume['phone'] or 'N/A',
                'Experience (Years)': resume['experience_years'],
                'Skills': ', '.join(resume['skills'][:3]) + ('...' if len(resume['skills']) > 3 else ''),
                'Education': ', '.join(resume['education']) if resume['education'] else 'N/A',
                'Filename': resume['filename']
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Detailed view
        st.subheader("Detailed View")
        selected_resume = st.selectbox("Select a resume to view details:", 
                                     [r['filename'] for r in st.session_state.resume_data])
        
        if selected_resume:
            resume = next(r for r in st.session_state.resume_data if r['filename'] == selected_resume)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Name:**", resume['name'])
                st.write("**Email:**", resume['email'] or 'N/A')
                st.write("**Phone:**", resume['phone'] or 'N/A')
                st.write("**Experience:**", f"{resume['experience_years']} years")
            
            with col2:
                st.write("**Skills:**")
                if resume['skills']:
                    for skill in resume['skills']:
                        st.write(f"• {skill}")
                else:
                    st.write("No skills identified")
                
                st.write("**Education:**")
                if resume['education']:
                    for edu in resume['education']:
                        st.write(f"• {edu}")
                else:
                    st.write("No education identified")
            
            st.write("**Resume Preview:**")
            st.text_area("", resume['raw_text'], height=200, disabled=True)
    
    elif page == "Analytics":
        st.header("Resume Analytics")
        
        if not st.session_state.resume_data:
            st.warning("No resume data available. Please upload resumes first.")
            return
        
        # Basic statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Resumes", len(st.session_state.resume_data))
        
        with col2:
            avg_exp = sum(r['experience_years'] for r in st.session_state.resume_data) / len(st.session_state.resume_data)
            st.metric("Avg Experience", f"{avg_exp:.1f} years")
        
        with col3:
            emails_count = sum(1 for r in st.session_state.resume_data if r['email'])
            st.metric("Emails Found", emails_count)
        
        with col4:
            phones_count = sum(1 for r in st.session_state.resume_data if r['phone'])
            st.metric("Phones Found", phones_count)
        
        # Experience distribution
        st.subheader("Experience Distribution")
        exp_data = [r['experience_years'] for r in st.session_state.resume_data]
        st.bar_chart(pd.DataFrame({'Experience (Years)': exp_data}).value_counts().sort_index())
        
        # Skills analysis
        st.subheader("Top Skills")
        all_skills = []
        for resume in st.session_state.resume_data:
            all_skills.extend(resume['skills'])
        
        if all_skills:
            skill_counts = pd.Series(all_skills).value_counts().head(10)
            st.bar_chart(skill_counts)
        
        # Education analysis
        st.subheader("Education Distribution")
        all_education = []
        for resume in st.session_state.resume_data:
            all_education.extend(resume['education'])
        
        if all_education:
            edu_counts = pd.Series(all_education).value_counts()
            st.bar_chart(edu_counts)

if __name__ == "__main__":
    main()