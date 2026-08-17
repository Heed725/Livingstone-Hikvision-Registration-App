from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from PIL import Image, ImageOps
from requests.auth import HTTPDigestAuth
from requests.exceptions import RequestException


class HikvisionError(RuntimeError):
    pass


@dataclass
class FingerprintCapture:
    data: str | None
    quality: int | None = None
    message: str = ""


def _xml_map(text: str) -> dict[str, str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return {}
    return {node.tag.rsplit("}", 1)[-1]: (node.text or "").strip() for node in root.iter()}


def response_message(response: requests.Response) -> str:
    try:
        body = response.json()
        status = body.get("ResponseStatus", body)
        return str(status.get("subStatusCode") or status.get("statusString") or response.reason)
    except ValueError:
        values = _xml_map(response.text)
        return values.get("subStatusCode") or values.get("statusString") or response.reason


class HikvisionClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 45, verify_tls: bool = False):
        if not base_url.startswith(("http://", "https://")):
            raise HikvisionError("The Hikvision URL must start with http:// or https://")
        if not username or not password:
            raise HikvisionError("Hikvision username and password are not configured.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.session = requests.Session()
        self.session.auth = HTTPDigestAuth(username, password)
        self.session.headers["User-Agent"] = "Livingstone-Registration/1.0"
        # Hikvision embedded web servers are more reliable without persistent connections.
        self.session.headers["Connection"] = "close"

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", self.verify_tls)
        try:
            response = self.session.request(method, f"{self.base_url}{path}", **kwargs)
        except RequestException as exc:
            raise HikvisionError(f"Could not reach the Hikvision terminal: {exc}") from exc
        if response.status_code == 401:
            raise HikvisionError("Hikvision authentication failed. Contact the administrator.")
        return response

    def find_user(self, employee_no: str) -> dict | None:
        body = {
            "UserInfoSearchCond": {
                "searchID": f"livingstone-{employee_no}",
                "searchResultPosition": 0,
                "maxResults": 1,
                "EmployeeNoList": [{"employeeNo": employee_no}],
            }
        }
        response = self.request("POST", "/ISAPI/AccessControl/UserInfo/Search?format=json", json=body)
        if not response.ok:
            raise HikvisionError(f"Employee lookup failed: {response_message(response)}")
        try:
            result = response.json().get("UserInfoSearch", {})
            users = result.get("UserInfo", [])
            if isinstance(users, dict):
                users = [users]
            return users[0] if users else None
        except ValueError as exc:
            raise HikvisionError("The device returned an unreadable employee-search response.") from exc

    def registered_employee_ids(self, employee_ids: list[str]) -> set[str]:
        """Return employees who already have at least one face or fingerprint."""
        if not employee_ids:
            return set()
        payload = {
            "UserInfoSearchCond": {
                "searchID": "livingstone-registration-status",
                "searchResultPosition": 0,
                "maxResults": len(employee_ids),
                "EmployeeNoList": [{"employeeNo": employee_id} for employee_id in employee_ids],
            }
        }
        response = self.request(
            "POST", "/ISAPI/AccessControl/UserInfo/Search?format=json", json=payload
        )
        if not response.ok:
            raise HikvisionError(
                f"Could not check registration status: {response_message(response)}"
            )
        try:
            users = response.json().get("UserInfoSearch", {}).get("UserInfo", [])
        except ValueError as exc:
            raise HikvisionError(
                "The device returned an unreadable registration-status response."
            ) from exc
        if isinstance(users, dict):
            users = [users]

        registered: set[str] = set()
        count_fields = (
            "numOfFace",
            "numOfFP",
            "numOfFingerPrint",
            "faceNum",
            "fingerPrintNum",
        )
        for user in users:
            for field in count_fields:
                try:
                    if int(user.get(field, 0) or 0) > 0:
                        registered.add(str(user.get("employeeNo", "")))
                        break
                except (TypeError, ValueError):
                    continue
        return registered

    def create_user(self, employee: dict) -> requests.Response:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        payload = {
            "UserInfo": {
                "employeeNo": employee["id"],
                "name": f"{employee['first_name']} {employee['last_name']}",
                "userType": "normal",
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "Valid": {
                    "enable": True,
                    "beginTime": now,
                    "endTime": "2036-05-01T23:59:59",
                    "timeType": "local",
                },
            }
        }
        return self.request("POST", "/ISAPI/AccessControl/UserInfo/Record?format=json", json=payload)

    @staticmethod
    def prepare_face_image(image: bytes) -> bytes:
        """Convert phone photos to a Hikvision-friendly JPEG below 200 KB."""
        try:
            with Image.open(io.BytesIO(image)) as source:
                prepared = ImageOps.exif_transpose(source).convert("RGB")
                prepared.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
                for quality in (88, 80, 72, 64, 56, 48):
                    output = io.BytesIO()
                    prepared.save(output, format="JPEG", quality=quality, optimize=True)
                    result = output.getvalue()
                    if len(result) <= 200 * 1024:
                        return result
                return result
        except (OSError, ValueError) as exc:
            raise HikvisionError("The selected face photograph is not a readable JPEG image.") from exc

    def upload_face(self, employee_no: str, image: bytes, filename: str) -> requests.Response:
        metadata = {"faceLibType": "blackFD", "FDID": "1", "FPID": employee_no}
        prepared_image = self.prepare_face_image(image)
        files = {
            "FaceDataRecord": (None, json.dumps(metadata), "application/json"),
            "FaceImage": ("face.jpg", prepared_image, "image/jpeg"),
        }
        return self.request("POST", "/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json", files=files)

    def capture_fingerprint(self, finger_id: int = 1) -> FingerprintCapture:
        response = self.request(
            "POST",
            "/ISAPI/AccessControl/CaptureFingerPrint?format=json",
            json={"CaptureFingerPrintCond": {"fingerNo": finger_id}},
            timeout=max(self.timeout, 60),
        )

        if not response.ok and "badxml" in response_message(response).replace(" ", "").lower():
            xml_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<CaptureFingerPrintCond version="2.0" '
                'xmlns="http://www.isapi.org/ver20/XMLSchema">'
                f"<fingerNo>{finger_id}</fingerNo>"
                "</CaptureFingerPrintCond>"
            )
            response = self.request(
                "POST",
                "/ISAPI/AccessControl/CaptureFingerPrint",
                data=xml_payload.encode("utf-8"),
                headers={"Content-Type": "application/xml"},
                timeout=max(self.timeout, 60),
            )

        if not response.ok:
            return FingerprintCapture(None, message=response_message(response))
        try:
            body = response.json()
            captured = (
                body.get("CaptureFingerPrintResult")
                or body.get("CaptureFingerPrint")
                or body
            )
            data = captured.get("fingerData") or captured.get("fingerPrintData")
            quality = captured.get("fingerPrintQuality") or captured.get("quality")
        except ValueError:
            values = _xml_map(response.text)
            data = values.get("fingerData") or values.get("fingerPrintData")
            quality = values.get("fingerPrintQuality") or values.get("quality")
        try:
            quality_value = int(quality) if quality is not None else None
        except (TypeError, ValueError):
            quality_value = None
        return FingerprintCapture(data, quality_value, response_message(response))

    def apply_fingerprint(self, employee_no: str, finger_data: str, finger_id: int) -> requests.Response:
        payload = {
            "FingerPrintCfg": {
                "employeeNo": employee_no,
                "enableCardReader": [1],
                "fingerPrintID": finger_id,
                "fingerType": "normalFP",
                "fingerData": finger_data,
            }
        }
        return self.request("POST", "/ISAPI/AccessControl/FingerPrintDownload?format=json", json=payload)
