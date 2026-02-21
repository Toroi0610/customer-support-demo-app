"""GoogleAuthService - provides Google Cloud access tokens via ADC."""
import google.auth
from google.auth.transport.requests import Request


class GoogleAuthService:
    """Retrieves Google Cloud access tokens using Application Default Credentials.

    This is the single place in the codebase that touches Google auth.
    Swap this class to use a service-account key file or a mock in tests.
    """

    def get_access_token(self) -> str:
        """Return a valid bearer token, refreshing if necessary.

        Returns an empty string on failure (caller decides how to handle).
        """
        try:
            creds, _ = google.auth.default()
            if not creds.valid:
                creds.refresh(Request())
            return creds.token
        except Exception as exc:
            print(f"Error generating access token: {exc}")
            print("Run: gcloud auth application-default login")
            return ""
