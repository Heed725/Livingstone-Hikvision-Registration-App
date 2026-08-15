from __future__ import annotations

import hashlib
import os
import time

import streamlit as st

from employees import EMPLOYEES, employee_label
from hikvision import HikvisionClient, HikvisionError, response_message


st.set_page_config(
    page_title="Livingstone Hikvision Registration",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .stApp {background:#f4f7f5;}
      .block-container {max-width:720px;padding:1rem 1rem 5rem;}
      h1 {font-size:1.65rem !important;line-height:1.2;margin-bottom:.15rem;}
      h2,h3 {color:#183d2a;}
      div[data-testid="stForm"] {background:white;border:1px solid #dce7df;
        border-radius:18px;padding:1rem;box-shadow:0 8px 24px rgba(16,52,32,.06);}
      .employee-card {background:#eaf5ed;border:1px solid #bdd9c5;border-radius:14px;
        padding:14px 16px;margin:.5rem 0 1rem;}
      .employee-name {font-size:1.12rem;font-weight:700;color:#173e28;}
      .employee-meta {font-size:.88rem;color:#496354;margin-top:4px;}
      .step {display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;
        border-radius:50%;background:#1f6b3b;color:white;font-weight:700;margin-right:7px;}
      .stButton>button,.stFormSubmitButton>button {min-height:48px;border-radius:12px;font-weight:650;}
      div[data-testid="stCameraInput"] button {min-height:48px;}
      @media (max-width:600px) {
        .block-container {padding:.75rem .75rem 4.5rem;}
        h1 {font-size:1.42rem !important;}
        div[data-testid="stForm"] {padding:.8rem;border-radius:14px;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def config(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except Exception:
        return os.getenv(name, default)


def secure_equal(left: str, right: str) -> bool:
    return bool(left and right) and hashlib.sha256(left.encode()).digest() == hashlib.sha256(right.encode()).digest()


def device() -> HikvisionClient:
    return HikvisionClient(
        base_url=config("HIKVISION_URL"),
        username=config("HIKVISION_USERNAME", "admin"),
        password=config("HIKVISION_PASSWORD"),
        timeout=int(config("HIKVISION_TIMEOUT", "45")),
        verify_tls=config("HIKVISION_VERIFY_TLS", "false").lower() == "true",
    )


def reset_session() -> None:
    for key in ("verified_employee", "verified_at", "face_done", "fingerprint_done"):
        st.session_state.pop(key, None)


def verified_employee():
    employee_id = st.session_state.get("verified_employee")
    verified_at = st.session_state.get("verified_at", 0)
    if not employee_id or time.time() - verified_at > 600:
        reset_session()
        return None
    return next((item for item in EMPLOYEES if item["id"] == employee_id), None)


st.title("Livingstone Hikvision Registration")
st.caption("Register your face or fingerprint securely")

if not all((config("HIKVISION_URL"), config("HIKVISION_PASSWORD"), config("ENROLLMENT_PIN"))):
    st.error("The administrator must configure the device URL, device password and enrollment PIN in Streamlit secrets.")
    st.stop()

current = verified_employee()

if current is None:
    st.markdown('<h3><span class="step">1</span>Select and verify yourself</h3>', unsafe_allow_html=True)
    choices = {employee_label(item): item for item in EMPLOYEES}
    with st.form("identify", clear_on_submit=False):
        selected_label = st.selectbox(
            "Employee",
            options=list(choices),
            index=None,
            placeholder="Tap to select your name",
        )
        pin = st.text_input("Registration PIN", type="password", placeholder="Enter the PIN provided by the administrator")
        accepted = st.checkbox("I confirm that I selected my own name.")
        submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
    if submitted:
        if selected_label is None:
            st.error("Select your name.")
        elif not accepted:
            st.error("Confirm that you selected your own name.")
        elif not secure_equal(pin, config("ENROLLMENT_PIN")):
            st.error("Incorrect registration PIN.")
        else:
            selected = choices[selected_label]
            st.session_state.verified_employee = selected["id"]
            st.session_state.verified_at = time.time()
            st.rerun()
    st.info("Registration should be supervised by an authorized administrator.")
    st.stop()

st.markdown(
    f"""
    <div class="employee-card">
      <div class="employee-name">{current['id']} · {current['first_name']} {current['last_name']}</div>
      <div class="employee-meta">{current['department']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("This is not me — change employee", use_container_width=True):
    reset_session()
    st.rerun()

try:
    api = device()
    lookup = api.find_user(current["id"])
    if lookup is None:
        with st.spinner("Creating your employee record on the device…"):
            created = api.create_user(current)
        if not created.ok:
            st.error(f"Employee record could not be created: {response_message(created)}")
            st.stop()
        st.success("Employee record created on the device.")
except HikvisionError as exc:
    st.error(str(exc))
    st.stop()

st.markdown('<h3><span class="step">2</span>Choose registration method</h3>', unsafe_allow_html=True)
face_tab, fingerprint_tab = st.tabs(["Face", "Fingerprint"])

with face_tab:
    st.write("Look directly at the camera in good light. Remove sunglasses, hats and face coverings.")
    face_photo = st.camera_input("Take your face photograph")
    uploaded_photo = st.file_uploader("Or choose a JPEG photograph", type=["jpg", "jpeg"])
    photo = face_photo or uploaded_photo
    if st.button("Register my face", type="primary", use_container_width=True, disabled=photo is None):
        try:
            with st.spinner("Sending face photograph to the Hikvision device…"):
                result = api.upload_face(current["id"], photo.getvalue(), photo.name or "face.jpg")
            if result.ok:
                st.session_state.face_done = True
                st.success("Face registration completed successfully.")
            else:
                st.error(f"Face registration failed: {response_message(result)}")
        except HikvisionError as exc:
            st.error(str(exc))

with fingerprint_tab:
    st.warning("Stand next to the Livingstone Hikvision terminal before starting. The fingerprint is captured by the terminal—not by your phone.")
    finger_number = st.selectbox("Finger slot", range(1, 11), format_func=lambda value: f"Fingerprint {value}")
    if st.button("Start fingerprint capture", type="primary", use_container_width=True):
        try:
            with st.spinner("Place your finger firmly on the terminal sensor…"):
                captured = api.capture_fingerprint(int(finger_number))
            if not captured.data:
                st.error(captured.message or "No fingerprint data was returned. Try again.")
            else:
                if captured.quality is not None:
                    st.metric("Capture quality", f"{captured.quality}%")
                with st.spinner("Registering fingerprint…"):
                    result = api.apply_fingerprint(current["id"], captured.data, int(finger_number))
                if result.ok:
                    st.session_state.fingerprint_done = True
                    st.success("Fingerprint registration completed successfully.")
                else:
                    st.error(f"Fingerprint registration failed: {response_message(result)}")
        except HikvisionError as exc:
            st.error(str(exc))

if st.session_state.get("face_done") or st.session_state.get("fingerprint_done"):
    st.divider()
    st.success("Registration saved. You may finish or register the other biometric method.")
    if st.button("Finish and sign out", use_container_width=True):
        reset_session()
        st.rerun()

st.caption("Your biometric information is sent directly to the configured Hikvision terminal and is not stored by this Streamlit application.")
