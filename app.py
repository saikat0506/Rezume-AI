import streamlit as st
import json
import asyncio
import os
import io
import difflib # For highlighting changes
from pdfminer.high_level import extract_text # For PDF text extraction
import requests

# --- Streamlit UI config (MUST BE THE FIRST Streamlit COMMAND) ---
st.set_page_config(page_title="AI Resume Tailor", layout="centered")

# --- Configuration for Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- API Key Check and Display (AFTER set_page_config) ---
if not GEMINI_API_KEY:
    st.error("Gemini API Key not found. Please set the 'GEMINI_API_KEY' environment variable in your deployment settings.")
    st.info("If running locally, ensure it's set in your shell or .env file.")
    st.stop() # Stop the app execution if the key is missing
else:
    st.success("Gemini API Key loaded successfully.") # This confirms the key is being picked up

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Function to call Gemini API ---
async def call_gemini_api(prompt_text: str, temperature: float = 0.7, max_output_tokens: int = 2048, response_schema: dict = None):
    """
    Makes an asynchronous call to the Gemini API to generate content.
    Oftenly accepts a response_schema for structured output.
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

    # st.write(f"Attempting to call Gemini API at: {GEMINI_API_URL}") # Debugging
    # Note: Do NOT print GEMINI_API_KEY directly in production logs for security reasons.

    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        # st.write(f"Gemini API raw response status: {response.status_code}") # Debugging
        # st.write(f"Gemini API raw response body: {result}") # For detailed debugging, but can be verbose

        if result.get("candidates") and len(result["candidates"]) > 0 and \
           result["candidates"][0].get("content") and \
           result["candidates"][0]["content"].get("parts") and \
           len(result["candidates"][0]["content"]["parts"]) > 0:
            generated_content = result["candidates"][0]["content"]["parts"][0]["text"]
            if response_schema:
                try:
                    return json.loads(generated_content)
                except json.JSONDecodeError:
                    st.error("Failed to parse JSON response from Gemini API. Check API response format.")
                    st.write(f"Raw non-JSON response received: {generated_content}") # For debugging
                    return None
            else:
                return generated_content
        else:
            st.error("Gemini API response structure is unexpected or content is missing. This often indicates an API error or rate limit.")
            st.write(f"Unexpected Gemini API response: {result}") # Debugging
            return None
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP Error calling Gemini API: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"Connection Error calling Gemini API. Check internet connection or API endpoint reachability: {e}")
        return None
    except requests.exceptions.Timeout as e:
        st.error(f"Timeout Error calling Gemini API. The request took too long: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Generic Request Error calling Gemini API: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during API call: {e}")
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
    # Reduced temperature slightly for more focused keyword extraction
    keywords = await call_gemini_api(prompt, temperature=0.2, max_output_tokens=100)
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
    You are a sophisticated AI system designed to evaluate resumes based on ATS (Applicant Tracking System) scoring criteria. 
    Your task is to review the following TAILORED resume against the provided Job Title and Job Description.

    Provide a comprehensive ATS compatibility score out of 100. A higher score means better keyword matching and formatting for ATS. 
    Then, provide a human interviewer's perspective on the resume against the job role and description, covering:
        - Strengths and weaknesses of the candidate's application.
        - Potential questions and concerns that may arise during an interview.
        - Overall readability and clarity.
        - How well it highlights relevant experience and skills for the specific job.
        - Suggestions for further improvement from a human perspective. 
    Ensure your responses are formal, detailed, and tailored to advanced users seeking in-depth analysis. 
    Respond ONLY with a valid JSON object containing 'ats_score' (integer out of 100) and 'review' (string). 
    DO NOT include any other text or conversational phrases outside the JSON.

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
        # Increased max_output_tokens and slightly reduced temperature for better JSON adherence
        review_data = await call_gemini_api(prompt, temperature=0.3, max_output_tokens=1500, response_schema=review_schema)
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
    html_diff.append('<div style="font-family: monospace; white-space: pre-wrap; background-color: #2E3036; padding: 10px; border-radius: 8px; overflow-x: auto; border: 1px solid #555555;">')
    for line in diff:
        if line.startswith('+ '):
            html_diff.append(f'<span style="background-color: #2F4F2F; color: #90EE90;">{line}</span>') # Darker Green for additions
        elif line.startswith('- '):
            html_diff.append(f'<span style="background-color: #4F2F2F; color: #FFB6C1;">{line}</span>') # Darker Red for deletions
        else:
            html_diff.append(f'<span style="color: #E0E0E0;">{line}</span>') # Light grey for no change
    html_diff.append('</div>')
    return "".join(html_diff)

# Set background color to black and text to white
st.markdown("""
<style>
    /* Ensure the main app container is black */
    .stApp {
        background-color: black !important;
        color: white !important;
    }

    /* Target specific Streamlit elements for consistent styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stFileUploader > div > div > button {
        color: white !important;
        background-color: #333 !important; /* Grey for text areas/inputs */
        border: 1px solid #555 !important; /* Default border */
        border-radius: 5px !important;
    }

    /* Text color for labels and general markdown */
    .stMarkdown,
    .stTextInput label,
    .stTextArea label,
    .stFileUploader label,
    .stSelectbox label, /* Selectbox label should still be white */
    .stButton > button {
        color: white !important;
    }

    /* Hover/Focus effect for text inputs and text areas */
    .stTextInput > div > div > input:hover,
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:hover,
    .stTextArea > div > div > textarea:focus {
        border: 1px solid red !important; /* Red border on hover/focus */
        box-shadow: 0 0 0 0.2rem rgba(255, 0, 0, 0.25) !important; /* Optional: subtle red glow */
    }

    /* Style for buttons */
    .stButton > button {
        background-color: #4CAF50 !important; /* Example green button */
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        padding: 10px 20px !important;
        cursor: pointer !important;
        transition: background-color 0.3s ease !important;
    }

    .stButton > button:hover {
        background-color: #45a049 !important; /* Darker green on hover */
    }

    /* Style for the score box */
    .score-box {
        background-color: #2E3036; /* Darker grey for the box */
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #555555;
        margin-top: 20px;
    }

    .score-box p {
        margin-bottom: 10px;
    }

    .score-box strong {
        color: #ADD8E6; /* Light blue for strong text */
    }

    .score-text {
        color: #FFD700; /* Gold for the score number */
        font-size: 1.2em;
        font-weight: bold;
    }

    /* Info and Warning boxes */
    .stAlert {
        background-color: #333 !important;
        color: white !important;
        border-left: 5px solid;
    }
    .stAlert.info {
        border-color: #2196F3 !important; /* Blue for info */
    }
    .stAlert.warning {
        border-color: #ff9800 !important; /* Orange for warning */
    }
    .stAlert.error {
        border-color: #f44336 !important; /* Red for error */
    }

</style>
""", unsafe_allow_html=True)


# --- Initialize session state variables if they don't exist ---
if 'tailored_resume' not in st.session_state:
    st.session_state.tailored_resume = None
if 'review_data' not in st.session_state:
    st.session_state.review_data = None
if 'original_resume_content' not in st.session_state:
    st.session_state.original_resume_content = None
if 'extracted_keywords_display' not in st.session_state:
    st.session_state.extracted_keywords_display = None


st.title("✨ AI Resume Tailor")
st.markdown("Upload your resume (TXT or PDF), provide a job title and description, and let AI tailor your resume for the perfect fit!")

# Input fields
uploaded_file = st.file_uploader("Upload your Resume (TXT or PDF file)", type=["txt", "pdf"])
job_title = st.text_input("Job Title", placeholder="e.g., Senior Software Engineer")
job_description = st.text_area("Job Description", height=200, placeholder="Paste the full job description here...")

# Tailoring Style Option
tailoring_style = st.selectbox(
    "Choose Tailoring Style:",
    ("Standard", "Concise", "Detailed"),
    help="Standard: Balanced changes. Concise: Focus on brevity. Detailed: More elaborate, comprehensive changes."
)

# Tailor button
if st.button("Tailor My Resume 🚀"):
    # Reset session state on new tailoring attempt
    st.session_state.tailored_resume = None
    st.session_state.review_data = None
    st.session_state.original_resume_content = None
    st.session_state.extracted_keywords_display = None

    if uploaded_file is not None and job_title and job_description:
        resume_content = ""
        try:
            if uploaded_file.type == "text/plain":
                resume_content = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "application/pdf":
                resume_content = extract_text(io.BytesIO(uploaded_file.read()))
            else:
                st.error("Unsupported file type. Please upload a TXT or PDF file.")
                st.stop()

            # Store original content for diffing later
            st.session_state.original_resume_content = resume_content

            # --- Step 1: Extract Keywords ---
            extracted_keywords = asyncio.run(extract_keywords(job_description))
            
            if not extracted_keywords:
                st.session_state.extracted_keywords_display = "Could not extract keywords. Proceeding with general tailoring."
                keywords_instruction = ""
            else:
                st.session_state.extracted_keywords_display = f"Extracted Keywords: {extracted_keywords}"
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
                st.session_state.tailored_resume = asyncio.run(call_gemini_api(prompt))

            if st.session_state.tailored_resume:
                # --- Step 3: Get ATS Score and Review ---
                st.session_state.review_data = asyncio.run(get_resume_review_and_score(
                    st.session_state.tailored_resume, job_title, job_description
                ))
            else:
                st.error("Failed to tailor resume. Please try again.")
                st.session_state.tailored_resume = None # Reset on failure
                st.session_state.review_data = None # Reset on failure

        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")
            st.info("Please ensure your PDF is not an image-only PDF and contains selectable text.")
            st.session_state.tailored_resume = None # Reset on error
            st.session_state.review_data = None # Reset on error
            st.session_state.original_resume_content = None
            st.session_state.extracted_keywords_display = None
    else:
        st.warning("Please upload your resume, enter a job title, and paste the job description to proceed.")

# --- Display Results if available in session_state ---
if st.session_state.tailored_resume:
    if st.session_state.extracted_keywords_display:
        st.info(st.session_state.extracted_keywords_display)

    st.subheader("Your Tailored Resume 🎉")
    st.markdown(st.session_state.tailored_resume)

    st.subheader("Changes Highlighted 🔍")
    # Clean up original and tailored text for diffing (remove empty lines)
    cleaned_original = "\n".join([line.strip() for line in st.session_state.original_resume_content.splitlines() if line.strip()])
    cleaned_tailored = "\n".join([line.strip() for line in st.session_state.tailored_resume.splitlines() if line.strip()])
    diff_html = generate_diff_html(cleaned_original, cleaned_tailored)
    st.markdown(diff_html, unsafe_allow_html=True)

    st.download_button(
        label="Download Tailored Resume",
        data=st.session_state.tailored_resume,
        file_name="tailored_resume.txt",
        mime="text/plain"
    )

if st.session_state.review_data and 'ats_score' in st.session_state.review_data and 'review' in st.session_state.review_data:
    st.subheader("Resume Review & ATS Score 📊")
    st.markdown(
        f"""
        <div class="score-box">
            <p><strong>ATS Compatibility Score:</strong> <span class="score-text">{st.session_state.review_data['ats_score']}/100</span></p>
            <p><strong>Humanized Review:</strong></p>
            <p>{st.session_state.review_data['review']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --- Download Resume Review and Score ---
    review_output_text = f"--- Resume Review and ATS Score ---\n\n" \
                         f"ATS Compatibility Score: {st.session_state.review_data['ats_score']}/100\n\n" \
                         f"Humanized Review:\n{st.session_state.review_data['review']}\n\n" \
                         f"--- End of Review ---"

    st.download_button(
        label="Download Review & Score (TXT)",
        data=review_output_text,
        file_name="resume_review_and_score.txt",
        mime="text/plain"
    )

    # Option to download as JSON:
    st.download_button(
        label="Download Review & Score (JSON)",
        data=json.dumps(st.session_state.review_data, indent=4),
        file_name="resume_review_and_score.json",
        mime="application/json"
    )

st.markdown("---")