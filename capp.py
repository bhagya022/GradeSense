import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re

# ---------------- CONFIG ----------------
#pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Hp\OneDrive\Desktop\Tesseract-OCR\tesseract.exe"
st.set_page_config(page_title="GradeSense", layout="centered")

st.title("GradeSense")

# ---------------- CONSTANTS ----------------
GRADE_POINTS = {"A+": 10, "A": 9, "B": 8, "C": 7, "D": 6}
GRADE_TO_MARK = {"A+": "60+", "A": "55+", "B": "50+", "C": "45+", "D": "40+"}

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
def internal_gp(internal):
    return (internal / 30) * 10

def verdict_text(target):
    if target >= 9.5:
        return "⚠️ Very difficult — requires almost all A+"
    elif target >= 9.0:
        return "✅ Achievable with strong performance in theory subjects"
    else:
        return "✅ Comfortably achievable"

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
    st.caption("Edit freely. Click **Confirm** to save. Click **Proceed** when done.")

    with st.form("edit_subjects_form"):
        edited_df = st.data_editor(
            st.session_state.df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["Theory", "Lab", "Internship", "Project"]
                )
            }
        )

        edited_df = edited_df.dropna(subset=["Subject"]).reset_index(drop=True)
        edited_df["S.No"] = range(1, len(edited_df) + 1)

        total_subjects = len(edited_df)
        total_credits = int(edited_df["Credit"].sum())
        theory_cnt = int((edited_df["Type"] == "Theory").sum())
        labs_other_cnt = total_subjects - theory_cnt

        st.info(
            f"""
            **Subjects:** {total_subjects}  
            **Total Credits:** {total_credits}  
            **Theory:** {theory_cnt}  
            **Labs / Other:** {labs_other_cnt}
            """
        )

        col1, col2, col3 = st.columns(3)
        back = col1.form_submit_button("⬅️ Back")
        confirm = col2.form_submit_button("💾 Confirm")
        proceed = col3.form_submit_button("➡️ Proceed")

    if back:
        st.session_state.step = 1

    if confirm:
        st.session_state.df = edited_df
        st.session_state.confirmed = True
        st.success("Changes confirmed. You can proceed or continue editing.")

    if proceed:
        if not st.session_state.confirmed:
            st.warning("Please confirm your changes before proceeding.")
        else:
            st.session_state.step = 3

# ---------------- STEP 3: INPUTS ----------------
elif st.session_state.step == 3:
    st.header("Step 3️⃣ Enter Known Information")

    df = st.session_state.df
    internals = {}
    non_theory = {}

    for idx, row in df.iterrows():
        if row["Type"] == "Theory":
            internals[row["Subject"]] = st.number_input(
                f"{row['Subject']} – Internal (out of 30)",
                0, 30, 20, 1,
                key=f"int_{idx}"
            )
        else:
            non_theory[row["Subject"]] = st.selectbox(
                f"{row['Subject']} – Expected Grade",
                list(GRADE_POINTS.keys()),
                index=1,
                key=f"grade_{idx}"
            )

    target = st.number_input(
        "Target CGPA",
        min_value=0.0, max_value=10.0, step=0.1
    )

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back"):
        st.session_state.step = 2
    if col2.button("Analyze & Get Strategy 🎯", type="primary"):
        st.session_state.inputs = (internals, non_theory, target)
        st.session_state.step = 4

# ---------------- STEP 4: FINAL ANALYSIS ----------------
elif st.session_state.step == 4:
    df = st.session_state.df
    internals, non_theory, target = st.session_state.inputs

    st.header("🎯 CGPA Strategy Analysis")
    st.subheader("Quick Verdict")
    st.success(verdict_text(target))

    st.markdown("## 📌 Option A — Simple Advisor")
    st.write(
        "- **3-credit theory subjects** → mostly **A+**\n"
        "- One 3-credit subject can drop to **A**\n"
        "- Labs / Internship → **A is enough**"
    )

    st.markdown("## 📊 Option B — Sample Subject-wise Plan")
    plan = []
    for _, row in df.iterrows():
        if row["Type"] == "Theory":
            grade = "A+" if row["Credit"] >= 3 else "A"
            plan.append([row["Subject"], row["Credit"], grade, GRADE_TO_MARK[grade]])
        else:
            plan.append([row["Subject"], row["Credit"], "A", "—"])

    st.dataframe(
        pd.DataFrame(plan, columns=["Subject", "Credits", "Suggested Grade", "Approx End-Sem Target"]),
        use_container_width=True
    )

    st.markdown("## 🧠 Option C — Strategy Comparison")
    st.write("🟢 Safe: All 3-credit → A+")
    st.write("🟡 Balanced: 2 × A+ + 1 × A")
    st.write("🔴 Risky: 1 × A+ + labs must be A+")

    st.markdown("### 🎓 Grade → Marks Guide")
    st.table(pd.DataFrame(GRADE_TO_MARK.items(), columns=["Grade", "End-Sem Target"]))

    if st.button("🔄 Start Over"):
        st.session_state.step = 1



