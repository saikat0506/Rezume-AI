import streamlit as st
import json
import asyncio
import os
import io
import difflib # For highlighting changes
from pdfminer.high_level import extract_text # For PDF text extraction
import requests # Moved import to the top

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

    try:
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
                    print(f"Raw non-JSON response: {generated_content}") # For debugging
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


# --- Streamlit UI ---
st.set_page_config(page_title="AI Resume Tailor", layout="centered")

# Set background color to black and text to white
st.markdown("""
<style>
    .stApp {
        background-color: black;
        color: white;
    }
    /* You might want to style other elements as well to ensure readability */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        color: white;
        background-color: #333;
    }
    .stMarkdown, .stButton > button {
        color: white;
    }
</style>
""", unsafe_allow_html=True)


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

            # --- Step 1: Extract Keywords ---
            extracted_keywords = asyncio.run(extract_keywords(job_description))
            if not extracted_keywords:
                st.warning("Could not extract keywords. Proceeding with general tailoring.")
                keywords_instruction = ""
            else:
                st.info(f"Extracted Keywords: {extracted_keywords}")
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
                # Clean up original and tailored text for diffing (remove empty lines)
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