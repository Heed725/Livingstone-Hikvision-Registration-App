# Livingstone Hikvision Registration

A mobile-friendly Streamlit application where an employee selects their own record and registers a face photograph or fingerprint on a compatible Hikvision access-control terminal.

## Safety design

- A registration PIN is required before biometric enrollment.
- The session expires after 10 minutes.
- The employee must confirm that they selected their own name.
- Device credentials are stored only in Streamlit secrets.
- Face images and fingerprint templates are not stored by this app.
- Phone photographs are resized and compressed before being sent to the terminal.
- Fingerprints are captured by the physical Hikvision terminal, not the phone.

Run enrollment only under administrator supervision. Biometric information is sensitive personal data.

## Local installation

```cmd
git clone https://github.com/Heed725/Livingstone-Hikvision-Registration-App.git
cd livingstone-hikvision-registration
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
notepad .streamlit\secrets.toml
streamlit run app.py
```

## Streamlit Community Cloud

1. Push this folder to a private GitHub repository.
2. Open Streamlit Community Cloud and select the repository.
3. Set the main file to `app.py`.
4. Open **Advanced settings → Secrets**.
5. Copy the values from `.streamlit/secrets.toml.example` and replace every placeholder.
6. Deploy the app.

Never commit `.streamlit/secrets.toml`.

## Device requirements

The terminal should report support for these ISAPI capabilities:

- `isSupportUserInfo`
- `isSupportFDLib`
- `isSupportCaptureFace`
- `isSupportFingerPrintCfg`
- `isSupportCaptureFingerPrint`

## Enrollment flow

1. The app hides employees who already have a face or fingerprint on the terminal; an unregistered employee selects their ID and name.
2. Employee enters the administrator-provided registration PIN.
3. The app checks that the employee exists on the Hikvision terminal and creates the record if missing.
4. For face enrollment, the employee uses the phone camera or uploads a clear JPEG.
5. For fingerprint enrollment, the employee stands at the physical terminal and captures one finger in slot 1. Yellow indicates waiting; green confirms successful capture and registration.

## Important hosting limitation

The Streamlit server must be able to reach the Hikvision terminal. Prefer a VPN or private network route. Avoid exposing the terminal directly to the public internet.
