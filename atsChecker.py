import os
import json
import streamlit as st
import plotly.graph_objects as go
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Page Setup
st.set_page_config(
    page_title="ResumeAI - ATS Analytics & Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished dashboard look
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #4F46E5;
        margin-bottom: 10px;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        margin: 3px;
    }
    .badge-match { background-color: #d1fae5; color: #065f46; }
    .badge-missing { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    extracted = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            extracted.append(page_text)
    return "\n".join(extracted).strip()

def analyze_resume_ats(resume_text, job_desc):
    prompt = f"""
You are an advanced Applicant Tracking System (ATS) evaluator and corporate career strategist.
Evaluate the resume against the target job description (or general industry role if unspecified).

Job Description:
\"\"\"{job_desc}\"\"\"

Resume:
\"\"\"{resume_text}\"\"\"

Return ONLY valid JSON matching this structure:
{{
  "overall_score": <int 0-100>,
  "sub_scores": {{
    "keyword_match": <int 0-100>,
    "experience_alignment": <int 0-100>,
    "quantified_impact": <int 0-100>,
    "formatting_ats_readability": <int 0-100>
  }},
  "summary": "<Concise 2-3 sentence executive assessment>",
  "matched_skills": ["<skill1>", "<skill2>"],
  "missing_critical_skills": ["<skill1>", "<skill2>"],
  "formatting_issues": [
    {{"issue": "<brief issue>", "fix": "<recommended correction>"}}
  ],
  "bullet_improvements": [
    {{
      "original": "<original weak line from resume>",
      "improved": "<enhanced version using Google's XYZ formula: Accomplished [X] as measured by [Y] by doing [Z]>",
      "critique": "<why the change improves recruiter perception>"
    }}
  ],
  "top_priorities": [
    "<actionable high-priority task 1>",
    "<actionable high-priority task 2>",
    "<actionable high-priority task 3>"
  ]
}}
"""
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

# --- SIDEBAR: Upload & Controls ---
with st.sidebar:
    st.title("📄 Resume Analyzer")
    st.caption("Upload and configure your ATS audit")

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    job_desc = st.text_area(
        "Job Description / Role Target",
        placeholder="Paste target job specifications here...",
        height=180
    )

    analyze_btn = st.button("⚡ Run Full ATS Scan", type="primary", use_container_width=True)

    if analyze_btn:
        if not client:
            st.error("Missing `GEMINI_API_KEY`. Check your .env configuration.")
        elif not uploaded_file:
            st.warning("Please upload a PDF resume.")
        else:
            with st.spinner("Analyzing semantics, keywords, and readability..."):
                try:
                    text = extract_pdf_text(uploaded_file)
                    if not text:
                        st.error("No extractable text found. Make sure this isn't an image-only scan.")
                    else:
                        st.session_state.analysis_result = analyze_resume_ats(
                            text, 
                            job_desc if job_desc.strip() else "Standard industry software/technology role"
                        )
                        st.success("Analysis complete!")
                except Exception as e:
                    st.error(f"Error during scan: {str(e)}")

# --- MAIN DASHBOARD AREA ---
st.title("🎯 ATS Performance Dashboard")

res = st.session_state.analysis_result

if not res:
    st.info("👈 Upload your resume and click **'Run Full ATS Scan'** in the sidebar to view your detailed dashboard.")
else:
    # Top KPI Row
    col_score, col_kw, col_exp, col_fmt = st.columns(4)

    sub = res.get("sub_scores", {})
    col_score.metric("Overall ATS Score", f"{res.get('overall_score', 0)}/100")
    col_kw.metric("Keyword Match", f"{sub.get('keyword_match', 0)}%")
    col_exp.metric("Experience Alignment", f"{sub.get('experience_alignment', 0)}%")
    col_fmt.metric("Format Readability", f"{sub.get('formatting_ats_readability', 0)}%")

    st.markdown("---")

    # Modular Tabs
    tab_overview, tab_keywords, tab_bullets, tab_formatting, tab_export = st.tabs([
        "📈 Overview & Breakdown",
        "🔍 Keyword Match & Gap",
        "✏️ Bullet Makeovers (XYZ)",
        "🛠️ Formatting & Layout",
        "📥 Export Report"
    ])

    # 1. OVERVIEW TAB
    with tab_overview:
        c1, c2 = st.columns([1, 1])

        with c1:
            st.subheader("Radar Score Breakdown")
            categories = ['Keyword Match', 'Experience Alignment', 'Quantified Impact', 'Formatting Readability']
            values = [
                sub.get('keyword_match', 0),
                sub.get('experience_alignment', 0),
                sub.get('quantified_impact', 0),
                sub.get('formatting_ats_readability', 0)
            ]

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                line_color='#4F46E5',
                fillcolor='rgba(79, 70, 229, 0.25)'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                margin=dict(l=40, r=40, t=20, b=20),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Executive Assessment")
            st.write(res.get("summary", "No summary provided."))

            st.subheader("⚡ Top 3 Immediate Fixes")
            for item in res.get("top_priorities", []):
                st.markdown(f"- **{item}**")

    # 2. KEYWORD ANALYSIS TAB
    with tab_keywords:
        st.subheader("Skills & Keyword Heatmap")
        k_col1, k_col2 = st.columns(2)

        with k_col1:
            st.markdown("#### ✅ Detected Matching Keywords")
            matched = res.get("matched_skills", [])
            if matched:
                badges = "".join([f'<span class="badge badge-match">{k}</span>' for k in matched])
                st.markdown(badges, unsafe_allow_html=True)
            else:
                st.write("No direct keyword matches detected.")

        with k_col2:
            st.markdown("#### ❌ Missing Critical Keywords")
            missing = res.get("missing_critical_skills", [])
            if missing:
                badges = "".join([f'<span class="badge badge-missing">{k}</span>' for k in missing])
                st.markdown(badges, unsafe_allow_html=True)
            else:
                st.write("No missing keywords identified.")

    # 3. BULLET MAKEOVERS TAB
    with tab_bullets:
        st.subheader("Bullet Point Impact Makeover (Google XYZ Formula)")
        st.caption("Formula: *Accomplished [X] as measured by [Y] by doing [Z]*")

        bullets = res.get("bullet_improvements", [])
        if not bullets:
            st.info("No bullet rewrites were suggested.")
        else:
            for idx, b in enumerate(bullets, 1):
                with st.expander(f"Improvement #{idx}: {b.get('original')[:70]}..."):
                    st.markdown("**Original:**")
                    st.warning(b.get("original", ""))

                    st.markdown("**ATS Optimized (Action + Metric):**")
                    st.success(b.get("improved", ""))

                    st.markdown(f"💡 **Why:** {b.get('critique', '')}")

    # 4. FORMATTING TAB
    with tab_formatting:
        st.subheader("ATS Structural Check & Layout Review")
        issues = res.get("formatting_issues", [])
        if not issues:
            st.success("Great job! No major structural or parsing obstacles found.")
        else:
            for item in issues:
                st.markdown(f"**Issue:** {item.get('issue')}")
                st.info(f"👉 **Fix:** {item.get('fix')}")
                st.divider()

    # 5. EXPORT REPORT TAB
    with tab_export:
        st.subheader("Download Full ATS Audit Summary")
        
        # Build text markdown report
        report_text = f"""# Resume AI ATS Audit Report
**Overall Score:** {res.get('overall_score')}/100

## Summary
{res.get('summary')}

## Matched Keywords
{", ".join(res.get('matched_skills', []))}

## Missing Keywords
{", ".join(res.get('missing_critical_skills', []))}

## Immediate Next Steps
""" + "\n".join([f"- {p}" for p in res.get("top_priorities", [])])

        st.download_button(
            label="📥 Download Audit Report (.md)",
            data=report_text,
            file_name="ats_resume_audit.md",
            mime="text/markdown",
            type="primary"
        )