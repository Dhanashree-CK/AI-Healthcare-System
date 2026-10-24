
from flask import Blueprint
prescription_routes = Blueprint("prescription_routes", __name__)
from flask import Flask, request, render_template_string, send_file, session, redirect, jsonify
import pytesseract
from PIL import Image, ImageEnhance
import io
import re
import datetime
import PyPDF2
from pdf2image import convert_from_bytes
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import tempfile
import json
import hashlib




# Update this path to match your Tesseract installation
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ==================== HISTORY DATABASE ====================
HISTORY_FILE = 'prescription_history.json'

def load_history():
    """Load prescription history from JSON file"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_history(history):
    """Save prescription history to JSON file"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def add_to_history(medicines, summary):
    """Add a new prescription to history"""
    history = load_history()
    
    # Create a unique ID for this prescription
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    prescription_id = f"RX_{timestamp}_{hashlib.md5(summary.encode()).hexdigest()[:6]}"
    
    history_entry = {
        "id": prescription_id,
        "date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "medicines": medicines,
        "summary": summary,
        "medicine_count": len(medicines)
    }
    
    history.append(history_entry)
    save_history(history)
    return prescription_id

def get_history_entry(prescription_id):
    """Get a specific history entry by ID"""
    history = load_history()
    for entry in history:
        if entry["id"] == prescription_id:
            return entry
    return None

# ==================== MEDICINE DATABASE ====================
medicine_db = {
    "amoxicillin": {
        "use": "Bacterial infections", 
        "form": "capsule", 
        "generic": "Amoxicillin", 
        "brands": ["Amoxil", "Mox", "Novamox"],
        "purpose": "Treats various bacterial infections",
        "typical_dosage": "250mg to 500mg",
        "typical_frequency": "Every 8 hours",
        "typical_duration": "5-7 days",
        "price": 70,
        "category": "Antibiotic"
    },

    "ibuprofen": {
        "use": "Pain and inflammation", 
        "form": "tablet", 
        "generic": "Ibuprofen", 
        "brands": ["Brufen", "Advil", "Motrin", "Ibugesic"],
        "purpose": "Reduces inflammation, pain, and fever",
        "typical_dosage": "400mg",
        "typical_frequency": "Every 6-8 hours",
        "typical_duration": "3-5 days",
        "price": 28,
        "category": "Pain Relief"
    },

    "pantoprazole": {
        "use": "Acidity, GERD", 
        "form": "tablet", 
        "generic": "Pantoprazole", 
        "brands": ["Pantocid", "Pan", "PantoKind"],
        "purpose": "Treats acid reflux",
        "typical_dosage": "40mg",
        "typical_frequency": "Once daily",
        "typical_duration": "2-4 weeks",
        "price": 38,
        "category": "Stomach Care"
    },

    "domperidone": {
        "use": "Nausea, vomiting", 
        "form": "tablet", 
        "generic": "Domperidone", 
        "brands": ["Domstal", "Domrid", "Vomistop"],
        "purpose": "Prevents nausea and vomiting",
        "typical_dosage": "10mg",
        "typical_frequency": "Three times daily",
        "typical_duration": "3-5 days",
        "price": 65,
        "category": "Stomach Care"
    },

    "paracetamol": {
        "use": "Fever and mild pain",
        "form": "tablet",
        "generic": "Acetaminophen",
        "brands": ["Crocin", "Calpol", "Dolo"],
        "purpose": "Reduces fever and pain",
        "typical_dosage": "500mg",
        "typical_frequency": "Every 6 hours",
        "typical_duration": "3-5 days",
        "price": 20,
        "category": "Pain Relief"
    }
}

# ==================== TEXT EXTRACTION ====================
def preprocess_image(image):
    """Preprocess image for better OCR accuracy"""
    try:
        if image.mode != 'L':
            image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        image = image.point(lambda x: 0 if x < 140 else 255, '1')
        return image
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        return image

def extract_text_from_pdf(file_content):
    """Extract text from PDF file"""
    try:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if text.strip():
                return text
        except Exception as e:
            print(f"PyPDF2 extraction failed: {str(e)}")
        
        print("Attempting OCR on PDF...")
        poppler_path = r"C:\Users\dshre\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
        poppler_available = os.path.exists(poppler_path)
        
        try:
            if poppler_available:
                images = convert_from_bytes(file_content, poppler_path=poppler_path)
            else:
                images = convert_from_bytes(file_content)
            
            text = ""
            for i, img in enumerate(images):
                img = preprocess_image(img)
                page_text = pytesseract.image_to_string(img)
                text += f"--- Page {i+1} ---\n{page_text}\n"
            return text.strip()
        except Exception as e:
            return f"PDF OCR failed: {str(e)}"
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

def extract_text(file):
    """Extract text from uploaded file"""
    try:
        filename = file.filename.lower()
        print(f"Processing file: {filename}")
        
        file_content = file.read()
        file.seek(0)
        
        if filename.endswith(('.png', '.jpg', '.jpeg', '.jfif')):
            try:
                img = Image.open(io.BytesIO(file_content))
                img = preprocess_image(img)
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(img, config=custom_config)
                return text.strip()
            except Exception as e:
                return f"Error processing image: {str(e)}"
        
        elif filename.endswith('.pdf'):
            return extract_text_from_pdf(file_content)
        else:
            return "Unsupported file format. Please upload PNG, JPG, or PDF."
    except Exception as e:
        return f"Error processing file: {str(e)}"

# ==================== MEDICINE EXTRACTION ====================
def extract_medicine_frequency(text, medicine_name):
    """Extract frequency information for a specific medicine"""
    text_lower = text.lower()
    medicine_lower = medicine_name.lower()
    
    med_pos = text_lower.find(medicine_lower)
    if med_pos == -1:
        return None
    
    context = text_lower[med_pos:med_pos + 150]
    
    freq_patterns = [
        r'(TID|BID|QID|q\d+h|q\.\d+h\.?)',
        r'(every\s+\d+\s*(?:hour|hr)s?)',
        r'(\d+\s*(?:times?)\s*(?:daily|a day))',
        r'(once|twice|thrice)\s*(?:daily|a day)',
    ]
    
    for pattern in freq_patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            freq = match.group(0).strip().upper()
            if freq in ['TID', r'T\.I\.D']:
                return 'Three times daily'
            elif freq in ['BID', r'B\.I\.D']:
                return 'Twice daily'
            elif freq in ['QID', r'Q\.I\.D']:
                return 'Four times daily'
            elif 'Q6H' in freq or 'q6h' in freq.lower():
                return 'Every 6 hours'
            elif 'Q8H' in freq or 'q8h' in freq.lower():
                return 'Every 8 hours'
            return freq
    
    return None

def detect_medicines(text):
    """Enhanced medicine detection with dosage extraction"""
    
    meds = []
    text_lower = text.lower()
    found_medicines = []
    
    print("\nSearching for medicines...")
    
    # Find RX section
    rx_section = re.search(r'RX\n(.*?)(?=Dr\.|Refills|SIGNATURE|$)', text, re.IGNORECASE | re.DOTALL)
    if rx_section:
        rx_text = rx_section.group(1)
        print("Found RX section:", rx_text[:200])
    else:
        rx_text = text
    
    # Look for medicines
    for med in medicine_db:
        if med in rx_text.lower() or any(brand.lower() in rx_text.lower() for brand in medicine_db[med].get("brands", [])):
            if med not in found_medicines:
                found_medicines.append(med)
                print(f"Found medicine: {med}")
                
                # Extract specific dosage
                dosage_match = re.search(fr'{med}.*?(\d+\s*mg)', rx_text, re.IGNORECASE)
                dosage = dosage_match.group(1) if dosage_match else medicine_db[med].get("typical_dosage", "As prescribed")
                
                # Extract frequency
                frequency = extract_medicine_frequency(rx_text, med)
                if not frequency:
                    if 'TID' in rx_text.upper():
                        frequency = 'Three times daily'
                    elif 'BID' in rx_text.upper():
                        frequency = 'Twice daily'
                    elif 'q6h' in rx_text.lower():
                        frequency = 'Every 6 hours'
                    elif 'q8h' in rx_text.lower():
                        frequency = 'Every 8 hours'
                    else:
                        frequency = medicine_db[med].get("typical_frequency", "As prescribed")
                
                # Extract duration
                duration_match = re.search(r'x\s*(\d+\s*days?)', rx_text, re.IGNORECASE)
                duration = duration_match.group(1) if duration_match else medicine_db[med].get("typical_duration", "As prescribed")
                
                meds.append({
                    "name": medicine_db[med].get("generic", med.capitalize()),
                    "purpose": medicine_db[med].get("purpose", "Not specified"),
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": duration,
                    "form": medicine_db[med].get("form", "Tablet")
                })
    
    return meds

# ==================== SUMMARY GENERATION ====================
def generate_comprehensive_summary(medicines, warnings, followup):
    """Creates a comprehensive prescription summary without patient details"""
    
    summary_parts = []
    
    # Header
    summary_parts.append("=" * 80)
    summary_parts.append("🏥 CARE CONNECT AI - PRESCRIPTION ANALYSIS REPORT")
    summary_parts.append("=" * 80)
    summary_parts.append("")
    
    # Diagnosis
    summary_parts.append("🔍 DIAGNOSIS")
    summary_parts.append("-" * 40)
    summary_parts.append("• General consultation")
    summary_parts.append("")
    
    # Medications
    if medicines:
        summary_parts.append("💊 PRESCRIBED MEDICATIONS")
        summary_parts.append("=" * 80)
        summary_parts.append("")
        
        for i, med in enumerate(medicines, 1):
            summary_parts.append(f"📌 MEDICATION #{i}")
            summary_parts.append("-" * 40)
            summary_parts.append(f"💊 Medicine Name  : {med['name']} ({med['form'].capitalize()})")
            summary_parts.append(f"🎯 Purpose/Use    : {med['purpose']}")
            summary_parts.append(f"⚖️  Dosage         : {med['dosage']}")
            summary_parts.append(f"⏰ Frequency      : {med['frequency']}")
            summary_parts.append(f"📆 Duration       : {med['duration']}")
            summary_parts.append("")
    else:
        summary_parts.append("💊 No specific medications detected")
        summary_parts.append("")
    
    # Warnings
    summary_parts.append("⚠️ IMPORTANT WARNINGS & PRECAUTIONS")
    summary_parts.append("-" * 40)
    for warning in warnings[:3]:
        summary_parts.append(f"• {warning}")
    summary_parts.append("")
    
    # Follow-up
    summary_parts.append("📅 FOLLOW-UP ADVICE")
    summary_parts.append("-" * 40)
    for follow in followup:
        summary_parts.append(f"• {follow}")
    summary_parts.append("")
    
    # General Instructions
    summary_parts.append("📋 GENERAL INSTRUCTIONS")
    summary_parts.append("-" * 40)
    summary_parts.append("• Complete the full course of medication")
    summary_parts.append("• Do not skip doses")
    summary_parts.append("• Store medicines as directed on the package")
    summary_parts.append("• Report any side effects to your doctor immediately")
    summary_parts.append("• Keep all medicines out of reach of children")
    summary_parts.append("")
    
    # Footer
    summary_parts.append("=" * 80)
    summary_parts.append(f"📌 Report Generated: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    summary_parts.append("=" * 80)
    summary_parts.append("⚠️ DISCLAIMER: This is an AI-generated summary. Consult your doctor.")
    summary_parts.append("=" * 80)
    
    return "\n".join(summary_parts)

# ==================== PDF GENERATION ====================
def create_pdf_from_summary(summary_text):
    """Create a PDF file from the summary text"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=15
    )
    
    story.append(Paragraph("CARE CONNECT AI - Prescription Summary Report", title_style))
    story.append(Spacer(1, 20))
    
    for line in summary_text.split('\n'):
        if line.strip():
            if line.startswith('='):
                story.append(Paragraph(line, styles['Normal']))
            elif any(icon in line for icon in ['🔍', '💊', '⚠️', '📅', '📋']):
                story.append(Paragraph(line, heading_style))
            elif line.startswith('📌 MEDICATION'):
                story.append(Paragraph(line, styles['Heading3']))
            else:
                story.append(Paragraph(line, styles['Normal']))
        else:
            story.append(Spacer(1, 10))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==================== MAIN HTML TEMPLATE ====================
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>CARE CONNECT AI - Prescription Analyzer</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; }
        .header h1 { color: white; font-size: 3rem; margin-bottom: 10px; }
        .header p { color: rgba(255,255,255,0.9); font-size: 1.2rem; }
        .nav-links {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 30px;
        }
        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 25px;
            transition: all 0.3s;
        }
        .nav-links a:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .main-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .upload-section {
            background: #f8f9fa;
            padding: 40px;
            text-align: center;
            border-bottom: 3px solid #667eea;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 40px;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover { 
            border-color: #764ba2;
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(102,126,234,0.2);
        }
        .upload-icon { font-size: 60px; color: #667eea; margin-bottom: 20px; }
        .upload-area h3 { color: #333; margin-bottom: 10px; }
        .upload-area p { color: #666; }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            background: #667eea;
            color: white;
            margin-top: 20px;
            transition: all 0.3s;
        }
        .btn:hover { 
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102,126,234,0.4);
        }
        .results-section { padding: 40px; }
        .summary-content {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            line-height: 1.6;
            border: 1px solid #ddd;
            max-height: 600px;
            overflow-y: auto;
        }
        .error-message {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .loading { display: none; text-align: center; padding: 40px; }
        .spinner {
            width: 40px; height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .btn-secondary {
            background: #28a745;
        }
        .btn-secondary:hover {
            background: #218838;
        }
        .buy-prompt {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-top: 20px;
        }
        .buy-prompt h3 {
            font-size: 1.5rem;
            margin-bottom: 15px;
        }
        .buy-prompt-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
        }
        .btn-yes {
            background: #28a745;
            padding: 12px 40px;
            font-size: 1.2rem;
        }
        .btn-no {
            background: #dc3545;
            padding: 12px 40px;
            font-size: 1.2rem;
        }
        .view-history-btn {
            background: #17a2b8;
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            display: inline-block;
            margin-top: 10px;
        }
        .view-history-btn:hover {
            background: #138496;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 CARE CONNECT AI</h1>
            <p>Advanced Prescription Analysis System</p>
        </div>
        
        <div class="nav-links">
            <a href="/history">📋 History</a>
        </div>
        
        <div class="main-card">
            <div class="upload-section">
                {% if error %}
                <div class="error-message">{{ error }}</div>
                {% endif %}
                
                <form method="POST" enctype="multipart/form-data" id="uploadForm">
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <div class="upload-icon">📄</div>
                        <h3>Upload Prescription</h3>
                        <p>Click to browse or drag and drop</p>
                        <p style="font-size: 0.9rem; color: #999;">Supported formats: PNG, JPG, PDF</p>
                        <input type="file" name="file" id="fileInput" accept=".png,.jpg,.jpeg,.pdf" style="display: none;" required>
                    </div>
                    <button type="submit" class="btn">Analyze Prescription</button>
                </form>
            </div>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Analyzing prescription... Please wait.</p>
            </div>
            
            {% if summary %}
            <div class="results-section">
                <div class="summary-content" id="summaryText">{{ summary }}</div>
                <div class="button-group">
                    <a href="/download/pdf" class="btn">📥 Download PDF Report</a>
                    <button class="btn btn-secondary" onclick="copyToClipboard()">📋 Copy to Clipboard</button>
                </div>
                
                <!-- Buy Medicine Prompt -->
                <div class="buy-prompt">
                    <h3>🛒 DO YOU WANT TO BUY THE MEDICINES?</h3>
                    <div class="buy-prompt-buttons">
                        <a href="/pharmacy" class="btn btn-yes">YES, Go to Pharmacy</a>
                        <button class="btn btn-no" onclick="closePrompt()">NO, Thanks</button>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="/history" class="view-history-btn">📋 View Prescription History</a>
                </div>
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        document.getElementById('uploadForm').onsubmit = function() {
            document.getElementById('loading').style.display = 'block';
        };
        
        function copyToClipboard() {
            const summaryText = document.getElementById('summaryText').innerText;
            navigator.clipboard.writeText(summaryText).then(function() {
                alert('✅ Summary copied to clipboard!');
            }, function() {
                alert('❌ Failed to copy text');
            });
        }
        
        function closePrompt() {
            const prompt = document.querySelector('.buy-prompt');
            prompt.style.display = 'none';
        }
        
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if(fileName) {
                const uploadArea = document.querySelector('.upload-area h3');
                uploadArea.innerHTML = `Selected: ${fileName}`;
            }
        });
    </script>
</body>
</html>
'''

# ==================== PHARMACY HTML TEMPLATE ====================
PHARMACY_HTML = '''
<!DOCTYPE html>
<html>
<head>
<title>Care Connect Pharmacy</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{
font-family:'Poppins',sans-serif;
background:#f4f6fb;
}
header{
background:linear-gradient(135deg,#4e73df,#1cc88a);
color:white;
padding:25px;
text-align:center;
font-size:28px;
font-weight:600;
}
.nav-links {
    display: flex;
    gap: 20px;
    justify-content: center;
    margin: 20px 0;
}
.nav-links a {
    color: white;
    text-decoration: none;
    padding: 8px 16px;
    background: rgba(255,255,255,0.2);
    border-radius: 20px;
}
.search{
text-align:center;
margin:30px;
}
.search input{
width:60%;
padding:12px;
border-radius:25px;
border:none;
box-shadow:0 4px 10px rgba(0,0,0,0.1);
}
.filters{
text-align:center;
margin-bottom:20px;
}
.filters button{
padding:8px 15px;
margin:5px;
border:none;
border-radius:20px;
background:#4e73df;
color:white;
cursor:pointer;
}
.catalog{
display:grid;
grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
gap:25px;
padding:30px;
max-width:1100px;
margin:auto;
}
.card{
background:white;
border-radius:15px;
padding:20px;
text-align:center;
box-shadow:0 8px 18px rgba(0,0,0,0.08);
}
.card img{
width:60px;
margin-bottom:10px;
}
.card button{
background:#1cc88a;
border:none;
padding:8px 18px;
color:white;
border-radius:20px;
cursor:pointer;
}
.qty{
display:flex;
justify-content:center;
gap:10px;
margin-top:10px;
}
.cart{
background:white;
padding:25px;
margin:30px auto;
max-width:700px;
border-radius:15px;
box-shadow:0 6px 15px rgba(0,0,0,0.08);
}
.cart li{
display:flex;
justify-content:space-between;
margin-bottom:8px;
}
.float-cart{
position:fixed;
bottom:25px;
right:25px;
background:#1cc88a;
color:white;
padding:15px;
border-radius:50%;
font-size:20px;
cursor:pointer;
}
.payment input{
width:100%;
padding:10px;
margin-top:10px;
border-radius:8px;
border:1px solid #ccc;
}
.payment button{
margin-top:15px;
padding:12px;
width:100%;
background:linear-gradient(135deg,#4e73df,#1cc88a);
border:none;
color:white;
border-radius:25px;
}
.qr{
text-align:center;
margin-top:20px;
}
footer{
text-align:center;
padding:20px;
background:#4e73df;
color:white;
margin-top:40px;
}
.back-btn {
    display: inline-block;
    background: #667eea;
    color: white;
    padding: 10px 20px;
    border-radius: 25px;
    text-decoration: none;
    margin: 20px;
}
.prescription-banner {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin: 20px;
    text-align: center;
}
.prescription-meds {
    background: #f0f4f8;
    padding: 15px;
    border-radius: 10px;
    margin: 20px;
}
.med-tag {
    display: inline-block;
    background: #4e73df;
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    margin: 5px;
    font-size: 14px;
}
</style>
</head>
<body>

<div class="nav-links">
    <a href="/history">📋 History</a>
</div>

<a href="/" class="back-btn">← Back to Prescription Analyzer</a>

{% if prescription_medicines %}
<div class="prescription-banner">
    <h3>📋 Medicines from Your Prescription</h3>
    <p>These medicines have been automatically added to your cart</p>
</div>
<div class="prescription-meds">
    {% for med in prescription_medicines %}
    <span class="med-tag">{{ med }}</span>
    {% endfor %}
</div>
{% endif %}

<header>🏥 Care Connect Pharmacy</header>

<div class="search">
<input id="search" placeholder="Search medicines..." onkeyup="searchMed()">
</div>

<div class="filters">
<button onclick="filter('all')">All</button>
<button onclick="filter('pain')">Pain Relief</button>
<button onclick="filter('cold')">Cold & Cough</button>
<button onclick="filter('antibiotic')">Antibiotics</button>
<button onclick="filter('stomach')">Stomach Care</button>
</div>

<div class="catalog" id="catalog"></div>

<div class="cart" id="cart">
<h2>Your Cart</h2>
<ul id="cartItems"></ul>
<p id="total"></p>
<button onclick="showPayment()">Proceed to Payment</button>

<div class="payment" id="paymentBox" style="display:none">
<h3>Delivery Details</h3>
<input placeholder="Full Name" id="name">
<input placeholder="Phone Number" id="phone">
<input placeholder="Delivery Address" id="address">
<input placeholder="Email (for receipt)" id="email">

<h3 style="margin-top:15px;">Payment Method</h3>
<label><input type="radio" name="pay" value="UPI" onchange="selectPayment()"> UPI</label><br>
<label><input type="radio" name="pay" value="Card" onchange="selectPayment()"> Credit / Debit Card</label><br>
<label><input type="radio" name="pay" value="COD" onchange="selectPayment()"> Cash on Delivery</label>

<div id="cardDetails" style="display:none;margin-top:15px;">
<h3>Card Details</h3>
<input placeholder="Cardholder Name" id="cardName">
<input placeholder="Card Number" id="cardNumber">
<input placeholder="Expiry Date (MM/YY)" id="cardExpiry">
<input placeholder="CVV" id="cardCVV">
</div>

<div class="qr" id="qrSection" style="display:none;">
<h3>Scan QR to Pay</h3>
<img id="qrCode" src="" style="width:180px">
<p style="font-size:14px;margin-top:5px;">Scan with UPI app</p>
</div>

<button onclick="payNow()">Confirm Payment</button>
<p id="msg"></p>
</div>
</div>

<div class="float-cart" onclick="document.getElementById('cart').scrollIntoView()">🛒</div>
<footer>© Care Connect Pharmacy</footer>

<script>
const medicines = [
  {name:"Amoxicillin", price:70, cat:"antibiotic"},
  {name:"Ibuprofen", price:28, cat:"pain"},
  {name:"Pantoprazole", price:38, cat:"stomach"},
  {name:"Domperidone", price:65, cat:"stomach"},
  {name:"Paracetamol", price:10, cat:"pain"},
  {name:"Azithromycin", price:95, cat:"antibiotic"},
  {name:"Cetirizine", price:12, cat:"cold"},
  {name:"Metformin", price:55, cat:"diabetes"},
  {name:"Atorvastatin", price:90, cat:"heart"},
  {name:"Losartan", price:60, cat:"heart"},
  {name:"Amlodipine", price:45, cat:"heart"},
  {name:"Ranitidine", price:35, cat:"stomach"},
  {name:"Levocetirizine", price:25, cat:"cold"},
  {name:"Doxycycline", price:75, cat:"antibiotic"},
  {name:"Fluconazole", price:95, cat:"antifungal"},
  {name:"Salbutamol", price:120, cat:"respiratory"},
  {name:"Montelukast", price:110, cat:"respiratory"},
  {name:"Ondansetron", price:70, cat:"stomach"},
  {name:"Diclofenac", price:40, cat:"pain"},
  {name:"Loperamide", price:30, cat:"stomach"},
  {name:"Clotrimazole", price:60, cat:"antifungal"},
  {name:"Hydroxyzine", price:50, cat:"cold"},
  {name:"Ciprofloxacin", price:80, cat:"antibiotic"},
  {name:"Omeprazole", price:40, cat:"stomach"},
  {name:"Naproxen", price:35, cat:"pain"},
  {name:"Tramadol", price:60, cat:"pain"},
  {name:"Lorazepam", price:75, cat:"anxiety"},
  {name:"Diazepam", price:65, cat:"anxiety"},
  {name:"Clonazepam", price:85, cat:"anxiety"},
  {name:"Hydrochlorothiazide", price:45, cat:"heart"},
  {name:"Simvastatin", price:70, cat:"heart"},
  {name:"Rosuvastatin", price:95, cat:"heart"},
  {name:"Levothyroxine", price:55, cat:"thyroid"},
  {name:"Prednisone", price:50, cat:"steroid"},
  {name:"Methylprednisolone", price:85, cat:"steroid"},
  {name:"Gabapentin", price:70, cat:"nerve"},
  {name:"Pregabalin", price:90, cat:"nerve"},
  {name:"Alprazolam", price:65, cat:"anxiety"},
  {name:"Propranolol", price:50, cat:"heart"},
  {name:"Metoprolol", price:55, cat:"heart"},
  {name:"Aspirin", price:25, cat:"heart"},
  {name:"Rivaroxaban", price:150, cat:"heart"},
  {name:"Warfarin", price:120, cat:"heart"},
  {name:"Clopidogrel", price:110, cat:"heart"},
  {name:"Furosemide", price:40, cat:"heart"},
  {name:"Spironolactone", price:50, cat:"heart"},
  {name:"Albuterol", price:110, cat:"respiratory"},
  {name:"Tiotropium", price:180, cat:"respiratory"},
  {name:"Budesonide", price:95, cat:"respiratory"},
  {name:"Fluticasone", price:100, cat:"respiratory"},
  {name:"Prednisolone", price:65, cat:"steroid"},
  {name:"Levocarnitine", price:85, cat:"supplement"},
  {name:"Vitamin D3", price:30, cat:"supplement"},
  {name:"Calcium Carbonate", price:25, cat:"supplement"},
  {name:"Multivitamins", price:50, cat:"supplement"},
  {name:"Iron Folic Acid", price:35, cat:"supplement"},
  {name:"Zinc Sulphate", price:25, cat:"supplement"},
  {name:"Mupirocin", price:90, cat:"antibiotic"},
  {name:"Bacitracin", price:85, cat:"antibiotic"},
  {name:"Neomycin", price:70, cat:"antibiotic"},
  {name:"Ketoconazole", price:95, cat:"antifungal"},
  {name:"Itraconazole", price:120, cat:"antifungal"},
  {name:"Terbinafine", price:100, cat:"antifungal"},
  {name:"Aciclovir", price:110, cat:"antiviral"},
  {name:"Valacyclovir", price:150, cat:"antiviral"},
  {name:"Oseltamivir", price:180, cat:"antiviral"},
  {name:"Metronidazole", price:50, cat:"antibiotic"},
  {name:"Tinidazole", price:65, cat:"antibiotic"},
  {name:"Rifaximin", price:150, cat:"stomach"},
  {name:"Domperidone Syrup", price:70, cat:"stomach"},
  {name:"Esomeprazole", price:85, cat:"stomach"},
  {name:"Rabeprazole", price:95, cat:"stomach"},
  {name:"Dexlansoprazole", price:120, cat:"stomach"},
  {name:"Sodium Bicarbonate", price:20, cat:"stomach"},
  {name:"Dextromethorphan", price:35, cat:"cold"},
  {name:"Ambroxol", price:40, cat:"cold"},
  {name:"Guaifenesin", price:50, cat:"cold"},
  {name:"Phenylephrine", price:25, cat:"cold"},
  {name:"Pseudoephedrine", price:30, cat:"cold"},
  {name:"Cetirizine + Montelukast", price:60, cat:"cold"},
  {name:"Levocetirizine + Montelukast", price:65, cat:"cold"},
  {name:"Olanzapine", price:200, cat:"psychiatric"},
  {name:"Risperidone", price:180, cat:"psychiatric"},
  {name:"Quetiapine", price:220, cat:"psychiatric"},
  {name:"Aripiprazole", price:250, cat:"psychiatric"},
  {name:"Haloperidol", price:160, cat:"psychiatric"},
  {name:"Lithium Carbonate", price:300, cat:"psychiatric"},
  {name:"Sertraline", price:150, cat:"psychiatric"},
  {name:"Fluoxetine", price:130, cat:"psychiatric"},
  {name:"Escitalopram", price:140, cat:"psychiatric"},
  {name:"Paroxetine", price:130, cat:"psychiatric"},
  {name:"Citalopram", price:120, cat:"psychiatric"},
  {name:"Clobazam", price:110, cat:"psychiatric"},
  {name:"Topiramate", price:150, cat:"nerve"},
  {name:"Valproate", price:200, cat:"nerve"},
  {name:"Carbamazepine", price:180, cat:"nerve"},
  {name:"Phenytoin", price:120, cat:"nerve"},
  {name:"Levetiracetam", price:250, cat:"nerve"},
  {name:"Lamotrigine", price:200, cat:"nerve"},
  {name:"Donepezil", price:180, cat:"nerve"},
  {name:"Rivastigmine", price:190, cat:"nerve"},
  {name:"Memantine", price:200, cat:"nerve"},
  {name:"Betahistine", price:150, cat:"nerve"}
];

let cart = {};

// Load prescription medicines into cart
{% if prescription_medicines %}
    {% for med in prescription_medicines %}
        cart['{{ med }}'] = (cart['{{ med }}'] || 0) + 1;
    {% endfor %}
{% endif %}

let current = medicines;

function load(list){
let html = "";
list.forEach(m=>{
let q = cart[m.name] || 0;
html += `
<div class="card">
<img src="https://cdn-icons-png.flaticon.com/512/4320/4320371.png">
<h3>${m.name}</h3>
<p>₹${m.price}</p>
${ q == 0 ?
`<button onclick="add('${m.name}')">Add</button>` :
`<div class="qty">
<button onclick="dec('${m.name}')">-</button>
<span>${q}</span>
<button onclick="inc('${m.name}')">+</button>
</div>` }
</div>`;
});
document.getElementById("catalog").innerHTML = html;
}

function add(n){cart[n]=1;showCart();load(current);}
function inc(n){cart[n]++;showCart();load(current);}
function dec(n){cart[n]--;if(cart[n]==0)delete cart[n];showCart();load(current);}

function showCart(){
let list = "";
let total = 0;
for(let item in cart){
let med = medicines.find(m=>m.name==item);
let cost = med.price * cart[item];
total += cost;
list += `<li>${item} x${cart[item]} <span>₹${cost}</span></li>`;
}
document.getElementById("cartItems").innerHTML = list;
document.getElementById("total").innerHTML = "<b>Total: ₹"+total+"</b>";
}

function searchMed(){
let s = document.getElementById("search").value.toLowerCase();
current = medicines.filter(m=>m.name.toLowerCase().includes(s));
load(current);
}

function filter(cat){
if(cat=="all") current = medicines;
else current = medicines.filter(m=>m.cat==cat);
load(current);
}

function showPayment(){
if(Object.keys(cart).length==0){
alert("Cart empty");
return;
}
document.getElementById("paymentBox").style.display = "block";
}

function selectPayment(){
let method = document.querySelector('input[name="pay"]:checked').value;
document.getElementById("cardDetails").style.display = "none";
document.getElementById("qrSection").style.display = "none";
if(method=="Card"){
document.getElementById("cardDetails").style.display = "block";
}
if(method=="UPI"){
document.getElementById("qrSection").style.display = "block";
let total = 0;
for(let item in cart){
let med = medicines.find(m=>m.name==item);
total += med.price * cart[item];
}
document.getElementById("qrCode").src =
"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa=careconnect@upi&pn=CareConnect&am="+total;
}
}

function payNow(){
let name = document.getElementById("name").value;
let phone = document.getElementById("phone").value;
let address = document.getElementById("address").value;
let email = document.getElementById("email").value;
let method = document.querySelector('input[name="pay"]:checked');
if(!name||!phone||!address||!email||!method){
alert("Fill all details");
return;
}
let order = "CC"+Math.floor(Math.random()*10000);
document.getElementById("msg").innerHTML =
"Payment Successful ✅ <br><br>"+
"Order ID: "+order+"<br>"+
"Payment Mode: "+method.value+"<br>"+
"Receipt sent to: "+email;
cart = {};
showCart();
load(current);
}

// Initial load
load(medicines);
showCart();
</script>
</body>
</html>
'''

# ==================== HISTORY HTML TEMPLATE ====================
HISTORY_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>CARE CONNECT AI - Prescription History</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 40px; }
        .header h1 { color: white; font-size: 3rem; margin-bottom: 10px; }
        .header p { color: rgba(255,255,255,0.9); font-size: 1.2rem; }
        .nav-links {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 30px;
        }
        .nav-links a {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 25px;
            transition: all 0.3s;
        }
        .nav-links a:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .main-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            overflow: hidden;
            padding: 30px;
        }
        .history-table {
            width: 100%;
            border-collapse: collapse;
        }
        .history-table th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }
        .history-table td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        .history-table tr:hover {
            background: #f5f5f5;
        }
        .view-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 15px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        .view-btn:hover {
            background: #218838;
        }
        .delete-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 14px;
        }
        .delete-btn:hover {
            background: #c82333;
        }
        .empty-history {
            text-align: center;
            padding: 50px;
            color: #666;
        }
        .back-btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            margin-top: 20px;
        }
        .back-btn:hover {
            background: #764ba2;
        }
        .medicine-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        .medicine-tag {
            background: #e9ecef;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Prescription History</h1>
            <p>View all your past prescriptions</p>
        </div>
        
        <div class="nav-links">
            <a href="/">🏠 Home</a>
            <a href="/history">📋 History</a>
        </div>
        
        <div class="main-card">
            {% if history %}
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Date & Time</th>
                        <th>Medicines</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for entry in history %}
                    <tr>
                        <td>{{ entry.date }}</td>
                        <td>
                            <div class="medicine-tags">
                                {% for med in entry.medicines[:3] %}
                                <span class="medicine-tag">{{ med }}</span>
                                {% endfor %}
                                {% if entry.medicines|length > 3 %}
                                <span class="medicine-tag">+{{ entry.medicines|length - 3 }} more</span>
                                {% endif %}
                            </div>
                        </td>
                        <td>
                            <a href="/history/{{ entry.id }}" class="view-btn">View</a>
                            <button class="delete-btn" onclick="deleteEntry('{{ entry.id }}')">Delete</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-history">
                <h3>No prescription history yet</h3>
                <p>Upload and analyze your first prescription to see it here!</p>
                <a href="/" class="back-btn">Go to Upload</a>
            </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        function deleteEntry(id) {
            if(confirm('Are you sure you want to delete this prescription?')) {
                fetch('/history/delete/' + id, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if(data.success) {
                        location.reload();
                    } else {
                        alert('Error deleting entry');
                    }
                });
            }
        }
    </script>
</body>
</html>
'''

# ==================== FLASK ROUTES ====================
@prescription_routes.route("/download/pdf")
def download_pdf():
    if 'last_summary' in session:
        pdf_buffer = create_pdf_from_summary(session['last_summary'])
        filename = f"prescription_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    return "No summary available", 404

@prescription_routes.route("/pharmacy")
def pharmacy():
    medicines = session.get('detected_medicines', [])
    return render_template_string(PHARMACY_HTML, prescription_medicines=medicines)

@prescription_routes.route("/history")
def history():
    """View prescription history"""
    history_data = load_history()
    # Sort by date (newest first)
    history_data.sort(key=lambda x: x['date'], reverse=True)
    return render_template_string(HISTORY_HTML, history=history_data)

@prescription_routes.route("/history/<prescription_id>")
def view_history_entry(prescription_id):
    """View a specific history entry"""
    entry = get_history_entry(prescription_id)
    if entry:
        return render_template_string(HTML, summary=entry['summary'])
    return "Prescription not found", 404

@prescription_routes.route("/history/delete/<prescription_id>", methods=["POST"])
def delete_history_entry(prescription_id):
    """Delete a history entry"""
    history = load_history()
    history = [entry for entry in history if entry["id"] != prescription_id]
    save_history(history)
    return jsonify({"success": True})

@prescription_routes.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if 'file' not in request.files:
            return render_template_string(HTML, error="No file selected")
        
        file = request.files["file"]
        
        if file.filename == '':
            return render_template_string(HTML, error="Please select a file")
        
        allowed_extensions = ('.png', '.jpg', '.jpeg', '.pdf')
        if not file.filename.lower().endswith(allowed_extensions):
            return render_template_string(HTML, error="Unsupported file format. Please upload PNG, JPG, or PDF.")
        
        text = extract_text(file)
        
        if text.startswith("Error"):
            return render_template_string(HTML, error=text)
        
        if text.strip():
            print("\n===== EXTRACTED TEXT =====")
            print(text)
            print("=========================\n")
            
            medicines = detect_medicines(text)
            warnings = ["Take as prescribed", "Complete the full course"]
            followup = ["Follow up as advised by doctor"]
            
            medicine_names = [med['name'] for med in medicines]
            session['detected_medicines'] = medicine_names
            
            summary = generate_comprehensive_summary(
                medicines, warnings, followup
            )
            
            # Add to history
            add_to_history(medicine_names, summary)
            
            session['last_summary'] = summary
            return render_template_string(HTML, summary=summary)
        else:
            return render_template_string(HTML, error="No text could be extracted. Please try a clearer image.")
    
    return render_template_string(HTML)


