import base64
import hashlib

import httpx
from cryptography.fernet import Fernet, InvalidToken


def _derive_fernet_key(secret_key: str) -> bytes:
    """Derive a Fernet-compatible key from the app secret_key."""
    key = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_secret(plain: str, secret_key: str) -> str:
    """Encrypt a plaintext string using Fernet symmetric encryption."""
    f = Fernet(_derive_fernet_key(secret_key))
    return f.encrypt(plain.encode()).decode()


def decrypt_secret(cipher: str, secret_key: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    f = Fernet(_derive_fernet_key(secret_key))
    try:
        return f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        return ""


async def test_erpnext_connection(url: str, api_key: str, api_secret: str) -> dict:
    """Test ERPNext connection by calling get_logged_user."""
    url = url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(
                f"{url}/api/method/frappe.auth.get_logged_user",
                headers={
                    "Authorization": f"token {api_key}:{api_secret}",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "user": data.get("message", "")}
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"success": False, "error": f"Cannot connect to {url}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def test_nextcloud_connection(url: str, username: str, password: str) -> dict:
    """Test Nextcloud connection by calling the OCS user endpoint."""
    url = url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(
                f"{url}/ocs/v1.php/cloud/user",
                auth=(username, password),
                headers={"OCS-APIRequest": "true", "Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                ocs = data.get("ocs", {})
                meta = ocs.get("meta", {})
                if meta.get("statuscode") == 100:
                    user_data = ocs.get("data", {})
                    return {
                        "success": True,
                        "user": user_data.get("display-name") or user_data.get("id", username),
                    }
                return {"success": False, "error": f"OCS error: {meta.get('message', 'Unknown')}"}
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"success": False, "error": f"Cannot connect to {url}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
