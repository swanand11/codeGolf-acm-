# ACM RIT Code Golf

A Flask-based web application for hosting programming challenges in a code golf format, where participants compete to solve problems with the shortest code possible.

## Project Description

This project was built for the ACM RIT Code Golf competition event. It provides a platform for programmers to solve algorithmic challenges while competing to write the most concise code. The system evaluates user submissions in real-time using secure sandboxed execution and maintains a live leaderboard of participants ranked by their performance.

## Features

- **User Authentication**: Simple registration and login system using Base64 tokens
- **Challenge Library**: JSON-defined programming challenges with varying difficulty levels
- **Code Execution**: Secure sandboxed code evaluation via the [Piston](https://github.com/engineer-man/piston) API
- **Live Leaderboard**: Real-time rankings of participants based on submission performance
- **Test Case Validation**: Automated verification of solutions against predefined test cases
- **User Dashboard**: Interface for viewing available challenges and submission history

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Code Execution**: Piston API
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Previously on Render (currently inactive)

## File Structure

```
📂server  
 ┣ 📂__pycache__  
 ┣ 📂static  
 ┃ ┣ 📜questions.json          # Challenge definitions  
 ┃ ┗ 📜testcases.json          # Test cases for each challenge  
 ┣ 📂templates  
 ┃ ┣ 📜leaderboard.html        # Leaderboard page  
 ┃ ┣ 📜login.html              # User login  
 ┃ ┣ 📜mainpage.html           # Challenge dashboard  
 ┃ ┣ 📜register.html           # User registration  
 ┃ ┗ 📜sampleq.html            # Sample question display  
 ┣ 📜evaluate.py               # Piston integration for code execution  
 ┣ 📜server.py                 # Main Flask app entry  
 ┣ 📜render.yaml               # Old Render deploy config (inactive)  
 ┣ 📜requirements.txt          # Python dependencies  
 ┗ 📜README.md                 # This file
```

## Setup Instructions

### Prerequisites

- Python 3.7+
- PostgreSQL
- Access to the Piston API (self-hosted or via public instance)

### Installation

1. Clone the repository:
   
2. Install dependencies:
   ```bash
   pip install -r server/requirements.txt
   ```

3. Configure PostgreSQL:
   - Create a database for the application
   - Update connection parameters in `server.py` if necessary

4. Configure Piston API connection:
   - Check `evaluate.py` and update the Piston API endpoint if needed

5. Run the application:
   ```bash
   python server/server.py
   ```

6. Access the web interface at `http://localhost:5000`

## Security Disclaimer

This application uses Base64 tokens for authentication, which is implemented for simplicity and educational purposes. **This authentication method is not secure for production environments** as it does not provide proper encryption or protection against common attack vectors.

If deploying this application in a production environment:
- Replace the authentication system with a proper secure solution (OAuth, JWT, etc.)
- Implement proper session management
- Add CSRF protection
- Consider rate limiting and additional security measures

## About ACM RIT Code Golf

This project was originally developed for the Association for Computing Machinery (ACM) chapter at Ramaiah Institute of Technology (RIT) to host their Code Golf programming competition. Code Golf is a type of recreational programming competition where participants strive to solve challenges using the fewest characters of code possible.

## Deployment Note

The application was previously deployed on Render, but that hosting instance is currently inactive. To deploy the application, you can:
- Set up a new instance on Render using the included `render.yaml` configuration file
- Deploy to another platform like Heroku, AWS, or DigitalOcean
- Run on your own server or local environment using the setup instructions above

## Credits

This application was developed for the ACM RIT Code Golf event. Special thanks to:
- [Piston](https://github.com/engineer-man/piston) for providing the code execution API
- ACM RIT for organizing the event
- All contributors to the project



