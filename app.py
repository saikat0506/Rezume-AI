import streamlit as st
import json
import asyncio
import os
import io
import difflib
from pdfminer.high_level import extract_text # For PDF text extraction
# If you switched to pypdf, uncomment the line below and comment the pdfminer.six line
# from pypdf import PdfReader

# --- Configuration for Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("Gemini API Key not found. Please set the 'GEMINI_API_KEY' environment variable.")
    st.stop()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Function to call Gemini API ---
async def call_gemini_api(prompt_text: str, temperature: float = 0.7, max_output_tokens: int = 2048, response_schema: dict = None):
    """
    Makes an asynchronous call to the Gemini API to generate content.
    Optionally accepts a response_schema for structured output.
    """
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt_text}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": max_output_tokens,
        }
    }

    if response_schema:
        payload["generationConfig"]["responseMimeType"] = "application/json"
        payload["generationConfig"]["responseSchema"] = response_schema

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        import requests
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("candidates") and len(result["candidates"]) > 0 and \
           result["candidates"][0].get("content") and \
           result["candidates"][0]["content"].get("parts") and \
           len(result["candidates"][0]["content"]["parts"]) > 0:
            generated_content = result["candidates"][0]["content"]["parts"][0]["text"]
            if response_schema:
                try:
                    return json.loads(generated_content)
                except json.JSONDecodeError:
                    st.error("Failed to parse JSON response from Gemini API.")
                    print(f"Raw non-JSON response: {generated_content}")
                    return None
            else:
                return generated_content
        else:
            st.error("Gemini API response structure is unexpected or content is missing.")
            print(f"Unexpected Gemini API response: {result}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling Gemini API: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

# --- Function to extract keywords from Job Description ---
async def extract_keywords(job_description: str) -> str:
    """
    Uses Gemini API to extract key skills and requirements from a job description.
    """
    prompt = f"""
    Extract the most important 10-15 keywords, key skills, and essential requirements from the following job description.
    List them as a comma-separated string. Do not include any other text or conversational phrases.

    Job Description:
    {job_description}

    Keywords:
    """
    with st.spinner("Extracting keywords from job description..."):
        keywords = await call_gemini_api(prompt, temperature=0.3, max_output_tokens=100)
        return keywords if keywords else ""

# --- Function to get ATS score and human review ---
async def get_resume_review_and_score(tailored_resume: str, job_title: str, job_description: str):
    """
    Uses Gemini API to provide an ATS score and a humanized review for the tailored resume.
    """
    review_schema = {
        "type": "OBJECT",
        "properties": {
            "ats_score": {"type": "INTEGER", "description": "ATS compatibility score out of 100"},
            "review": {"type": "STRING", "description": "Humanized review of the resume"}
        },
        "required": ["ats_score", "review"]
    }

    prompt = f"""
    You are an expert ATS (Applicant Tracking System) and a human recruiter.
    Your task is to review the following TAILORED resume against the provided Job Title and Job Description.

    Provide a score out of 100 for its ATS compatibility. A higher score means better keyword matching and formatting for ATS.
    Then, provide a humanized review, focusing on:
    - Overall readability and clarity.
    - Impact and strength of language.
    - How well it highlights relevant experience and skills for the specific job.
    - Any suggestions for further improvement from a human perspective.
    - Ensure the resume is highly ATS friendly AND humanized.

    Respond ONLY with a JSON object containing 'ats_score' (integer out of 100) and 'review' (string).

    ---
    **Tailored Resume:**
    {tailored_resume}

    ---
    **Job Title:**
    {job_title}

    ---
    **Job Description:**
    {job_description}

    ---
    JSON Output:
    """
    with st.spinner("Analyzing tailored resume for ATS score and human review..."):
        review_data = await call_gemini_api(prompt, temperature=0.5, max_output_tokens=500, response_schema=review_schema)
        return review_data

# --- Function to generate HTML diff ---
def generate_diff_html(text1: str, text2: str) -> str:
    """
    Generates an HTML string highlighting differences between two texts.
    Additions are green, deletions are red.
    """
    d = difflib.Differ()
    diff = d.compare(text1.splitlines(keepends=True), text2.splitlines(keepends=True))

    html_diff = []
    html_diff.append('<div style="font-family: \'Inter\', sans-serif; white-space: pre-wrap; background-color: #f8f8f8; padding: 10px; border-radius: 8px; overflow-x: auto; border: 1px solid #ddd;">')
    for line in diff:
        if line.startswith('+ '):
            html_diff.append(f'<span style="background-color: #e6ffe6; color: #008000;">{line}</span>') # Green for additions
        elif line.startswith('- '):
            html_diff.append(f'<span style="background-color: #ffe6e6; color: #ff0000;">{line}</span>') # Red for deletions
        else:
            html_diff.append(f'<span>{line}</span>') # No change
    html_diff.append('</div>')
    return "".join(html_diff)


# --- Streamlit UI ---
st.set_page_config(page_title="AI Resume Tailor", layout="centered")

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        color: #333;
    }
    .main {
        background-color: #ffffff; /* Lighter background */
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1); /* Stronger shadow */
        max-width: 900px; /* Max width for better readability */
        margin: auto;
    }
    h1 {
        color: #2c3e50; /* Darker heading */
        text-align: center;
        font-weight: 700;
        margin-bottom: 20px;
        font-size: 2.5em; /* Bigger heading */
    }
    h2, h3 {
        color: #34495e; /* Slightly lighter heading */
        margin-top: 30px;
        border-bottom: 2px solid #ecf0f1; /* Subtle separator */
        padding-bottom: 10px;
    }
    .stButton>button {
        background-color: #3498db; /* Blue for action */
        color: white;
        border-radius: 10px; /* More rounded */
        padding: 12px 25px;
        font-size: 18px;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease, transform 0.2s ease;
        width: 100%; /* Full width button */
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .stButton>button:hover {
        background-color: #2980b9; /* Darker blue on hover */
        transform: translateY(-2px); /* Slight lift effect */
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div {
        border-radius: 10px;
        border: 1px solid #dcdcdc; /* Lighter border */
        padding: 12px;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.05); /* Inner shadow */
        transition: border-color 0.3s ease;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus, .stSelectbox>div>div:focus {
        border-color: #3498db; /* Highlight on focus */
        outline: none;
    }
    .stFileUploader>div>div>button {
        background-color: #2ecc71; /* Green for upload */
        color: white;
        border-radius: 10px;
        padding: 12px 20px;
        font-size: 16px;
        border: none;
        transition: background-color 0.3s ease;
        font-weight: 500;
    }
    .stFileUploader>div>div>button:hover {
        background-color: #27ae60; /* Darker green on hover */
    }
    .score-box {
        background-color: #e8f8f5; /* Very light teal */
        border-left: 6px solid #1abc9c; /* Stronger teal border */
        padding: 20px;
        margin-top: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08); /* More prominent shadow */
    }
    .score-text {
        font-size: 2.8em; /* Larger score */
        font-weight: 700;
        color: #16a085; /* Darker teal */
        text-align: center;
        display: block; /* Ensures it takes full width for centering */
        margin-bottom: 10px;
    }
    .stInfo {
        background-color: #d9edf7; /* Light blue for info */
        border-left: 5px solid #3498db;
        color: #31708f;
        border-radius: 8px;
        padding: 10px;
    }
    .stWarning {
        background-color: #fcf8e3; /* Light yellow for warning */
        border-left: 5px solid #f39c12;
        color: #8a6d3b;
        border-radius: 8px;
        padding: 10px;
    }
    .stError {
        background-color: #f2dede; /* Light red for error */
        border-left: 5px solid #e74c3c;
        color: #a94442;
        border-radius: 8px;
        padding: 10px;
    }
    .stSpinner > div > div {
        color: #3498db; /* Spinner color */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("✨ AI Resume Tailor")
st.markdown("### Optimize your resume for the perfect job fit with AI-powered insights.")

# Using columns for better layout of inputs
col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Upload your Resume (TXT or PDF file)", type=["txt", "pdf"])
    job_title = st.text_input("Job Title", placeholder="e.g., Senior Software Engineer")

with col2:
    tailoring_style = st.selectbox(
        "Choose Tailoring Style:",
        ("Standard", "Concise", "Detailed"),
        help="Standard: Balanced changes. Concise: Focus on brevity. Detailed: More elaborate, comprehensive changes."
    )
    # Placeholder to align layout, or you can add another input here
    st.markdown("---") # Visual separator

job_description = st.text_area("Job Description", height=200, placeholder="Paste the full job description here...")


# Tailor button
st.markdown("---") # Separator before the action button
if st.button("Tailor My Resume 🚀"):
    if uploaded_file is not None and job_title and job_description:
        resume_content = ""
        try:
            if uploaded_file.type == "text/plain":
                resume_content = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "application/pdf":
                # If you switched to pypdf, use this block:
                # reader = PdfReader(io.BytesIO(uploaded_file.read()))
                # resume_content = ""
                # for page in reader.pages:
                #     resume_content += page.extract_text() or ""
                # If using pdfminer.six, use this block:
                resume_content = extract_text(io.BytesIO(uploaded_file.read()))
            else:
                st.error("Unsupported file type. Please upload a TXT or PDF file.")
                st.stop()

            # --- Step 1: Extract Keywords ---
            extracted_keywords = asyncio.run(extract_keywords(job_description))
            if not extracted_keywords:
                st.warning("Could not extract keywords. Proceeding with general tailoring.")
                keywords_instruction = ""
            else:
                st.info(f"Extracted Keywords: **{extracted_keywords}**")
                keywords_instruction = f"Ensure the tailored resume highlights these specific keywords and phrases: {extracted_keywords}. "

            # --- Step 2: Tailor Resume ---
            tailoring_guidance = ""
            if tailoring_style == "Concise":
                tailoring_guidance = "Make the tailored resume concise and to the point, focusing only on the most relevant information."
            elif tailoring_style == "Detailed":
                tailoring_guidance = "Provide a detailed and comprehensive tailored resume, elaborating on experiences where relevant."
            else: # Standard
                tailoring_guidance = "Provide a balanced and standard tailored resume."

            prompt = f"""
            You are an expert resume writer and career coach. Your task is to tailor a given resume to a specific job description and job title.
            {tailoring_guidance}
            Focus on highlighting relevant skills, experiences, and achievements that directly match the requirements and keywords in the job description.
            {keywords_instruction}
            Ensure the tone is professional and impactful.
            The output should ONLY be the tailored resume text. Do NOT include any conversational text, introductions, or conclusions.

            ---
            **Original Resume:**
            {resume_content}

            ---
            **Job Title:**
            {job_title}

            ---
            **Job Description:**
            {job_description}

            ---
            **Tailored Resume:**
            """

            with st.spinner("Tailoring your resume... This might take a moment. ✨"):
                tailored_resume = asyncio.run(call_gemini_api(prompt))

            if tailored_resume:
                st.subheader("Your Tailored Resume 🎉")
                st.markdown(tailored_resume)

                st.subheader("Changes Highlighted 🔍")
                cleaned_original = "\n".join([line.strip() for line in resume_content.splitlines() if line.strip()])
                cleaned_tailored = "\n".join([line.strip() for line in tailored_resume.splitlines() if line.strip()])
                diff_html = generate_diff_html(cleaned_original, cleaned_tailored)
                st.markdown(diff_html, unsafe_allow_html=True)

                st.download_button(
                    label="Download Tailored Resume",
                    data=tailored_resume,
                    file_name="tailored_resume.txt",
                    mime="text/plain"
                )

                # --- Step 3: Get ATS Score and Review ---
                review_data = asyncio.run(get_resume_review_and_score(tailored_resume, job_title, job_description))

                if review_data and 'ats_score' in review_data and 'review' in review_data:
                    st.subheader("Resume Review & ATS Score 📊")
                    st.markdown(
                        f"""
                        <div class="score-box">
                            <p><strong>ATS Compatibility Score:</strong> <span class="score-text">{review_data['ats_score']}/100</span></p>
                            <p><strong>Humanized Review:</strong></p>
                            <p>{review_data['review']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("Could not generate ATS score and review. Please try again.")

            else:
                st.error("Failed to tailor resume. Please try again.")

        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")
            st.info("Please ensure your PDF is not an image-only PDF and contains selectable text.")

    else:
        st.warning("Please upload your resume, enter a job title, and paste the job description to proceed.")

st.markdown("---")
st.markdown("Developed with ❤️ using Streamlit and Google Gemini API.")
