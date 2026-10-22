import smtplib
from email.message import EmailMessage

from flask import current_app, url_for


def send_link_email(user, kind, raw_token):
    endpoint = "auth.verify_email" if kind == "verify" else "auth.reset_password"
    link = url_for(endpoint, token=raw_token, _external=True)
    subject = "Verify your EchoGuard AI email" if kind == "verify" else "Reset your EchoGuard AI password"
    body = (
        f"Hi {user.name},\n\n"
        f"Use this one-time EchoGuard AI link within the expiry window:\n{link}\n\n"
        "If you did not request this, you can safely ignore it."
    )
    host = current_app.config.get("SMTP_HOST")
    if not host:
        if current_app.config.get("APP_ENV") == "development":
            current_app.logger.info("DEVELOPMENT OUTBOX [%s] %s -> %s", kind, user.email, link)
            return {"delivered": False, "development_link": link}
        current_app.logger.error("Email delivery is not configured; no %s link was emitted.", kind)
        return {"delivered": False}
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["MAIL_FROM"]
    message["To"] = user.email
    message.set_content(body)
    with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=10) as server:
        if current_app.config["SMTP_USE_TLS"]:
            server.starttls()
        if current_app.config.get("SMTP_USERNAME"):
            server.login(current_app.config["SMTP_USERNAME"], current_app.config["SMTP_PASSWORD"])
        server.send_message(message)
    return {"delivered": True}
