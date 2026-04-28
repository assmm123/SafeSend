import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="https://3ade92ae1026ec98d9933d9bfa080b68@o4511288747294720.ingest.us.sentry.io/4511288759091200",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    environment="production",
)
