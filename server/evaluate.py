import ast
import re
from pyston import PystonClient, File
import asyncio
import json

def validate_python_code(code):
    """Perform syntax and security validation"""
    try:
        # Syntax validation
        ast.parse(code)
        
        # Security validation (block dangerous constructs)
        forbidden_patterns = [
            r'__import__\s*\(', r'os\.', r'subprocess\.',
            r'open\s*\(', r'eval\s*\(', r'exec\s*\('
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, code):
                return False, "Dangerous code pattern detected"
                
        return True, "Validation passed"
        
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"

def clean_output(output_text):
    """Clean and standardize the output for comparison"""
    # Remove whitespace, normalize newlines
    cleaned = output_text.strip()
    # Handle edge cases based on output format
    return cleaned

async def run_code(code, language, expected_output):
    """Execute code with validation and scoring"""
    if language == "python":
        is_valid, message = validate_python_code(code)
        if not is_valid:
            return {
                "correct": False,
                "message": message,
                "output": None,
                "expected": expected_output,
                "score": 0
            }

        try:
            client = PystonClient()
            result = await client.execute("python", [File(code)])
            
            # Get and clean the output from execution
            actual_output = str(result).strip()
            cleaned_expected = expected_output.strip()
            
            # Compare the actual output with the expected output
            is_correct = actual_output == cleaned_expected
            
            return {
                "correct": is_correct,
                "output": actual_output,
                "expected": cleaned_expected,
                "message": "Code executed successfully" if is_correct else "Output doesn't match expected result",
                "score": 10 if is_correct else 0
            }
            
        except Exception as e:
            return {
                "correct": False,
                "message": f"Execution error: {str(e)}",
                "output": None,
                "expected": expected_output,
                "score": 0
            }
    
    return {
        "correct": False, 
        "message": "Unsupported language", 
        "output": None,
        "expected": expected_output,
        "score": 0
    }