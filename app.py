from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os
import fitz
from sentence_transformers import SentenceTransformer, util
import logging
from utils import match_skills_by_category, initialize_role_skill_mapping

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'pdf'}
MIN_JOB_DESC_LENGTH = 50
MAX_JOB_DESC_LENGTH = 5000

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_models():
    """Load ML models with error handling"""
    try:
        logger.info("Loading sentence transformer model...")
        model = SentenceTransformer('stsb-roberta-large')
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise RuntimeError(f"Failed to load ML models. Please check your internet connection and try again.")

def extract_text_pymupdf(pdf_path):
    """Extract text from PDF with error handling"""
    try:
        text = ""
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        text = text.strip()
        
        if not text:
            raise ValueError("PDF appears to be empty or contains no extractable text.")
        
        return text
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

# Load role-skill mapping at startup (fail fast if missing/invalid)
try:
    logger.info("Loading role-skill mapping...")
    initialize_role_skill_mapping()
    logger.info("Role-skill mapping loaded successfully")
except Exception as e:
    logger.error(f"CRITICAL: Failed to load role-skill mapping: {str(e)}")
    logger.error("Application cannot start without role-skill mapping file.")
    raise SystemExit(f"Startup failed: {str(e)}")

# Load models at startup
try:
    model = load_models()
except Exception as e:
    logger.error(f"Application startup failed: {str(e)}")
    model = None

@app.route('/')
def index():
    """Render the main upload form"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Process resume and job description to generate match analysis"""
    save_path = None
    
    try:
        # Check if model is loaded
        if model is None:
            return render_template('error.html', 
                message="ML models failed to load. Please restart the application."), 500
        
        # Validate inputs
        if 'resume' not in request.files:
            return render_template('error.html', 
                message="Please upload a resume file."), 400
        
        resume_file = request.files['resume']
        job_desc = request.form.get('job_description', '').strip()
        
        # Validate resume file
        if resume_file.filename == '':
            return render_template('error.html', 
                message="No file selected. Please choose a PDF file."), 400
        
        if not allowed_file(resume_file.filename):
            return render_template('error.html', 
                message="Invalid file type. Please upload a PDF file."), 400
        
        # Validate job description
        if not job_desc:
            return render_template('error.html', 
                message="Job description is required."), 400
        
        if len(job_desc) < MIN_JOB_DESC_LENGTH:
            return render_template('error.html', 
                message=f"Job description is too short. Please provide at least {MIN_JOB_DESC_LENGTH} characters."), 400
        
        if len(job_desc) > MAX_JOB_DESC_LENGTH:
            return render_template('error.html', 
                message=f"Job description is too long. Maximum {MAX_JOB_DESC_LENGTH} characters allowed."), 400
        
        # Check file size
        resume_file.seek(0, os.SEEK_END)
        file_size = resume_file.tell()
        resume_file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return render_template('error.html', 
                message=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."), 400
        
        # Save file
        filename = secure_filename(resume_file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        resume_file.save(save_path)
        
        # Extract text from PDF
        try:
            resume_text = extract_text_pymupdf(save_path)
        except ValueError as e:
            return render_template('error.html', 
                message=str(e)), 400
        
        # Calculate semantic similarity (secondary score)
        try:
            embeddings = model.encode([resume_text, job_desc], convert_to_tensor=True)
            similarity_score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
            semantic_score = round(similarity_score * 100, 2)
        except Exception as e:
            logger.error(f"Model encoding failed: {str(e)}")
            semantic_score = None
            logger.warning("Semantic similarity calculation failed, continuing with skill matching only")
        
        # Match skills using role-skill mapping dataset
        try:
            skill_analysis = match_skills_by_category(resume_text, job_desc)
        except Exception as e:
            logger.error(f"Skill matching failed: {str(e)}")
            return render_template('error.html', 
                message=f"Failed to analyze skills: {str(e)}"), 500
        
        # Generate suggestions based on missing skills
        suggestions = []
        resume_lower = resume_text.lower()
        
        if skill_analysis['missing_core_skills']:
            missing_core = skill_analysis['missing_core_skills'][:3]  # Top 3
            suggestions.append(f"Add core skills: {', '.join(missing_core)}")
        
        if skill_analysis['missing_tools_frameworks']:
            missing_tools = skill_analysis['missing_tools_frameworks'][:3]
            suggestions.append(f"Consider mentioning experience with: {', '.join(missing_tools)}")
        
        if len(resume_text.split()) < 150:
            suggestions.append("Your resume seems short. Add more details about your experience, skills, or projects.")
        
        if not any(heading in resume_lower for heading in ["experience", "work", "project"]):
            suggestions.append("Consider adding an 'Experience' or 'Projects' section to highlight your background.")
        
        if semantic_score and semantic_score < 50:
            suggestions.append("Your resume has a low semantic similarity score. Consider tailoring it more closely to the job description.")
        
        # Calculate overall match score based on comprehensive skill coverage
        # Weight: Core Skills (50%), Supporting Skills (30%), Tools/Frameworks (20%)
        
        # Core skills coverage
        total_core = (len(skill_analysis['matched_core_skills']) + 
                     len(skill_analysis['missing_core_skills']))
        core_coverage = (len(skill_analysis['matched_core_skills']) / total_core * 100) if total_core > 0 else 0
        
        # Supporting skills coverage
        total_supporting = (len(skill_analysis['matched_supporting_skills']) + 
                           len(skill_analysis['missing_supporting_skills']))
        supporting_coverage = (len(skill_analysis['matched_supporting_skills']) / total_supporting * 100) if total_supporting > 0 else 100
        
        # Tools/Frameworks coverage
        total_tools = (len(skill_analysis['matched_tools_frameworks']) + 
                      len(skill_analysis['missing_tools_frameworks']))
        tools_coverage = (len(skill_analysis['matched_tools_frameworks']) / total_tools * 100) if total_tools > 0 else 100
        
        # Weighted skill coverage score
        skill_coverage_score = (
            core_coverage * 0.5 +           # 50% weight on core skills
            supporting_coverage * 0.3 +      # 30% weight on supporting skills
            tools_coverage * 0.2              # 20% weight on tools/frameworks
        )
        
        # Combine skill coverage (60%) and semantic similarity (40%)
        if semantic_score:
            overall_score = round(skill_coverage_score * 0.6 + semantic_score * 0.4, 2)
        else:
            overall_score = round(skill_coverage_score, 2)
        
        return render_template(
            'result.html',
            overall_score=overall_score,
            semantic_score=semantic_score,
            skill_coverage_score=round(skill_coverage_score, 2),
            core_coverage=round(core_coverage, 2),
            supporting_coverage=round(supporting_coverage, 2),
            tools_coverage=round(tools_coverage, 2),
            role_detected=skill_analysis['role_detected'],
            matched_core_skills=skill_analysis['matched_core_skills'],
            matched_supporting_skills=skill_analysis['matched_supporting_skills'],
            matched_tools_frameworks=skill_analysis['matched_tools_frameworks'],
            missing_core_skills=skill_analysis['missing_core_skills'],
            missing_supporting_skills=skill_analysis['missing_supporting_skills'],
            missing_tools_frameworks=skill_analysis['missing_tools_frameworks'],
            bonus_skills=skill_analysis['bonus_skills'][:10],  # Top 10 bonus skills
            suggestions=suggestions
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in analyze route: {str(e)}")
        return render_template('error.html', 
            message="An unexpected error occurred. Please try again."), 500
    
    finally:
        # Clean up uploaded file
        if save_path and os.path.exists(save_path):
            try:
                os.remove(save_path)
                logger.info(f"Cleaned up file: {save_path}")
            except Exception as e:
                logger.warning(f"Failed to delete file {save_path}: {str(e)}")

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return render_template('error.html', 
        message=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."), 413

if __name__ == '__main__':
    # Disable debug mode for production
    app.run(debug=False, host='0.0.0.0', port=5000)
