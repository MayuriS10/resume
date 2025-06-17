import os
import re
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import PyPDF2
from docx import Document
import pandas as pd
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory storage for parsed resumes
resume_data = []

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

    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
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

    def parse_resume(self, file_path, filename):
        """Main function to parse resume and extract information"""
        # Extract text based on file type
        if filename.lower().endswith('.pdf'):
            text = self.extract_text_from_pdf(file_path)
        elif filename.lower().endswith(('.docx', '.doc')):
            text = self.extract_text_from_docx(file_path)
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

@app.route('/')
def index():
    return render_template('index.html', resume_count=len(resume_data))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        flash('No files selected')
        return redirect(request.url)
    
    files = request.files.getlist('files')
    uploaded_count = 0
    
    for file in files:
        if file and file.filename:
            if file.filename.lower().endswith(('.pdf', '.docx', '.doc')):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Parse the resume
                parsed_data = parser.parse_resume(file_path, filename)
                if parsed_data:
                    resume_data.append(parsed_data)
                    uploaded_count += 1
                
                # Clean up uploaded file
                os.remove(file_path)
    
    flash(f'Successfully uploaded and parsed {uploaded_count} resumes')
    return redirect(url_for('index'))

@app.route('/query', methods=['POST'])
def query_resumes():
    query = request.json.get('query', '').lower()
    
    try:
        if 'experience greater than' in query or 'experience > ' in query:
            # Extract the number from query
            numbers = re.findall(r'\d+', query)
            if numbers:
                threshold = int(numbers[0])
                count = sum(1 for resume in resume_data if resume['experience_years'] > threshold)
                return jsonify({
                    'answer': f"{count} persons have experience greater than {threshold} years",
                    'count': count
                })
        
        elif 'experience less than' in query or 'experience < ' in query:
            numbers = re.findall(r'\d+', query)
            if numbers:
                threshold = int(numbers[0])
                count = sum(1 for resume in resume_data if resume['experience_years'] < threshold)
                return jsonify({
                    'answer': f"{count} persons have experience less than {threshold} years",
                    'count': count
                })
        
        elif 'average experience' in query:
            if resume_data:
                avg_exp = sum(resume['experience_years'] for resume in resume_data) / len(resume_data)
                return jsonify({
                    'answer': f"Average experience is {avg_exp:.1f} years",
                    'average': round(avg_exp, 1)
                })
        
        elif 'skill' in query:
            # Extract skill name from query
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
                return jsonify({
                    'answer': f"{count} persons have {skill_mentioned} skill",
                    'count': count
                })
        
        elif 'total count' in query or 'how many resumes' in query:
            return jsonify({
                'answer': f"Total {len(resume_data)} resumes uploaded",
                'count': len(resume_data)
            })
        
        elif 'education' in query:
            education_counts = defaultdict(int)
            for resume in resume_data:
                for edu in resume['education']:
                    education_counts[edu] += 1
            
            if education_counts:
                edu_summary = ", ".join([f"{edu}: {count}" for edu, count in education_counts.items()])
                return jsonify({
                    'answer': f"Education distribution: {edu_summary}",
                    'education_counts': dict(education_counts)
                })
        
        else:
            return jsonify({
                'answer': "I can help you with queries like: 'How many persons have experience greater than 5 years?', 'What is the average experience?', 'How many people have Python skill?', 'Show education distribution'",
                'suggestion': True
            })
    
    except Exception as e:
        return jsonify({
            'answer': f"Error processing query: {str(e)}",
            'error': True
        })

@app.route('/resumes')
def view_resumes():
    return render_template('resumes.html', resumes=resume_data)

@app.route('/clear')
def clear_data():
    global resume_data
    resume_data = []
    flash('All resume data cleared')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)