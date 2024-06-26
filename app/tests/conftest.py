import os

import pytest

# Set environment variables before other imports
os.environ["DB_URI"] = "sqlite:///:memory:"
os.environ["VSTORE_URI"] = "sqlite:///:memory:"
os.environ[
    "OAUTH2_OPENID_CONFIGURATION"
] = "http://localhost:9999/.well-known/openid-configuration"
os.environ["OAUTH2_AUDIENCE"] = "test_audience"
os.environ["SLACK_CLIENT_ID"] = "slack_client_id"
os.environ["SLACK_CLIENT_SECRET"] = "slack_client_secret"
os.environ["SLACK_SIGNING_SECRET"] = "slack_signing_secret"


@pytest.fixture(scope="session", autouse=True)
def setup_teardown():
    del os.environ["DB_URI"]
    del os.environ["VSTORE_URI"]
    del os.environ["OAUTH2_OPENID_CONFIGURATION"]
    del os.environ["OAUTH2_AUDIENCE"]
    del os.environ["SLACK_CLIENT_ID"]
    del os.environ["SLACK_CLIENT_SECRET"]
    del os.environ["SLACK_SIGNING_SECRET"]
