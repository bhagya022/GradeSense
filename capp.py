import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re

# ---------------- CONFIG ----------------
st.set_page_config(page_title="What's your CGPA?", layout="centered")
st.title("What's your CGPA?")

# ---------------- CONSTANTS ----------------
GRADE_POINTS = {
    "S": 10,
    "A": 9,
    "B": 8,
    "C": 7,
    "D": 6
}

GRADE_TO_MARK = {
    "S": "65+",
    "A": "55+",
    "B": "50+",
    "C": "45+",
    "D": "40+"
}

# ---------------- SESSION STATE ----------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "df" not in st.session_state:
    st.session_state.df = None
if "inputs" not in st.session_state:
    st.session_state.inputs = None
if "confirmed" not in st.session_state:
    st.session_state.confirmed = False

# ---------------- HELPERS ----------------
def verdict_text(required_avg):
    if required_avg > 9.5:
        return "⚠️ Extremely difficult — near-perfect grades required"
    elif required_avg > 9.0:
        return "⚠️ Difficult but achievable with focus"
    elif required_avg > 8.0:
        return "✅ Comfortable with consistent effort"
    else:
        return "🟢 Very safe target"

def grade_from_points(avg):
    for g, p in GRADE_POINTS.items():
        if avg >= p:
            return g
    return "D"

# ---------------- STEP 1: OCR ----------------
if st.session_state.step == 1:
    st.header("Step 1️⃣ Upload Almanac")

    uploaded = st.file_uploader("Upload almanac image", type=["jpg", "png", "jpeg"])
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, use_column_width=True)

        text = pytesseract.image_to_string(image)
        editable = st.text_area("OCR Preview (edit if needed)", text, height=180)

        rows = []
        for line in editable.split("\n"):
            line = line.strip()
            if not line:
                continue

            credit_match = re.findall(r"\b[1-4]\b", line)
            if not credit_match:
                continue

            credit = int(credit_match[-1])
            subject = re.sub(r"\bU\d+\w+\b", "", line)
            subject = re.sub(r"[0-9|_–\-]", " ", subject)
            subject = re.sub(r"\s+", " ", subject).strip()

            if len(subject) > 5:
                rows.append([subject, credit, "Theory"])

        df = pd.DataFrame(rows, columns=["Subject", "Credit", "Type"])
        df.insert(0, "S.No", range(1, len(df) + 1))
        st.session_state.df = df
        st.session_state.confirmed = False

        if st.button("➡️ Proceed", type="primary"):
            st.session_state.step = 2

# ---------------- STEP 2: EDIT SUBJECTS ----------------
elif st.session_state.step == 2:
    st.header("Step 2️⃣ Edit & Confirm Subjects")

    with st.form("edit_form"):
        edited_df = st.data_editor(
            st.session_state.df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Type": st.column_config.SelectboxColumn(
                    options=["Theory", "Lab", "Internship", "Project"]
                )
            }
        )

        edited_df = edited_df.dropna(subset=["Subject"]).reset_index(drop=True)
        edited_df["S.No"] = range(1, len(edited_df) + 1)

        st.info(
            f"**Total Credits:** {edited_df['Credit'].sum()}  |  "
            f"**Subjects:** {len(edited_df)}"
        )

        back, confirm, proceed = st.columns(3)
        if back.form_submit_button("⬅️ Back"):
            st.session_state.step = 1

        if confirm.form_submit_button("💾 Confirm"):
            st.session_state.df = edited_df
            st.session_state.confirmed = True
            st.success("Confirmed!")

        if proceed.form_submit_button("➡️ Proceed"):
            if st.session_state.confirmed:
                st.session_state.step = 3
            else:
                st.warning("Confirm before proceeding")

# ---------------- STEP 3: INPUTS ----------------
elif st.session_state.step == 3:
    st.header("Step 3️⃣ Enter Known Information")

    df = st.session_state.df
    known_grades = {}

    for idx, row in df.iterrows():
        if row["Type"] != "Theory":
            known_grades[row["Subject"]] = st.selectbox(
                f"{row['Subject']} – Expected Grade",
                list(GRADE_POINTS.keys()),
                index=1,
                key=f"g_{idx}"
            )

    target = st.number_input("🎯 Target CGPA", 0.0, 10.0, 9.0, 0.1)

    if st.button("Analyze 🎯", type="primary"):
        st.session_state.inputs = (known_grades, target)
        st.session_state.step = 4

# ---------------- STEP 4: POINTS-BASED ANALYSIS ----------------
elif st.session_state.step == 4:
    df = st.session_state.df
    known_grades, target = st.session_state.inputs

    total_credits = df["Credit"].sum()
    target_points = target * total_credits

    earned_points = 0
    earned_credits = 0

    for _, row in df.iterrows():
        if row["Subject"] in known_grades:
            gp = GRADE_POINTS[known_grades[row["Subject"]]]
            earned_points += gp * row["Credit"]
            earned_credits += row["Credit"]

    remaining_credits = total_credits - earned_credits
    remaining_points = target_points - earned_points
    required_avg = remaining_points / remaining_credits if remaining_credits else 0

    st.header("🎯 CGPA Strategy (Points-Based)")
    st.success(verdict_text(required_avg))

    st.metric("Target Points", round(target_points, 2))
    st.metric("Earned Points", round(earned_points, 2))
    st.metric("Remaining Avg Grade", round(required_avg, 2))

    st.markdown("## 📊 Subject-wise Minimum Grade Needed")

    plan = []
    for _, row in df.iterrows():
        if row["Subject"] in known_grades:
            g = known_grades[row["Subject"]]
        else:
            g = grade_from_points(required_avg)

        plan.append([
            row["Subject"],
            row["Credit"],
            g,
            GRADE_POINTS[g],
            GRADE_TO_MARK[g]
        ])

    st.dataframe(
        pd.DataFrame(
            plan,
            columns=["Subject", "Credits", "Suggested Grade", "Grade Points", "Approx End-Sem Marks"]
        ),
        use_container_width=True
    )

    if st.button("🔄 Start Over"):
        st.session_state.step = 1





