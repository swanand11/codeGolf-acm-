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
    return output_text.strip()

def calculate_score(base_score, code_length, target_chars):
    """Calculate the final score based on code length and target character count"""
    if code_length <= target_chars:
        return base_score, f"Perfect! You hit the target of {target_chars} characters or fewer."
    else:
        percentage_over = (code_length - target_chars) / target_chars * 100
        penalty = int(percentage_over / 10)
        final_score = max(1, base_score - penalty)
        return final_score, f"Your solution is {percentage_over:.1f}% over the target ({code_length}/{target_chars} chars). Penalty: -{penalty} points."

async def validate_test_cases(code, language, question_id):
    """Validate the submitted code against all test cases for the given question."""
    try:
        # Load test cases from testcases.json
        with open("static/testcases.json", "r") as file:
            testcases = json.load(file)
        
        # Get test cases for the given question ID
        question_testcases = testcases.get(str(question_id), [])
        if not question_testcases:
            return False, "No test cases found for this question."
        
        # Initialize PystonClient
        client = PystonClient()
        
        # Validate each test case
        for testcase in question_testcases:
            input_data = testcase["input"]
            expected_output = testcase["expected_output"]
            
            # Execute the code with the given input
            try:
                result = await client.execute(language, [File(code)], stdin=input_data)
                actual_output = clean_output(str(result))
                
                # Compare the actual output with the expected output
                if actual_output != expected_output:
                    return False, f"Test case failed."
            except Exception as e:
                return False, f"Execution error for input {input_data}: {str(e)}"
        
        # All test cases passed
        return True, "All test cases passed."
    
    except Exception as e:
        return False, f"Error validating test cases: "

async def run_code(code, language, expected_output, question_id):
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

        # Validate test cases
        test_cases_passed, test_case_message = await validate_test_cases(code, language, question_id)
        if not test_cases_passed:
            return {
                "correct": False,
                "message": test_case_message,
                "output": None,
                "expected": expected_output,
                "score": 0
            }

        # If all test cases pass, calculate the score
        try:
            with open("templates/questions.json", "r") as file:
                questions = json.load(file)
                question = next((q for q in questions if q["id"] == question_id), None)
                if not question:
                    return {"correct": False, "message": "Question not found.", "score": 0}
                
                base_score = question["base_score"]
                target_chars = question["target_chars"]
                code_length = len(re.sub(r'#.*|[\s]', '', code))
                
                final_score, score_message = calculate_score(base_score, code_length, target_chars)
                return {
                    "correct": True,
                    "message": f"All test cases passed. {score_message}",
                    "score": final_score,
                    "code_length": code_length,
                    "target_chars": target_chars,
                    "base_score": base_score
                }
        except Exception as e:
            return {
                "correct": False,
                "message": f"Error updating score: {str(e)}",
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