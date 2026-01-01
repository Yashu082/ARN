import json
import os
import re
from typing import Dict, List, Tuple, Optional

# Load role-skill mapping dataset
ROLE_SKILL_MAPPING_FILE = 'role_skill_mapping.json'

# Global cache for role-skill mapping (loaded once at startup)
_ROLE_SKILL_MAPPING: Optional[Dict] = None

def initialize_role_skill_mapping() -> Dict:
    """
    Load and validate role-skill mapping from JSON file at startup.
    Raises exception if file is missing or invalid.
    """
    global _ROLE_SKILL_MAPPING
    
    if _ROLE_SKILL_MAPPING is not None:
        return _ROLE_SKILL_MAPPING
    
    if not os.path.exists(ROLE_SKILL_MAPPING_FILE):
        raise FileNotFoundError(
            f"CRITICAL: Role-skill mapping file '{ROLE_SKILL_MAPPING_FILE}' not found. "
            f"Please ensure the file exists in the application directory."
        )
    
    try:
        with open(ROLE_SKILL_MAPPING_FILE, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        # Validate structure
        if not isinstance(mapping, dict):
            raise ValueError(
                f"CRITICAL: Invalid format in '{ROLE_SKILL_MAPPING_FILE}'. "
                f"Expected a JSON object (dict), got {type(mapping).__name__}."
            )
        
        if len(mapping) == 0:
            raise ValueError(
                f"CRITICAL: Role-skill mapping file '{ROLE_SKILL_MAPPING_FILE}' is empty. "
                f"At least one role definition is required."
            )
        
        # Validate each role has required structure
        for role_name, role_data in mapping.items():
            if not isinstance(role_data, dict):
                raise ValueError(
                    f"CRITICAL: Invalid role definition for '{role_name}'. "
                    f"Expected a dict, got {type(role_data).__name__}."
                )
        
        _ROLE_SKILL_MAPPING = mapping
        return _ROLE_SKILL_MAPPING
        
    except json.JSONDecodeError as e:
        raise ValueError(
            f"CRITICAL: Invalid JSON in '{ROLE_SKILL_MAPPING_FILE}': {str(e)}. "
            f"Please check the file format and fix any syntax errors."
        )
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise RuntimeError(
            f"CRITICAL: Failed to load role-skill mapping file '{ROLE_SKILL_MAPPING_FILE}': {str(e)}"
        )

def load_role_skill_mapping() -> Dict:
    """
    Get the cached role-skill mapping.
    Returns the mapping loaded at startup.
    """
    if _ROLE_SKILL_MAPPING is None:
        raise RuntimeError(
            "CRITICAL: Role-skill mapping not initialized. "
            "Call initialize_role_skill_mapping() at application startup."
        )
    return _ROLE_SKILL_MAPPING

def normalize_role_name(job_description: str) -> Optional[str]:
    """
    Detect and normalize role name from job description.
    Returns the best matching role name from the dataset, or None if no match.
    """
    job_desc_lower = job_description.lower()
    role_mapping = load_role_skill_mapping()
    
    # Score each role based on keyword matches
    role_scores = {}
    
    for role_name in role_mapping.keys():
        score = 0
        role_lower = role_name.lower()
        
        # Exact role name match gets highest score
        if role_lower in job_desc_lower:
            score += 100
        
        # Check for key terms in role name
        role_terms = role_lower.split()
        for term in role_terms:
            if term in job_desc_lower and len(term) > 3:  # Ignore short words like "a", "an"
                score += 10
        
        # Special handling for "Intern" vs full-time
        if "intern" in job_desc_lower or "internship" in job_desc_lower:
            if "intern" in role_lower:
                score += 50
            elif "intern" not in role_lower and "graduate" not in role_lower and "entry-level" not in role_lower:
                score -= 20
        else:
            # Prefer non-intern roles for full-time positions
            if "intern" not in role_lower:
                score += 30
    
    if not role_scores:
        return None
    
    max_score = max(role_scores.values())
    if max_score == 0:
        return None
    
    # Return role with highest score
    best_role = max(role_scores, key=role_scores.get)
    return best_role if role_scores[best_role] > 0 else None

def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract skills from resume text using case-insensitive string matching.
    Returns a list of matched skill names (normalized to title case).
    """
    text_lower = text.lower()
    role_mapping = load_role_skill_mapping()
    
    # Collect all unique skills from all roles
    all_skills = set()
    for role_data in role_mapping.values():
        for category in ['core_skills', 'supporting_skills', 'tools_frameworks', 'optional_skills']:
            all_skills.update(role_data.get(category, []))
    
    matched_skills = []
    
    # Match skills using case-insensitive search
    for skill in all_skills:
        skill_lower = skill.lower()
        
        # Direct match
        if skill_lower in text_lower:
            matched_skills.append(skill)
        # Match with word boundaries (handles "Python" in "Python3" or "Python developer")
        elif re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower):
            matched_skills.append(skill)
        # Handle variations (e.g., "React.js" vs "React" vs "ReactJS")
        else:
            skill_base = skill_lower.replace('.js', '').replace('.', '').replace(' ', '').replace('-', '')
            text_normalized = text_lower.replace('.js', '').replace('.', '').replace(' ', '').replace('-', '')
            if skill_base in text_normalized and len(skill_base) > 2:
                matched_skills.append(skill)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_skills = []
    for skill in matched_skills:
        if skill not in seen:
            seen.add(skill)
            unique_skills.append(skill)
    
    return unique_skills

def match_skills_by_category(resume_text: str, job_description: str) -> Dict:
    """
    Match skills from resume against role requirements.
    Returns a dictionary with matched and missing skills by category.
    """
    # Detect role from job description
    role_name = normalize_role_name(job_description)
    
    if not role_name:
        # Fallback: use generic matching if role not detected
        return {
            'role_detected': None,
            'matched_core_skills': [],
            'matched_supporting_skills': [],
            'matched_tools_frameworks': [],
            'matched_optional_skills': [],
            'missing_core_skills': [],
            'missing_supporting_skills': [],
            'missing_tools_frameworks': [],
            'bonus_skills': []
        }
    
    # Load role requirements
    role_mapping = load_role_skill_mapping()
    role_requirements = role_mapping.get(role_name, {})
    
    # Extract skills from resume
    resume_skills = extract_skills_from_text(resume_text)
    resume_skills_lower = [s.lower() for s in resume_skills]
    
    # Match by category
    result = {
        'role_detected': role_name,
        'matched_core_skills': [],
        'matched_supporting_skills': [],
        'matched_tools_frameworks': [],
        'matched_optional_skills': [],
        'missing_core_skills': [],
        'missing_supporting_skills': [],
        'missing_tools_frameworks': [],
        'bonus_skills': []
    }
    
    # Helper function to match skills in a category
    def match_category(category_name: str, matched_list: List, missing_list: List):
        required_skills = role_requirements.get(category_name, [])
        for skill in required_skills:
            skill_lower = skill.lower()
            # Check if skill is in resume (with variations)
            found = False
            for resume_skill in resume_skills:
                if skill_lower == resume_skill.lower():
                    found = True
                    matched_list.append(skill)
                    break
                # Handle variations
                skill_base = skill_lower.replace('.js', '').replace('.', '').replace(' ', '').replace('-', '')
                resume_base = resume_skill.lower().replace('.js', '').replace('.', '').replace(' ', '').replace('-', '')
                if skill_base in resume_base or resume_base in skill_base:
                    found = True
                    matched_list.append(skill)
                    break
            
            if not found:
                missing_list.append(skill)
    
    # Match each category
    match_category('core_skills', result['matched_core_skills'], result['missing_core_skills'])
    match_category('supporting_skills', result['matched_supporting_skills'], result['missing_supporting_skills'])
    match_category('tools_frameworks', result['matched_tools_frameworks'], result['missing_tools_frameworks'])
    
    # Optional skills that are matched (bonus)
    optional_skills = role_requirements.get('optional_skills', [])
    for skill in optional_skills:
        skill_lower = skill.lower()
        for resume_skill in resume_skills:
            if skill_lower == resume_skill.lower():
                result['bonus_skills'].append(skill)
                break
            # Handle variations
            skill_base = skill_lower.replace('.js', '').replace('.', '').replace(' ', '').replace('-', '')
            resume_base = resume_skill.lower().replace('.js', '').replace('.', '').replace(' ', '').replace('-', '')
            if skill_base in resume_base or resume_base in skill_base:
                result['bonus_skills'].append(skill)
                break
    
    # Skills in resume that aren't in requirements (also bonus)
    all_required = set()
    for category in ['core_skills', 'supporting_skills', 'tools_frameworks', 'optional_skills']:
        all_required.update(s.lower() for s in role_requirements.get(category, []))
    
    for resume_skill in resume_skills:
        if resume_skill.lower() not in all_required:
            # Check if it's not already in bonus_skills
            if resume_skill not in result['bonus_skills']:
                result['bonus_skills'].append(resume_skill)
    
    return result
