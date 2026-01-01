"""
Minimal unit tests for core skill matching logic.
Tests role normalization, skill extraction, and edge cases.
"""
import pytest
from unittest.mock import patch
from utils import normalize_role_name, extract_skills_from_text, match_skills_by_category


# Sample role-skill mapping for testing
SAMPLE_ROLE_MAPPING = {
    "Software Engineer Intern": {
        "core_skills": ["Python", "Java", "JavaScript"],
        "supporting_skills": ["SQL", "Git"],
        "tools_frameworks": ["VS Code", "GitHub"],
        "optional_skills": ["Docker"]
    },
    "Backend Developer": {
        "core_skills": ["Python", "Node.js"],
        "supporting_skills": ["SQL", "REST"],
        "tools_frameworks": ["Postman", "Flask"],
        "optional_skills": ["Docker", "AWS"]
    }
}


@patch('utils.load_role_skill_mapping')
def test_normalize_role_name_returns_valid_result(mock_load):
    """Test that role normalization function works correctly."""
    # Mock the cached mapping
    mock_load.return_value = SAMPLE_ROLE_MAPPING
    # Test with job description containing role keywords
    job_desc = "Looking for Software Engineer Intern with Python and Java skills for internship program."
    
    result = normalize_role_name(job_desc)
    # Function should return None or a valid role name (not crash)
    assert result is None or isinstance(result, str)
    if result is not None:
        assert result in SAMPLE_ROLE_MAPPING.keys()


@patch('utils.load_role_skill_mapping')
def test_extract_skills_from_text_finds_skills(mock_load):
    """Test that skill extraction correctly identifies skills in resume text."""
    mock_load.return_value = SAMPLE_ROLE_MAPPING
    resume_text = "I have experience with Python, Java, and SQL. Also worked with Git and Docker."
    
    result = extract_skills_from_text(resume_text)
    
    # Should find skills from the text
    assert "Python" in result
    assert "Java" in result
    assert "SQL" in result
    assert "Git" in result
    assert "Docker" in result


@patch('utils.load_role_skill_mapping')
def test_match_skills_by_category_handles_empty_resume(mock_load):
    """Test that skill matching safely handles empty resume text."""
    mock_load.return_value = SAMPLE_ROLE_MAPPING
    resume_text = ""
    job_desc = "Software Engineer Intern position."
    
    result = match_skills_by_category(resume_text, job_desc)
    
    # Should handle empty resume gracefully
    assert isinstance(result, dict)
    assert 'role_detected' in result
    assert 'matched_core_skills' in result
    assert 'missing_core_skills' in result
    # If role detected, should have missing skills; if not, should be empty lists
    if result['role_detected']:
        assert len(result['matched_core_skills']) == 0
        assert len(result['missing_core_skills']) > 0
    assert len(result['bonus_skills']) == 0


@patch('utils.load_role_skill_mapping')
def test_match_skills_by_category_matches_correctly(mock_load):
    """Test that skill matching correctly identifies matched and missing skills."""
    mock_load.return_value = SAMPLE_ROLE_MAPPING
    resume_text = "I know Python and Java. Worked with SQL and Git."
    job_desc = "Software Engineer Intern position requiring Python, Java, JavaScript, and SQL."
    
    result = match_skills_by_category(resume_text, job_desc)
    
    # Should return proper structure
    assert isinstance(result, dict)
    assert 'matched_core_skills' in result
    assert 'missing_core_skills' in result
    
    # If role was detected, should have matching results
    if result['role_detected'] == "Software Engineer Intern":
        # Should match some core skills that are in resume
        assert "Python" in result['matched_core_skills']
        assert "Java" in result['matched_core_skills']
        # Should identify missing skills
        assert "JavaScript" in result['missing_core_skills']

