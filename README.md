# AI Resume Tailor

This application helps you tailor your resume to specific job descriptions and titles using Google's Gemini AI. It also provides an ATS (Applicant Tracking System) compatibility score and a humanized review of your tailored resume, highlighting the changes made.

try the website at : https://rezume-ai.streamlit.app/

## User Manual

Follow these steps to set up and use the AI Resume Tailor locally.

## 1. Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8+**: Download from [python.org](https://www.python.org/downloads/).
* **pip**: Python's package installer (usually comes with Python).
* **Google Gemini API Key**: You'll need an API key from the Google AI Studio or Google Cloud Console.

## 2. Local Setup

To run the application on your local machine:

### Step 2.1: Clone the Repository

First, clone your project repository from GitHub (or wherever you've hosted it) to your local machine.

```bash
git clone <your-repository-url>
cd your-resume-tailor-app/ # Navigate into your project directory

(Replace `<your-repository-url>` with the actual URL of your Git repository and `your-resume-tailor-app/` with your project's folder name).

**Step 2.2: Install Dependencies**

Install all the required Python libraries using `pip`:

```bash
pip install -r requirements.txt
```

**Step 2.3: Set Your Gemini API Key**

Your application requires a Gemini API key. For local testing, you need to set this as an environment variable in your terminal *before* running the app.

  * **On Linux/macOS (or Git Bash on Windows):**
    ```bash
    export GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"
    ```
  * **On Windows (PowerShell):**
    ```powershell
    $env:GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"
    ```
  * **On Windows (Command Prompt):**
    ```cmd
    set GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY_HERE"
    ```

**Important:** Replace `"YOUR_ACTUAL_GEMINI_API_KEY_HERE"` with your real Gemini API key. Ensure there are no spaces around the `=` sign.

**Step 2.4: Run the Application**

After setting the API key in the *same* terminal session, start the Streamlit application:

```bash
streamlit run app.py
```

This command will open the application in your default web browser (usually at `http://localhost:8501`).

### 3\. How to Use the AI Resume Tailor

Once the application is running in your browser:

**Step 3.1: Upload Your Resume**

  * Click the "Browse files" button under "Upload your Resume (TXT or PDF file)".
  * Select your resume file. The app supports both plain text (`.txt`) and PDF (`.pdf`) formats.

**Step 3.2: Enter Job Title**

  * In the "Job Title" text box, type the exact title of the job you are applying for (e.g., "Senior Software Engineer", "Marketing Specialist").

**Step 3.3: Enter Job Description**

  * In the "Job Description" text area, paste the complete job description from the job posting. The more detailed it is, the better the AI can tailor your resume.

**Step 3.4: Choose Tailoring Style**

  * Select your preferred "Tailoring Style" from the dropdown menu:
      * **Standard:** Provides a balanced set of changes.
      * **Concise:** Focuses on brevity and the most critical information.
      * **Detailed:** Offers more elaborate and comprehensive modifications.

**Step 3.5: Tailor Your Resume**

  * Click the "Tailor My Resume 🚀" button.
  * The app will display a spinner indicating that the AI is working. This process might take a few moments.

**Step 3.6: Review Results**

Once the process is complete, you will see three main sections:

  * **Your Tailored Resume 🎉:** This is the AI-generated version of your resume, optimized for the job description.
  * **Changes Highlighted 🔍:** This section visually compares your original resume with the tailored version.
      * Text highlighted in **green** indicates additions made by the AI.
      * Text highlighted in **red** indicates deletions made by the AI.
  * **Resume Review & ATS Score 📊:**
      * **ATS Compatibility Score:** A score out of 100 indicating how well your resume is optimized for Applicant Tracking Systems (ATS).
      * **Humanized Review:** A detailed review from the perspective of a human recruiter, offering insights into readability, impact, and suggestions for further improvement.

**Step 3.7: Download Tailored Resume**

  * Click the "Download Tailored Resume" button to save the AI-generated resume as a `.txt` file to your computer.

### 4\. Deployment (for Developers)

This application can be easily deployed to platforms like Vercel. Refer to the project's deployment instructions (if provided separately, or in the project's main documentation) for details on setting up environment variables and build commands on Vercel.

-----

```
```
