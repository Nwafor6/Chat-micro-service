import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Union

import requests
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from loguru import logger as LOGGER

from app.core.config import settings


# pylint: disable=too-many-instance-attributes
class Mail:
    """
    A class to send emails using either SMTP or Mailgun API.

    Attributes:
        subject (Optional[str]): Subject of the email.
        recipients (List[str]): List of recipient email addresses.
        sender (str): Sender email address.
        mail_driver (str): Email driver (smtp or mailgun).
        smtp_server (str): SMTP server address.
        smtp_port (int): SMTP port number.
        smtp_user (str): SMTP username.
        smtp_password (str): SMTP password.
        mailgun_domain (str): Mailgun domain.
        mailgun_api_key (str): Mailgun API key.
        use_ssl (bool): Whether to use SSL (auto-detected).
        use_tls (bool): Whether to use STARTTLS (auto-detected).
        env (Environment): Jinja2 environment for rendering templates.
    """

    def __init__(
        self, subject: Optional[str] = None, to: Optional[Union[str, List[str]]] = None
    ) -> None:
        """
        Initializes the Mail class with optional subject and recipients.

        Args:
            subject (Optional[str]): Email subject.
            to (Optional[Union[str, List[str]]]): Recipient email or list of emails.
        """
        self.subject_text = subject or "No Subject"
        if to:
            self.recipients = [to] if isinstance(to, str) else to or []
        else:
            self.recipients = []
        self.sender = f"{settings.app_name} <{settings.mail_from_address}>"

        # Determine mail driver
        self.mail_driver: str = settings.mail_driver.lower()

        # SMTP Settings
        self.smtp_server: str = settings.mail_host
        self.smtp_port: int = int(settings.mail_port)
        self.smtp_user: str = settings.mail_username
        self.smtp_password: str = settings.mail_password

        # Mailgun Settings
        self.mailgun_domain: str = settings.mailgun_domain
        self.mailgun_api_key: str = settings.mailgun_secret

        # Auto-detect SSL/TLS usage
        self.use_ssl: bool = self.smtp_port == 465
        self.use_tls: bool = not self.use_ssl

        # Jinja2 setup
        template_dir = os.path.join(os.path.dirname(__file__), "templates")

        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        env.globals["now"] = lambda: datetime.now(timezone.utc)  # Adds `now()` globally
        self.env = env

        LOGGER.info(
            "Mail initialized. Driver: %s, SMTP: %s, Port: %d, SSL: %s, TLS: %s",
            self.mail_driver,
            self.smtp_server,
            self.smtp_port,
            self.use_ssl,
            self.use_tls,
        )

    def to(self, recipients: Union[str, List[str]]) -> "Mail":
        """Sets the recipient email address(es)."""
        if isinstance(recipients, str):
            self.recipients.append(recipients)
        else:
            self.recipients = recipients
        return self

    def subject(self, subject: str) -> "Mail":
        """Sets the email subject."""
        self.subject_text = subject
        return self

    def render_template(self, template_name: str, context: Dict[str, str]) -> str:
        """Render Jinja2 email template from lib/mail/templates/."""
        if not template_name.endswith(".html"):
            template_name += ".html"
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound as error:
            raise FileNotFoundError(
                f"Email template '{template_name}' not found."
            ) from error
        return template.render(context)

    def send(
        self,
        template_name: Optional[str] = None,
        context: Optional[dict] = None,
        html_content: Optional[str] = None,
    ) -> None:
        """
        Sends an email using the configured mail driver.

        Args:
            template (Optional[str]): Template name (without `.html` extension).
            context (Optional[dict]): Context variables for the template.
            html_content (Optional[str]): Direct HTML content (overrides template).

        Raises:
            ValueError: If email sending fails.
        """
        if not self.recipients:
            raise ValueError("Recipient email is required.")
        if not self.subject_text:
            raise ValueError("Subject is required.")

        if html_content:
            email_body = html_content
        elif template_name and context:
            email_body = self.render_template(template_name, context)
        else:
            raise ValueError(
                "Either a template name with context or raw HTML content must be provided."
            )

        if self.mail_driver == "mailgun":
            self._send_via_mailgun(email_body)
        elif self.mail_driver == "smtp":
            self._send_via_smtp(email_body)
        else:
            raise ValueError("Invalid mail driver: Use 'smtp' or 'mailgun'.")

    def _send_via_smtp(self, email_body: str) -> None:
        """Sends an email using SMTP with automatic SSL/TLS detection."""
        msg = MIMEMultipart()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = self.subject_text
        msg.attach(MIMEText(email_body, "html"))

        try:
            if self.use_ssl:
                LOGGER.info("Using SMTP_SSL on port %d", self.smtp_port)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.smtp_server, self.smtp_port, context=context
                ) as server:
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    else:
                        LOGGER.info(
                            "Skipping SMTP authentication as no credentials were provided."
                        )
                    server.sendmail(self.sender, self.recipients, msg.as_string())

            else:
                LOGGER.info(
                    "Using plain SMTP on port %d (STARTTLS disabled)", self.smtp_port
                )
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.ehlo()
                    try:
                        if server.has_extn("STARTTLS"):
                            server.starttls(context=ssl.create_default_context())
                            server.ehlo()
                            LOGGER.info("STARTTLS enabled")
                        else:
                            LOGGER.warning(
                                "STARTTLS not supported by server. Proceeding without encryption."
                            )

                        if self.smtp_user and self.smtp_password:
                            server.login(self.smtp_user, self.smtp_password)
                        else:
                            LOGGER.info(
                                "Skipping SMTP authentication as no credentials were provided."
                            )

                        server.sendmail(self.sender, self.recipients, msg.as_string())

                    except smtplib.SMTPException as e:
                        LOGGER.error("Error during SMTP connection: %s", str(e))
                        raise

            LOGGER.info(
                "Email successfully sent to %s via SMTP", ", ".join(self.recipients)
            )

        except smtplib.SMTPException as e:
            LOGGER.error("SMTP error: %s", str(e))
            raise

    def _send_via_mailgun(self, email_body: str) -> None:
        """Sends an email using Mailgun API."""
        if not self.mailgun_domain or not self.mailgun_api_key:
            LOGGER.error("Mailgun credentials missing. Email not sent.")
            return

        mailgun_url = f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages"
        auth = ("api", self.mailgun_api_key)
        data = {
            "from": self.sender,
            "to": self.recipients,
            "subject": self.subject_text,
            "html": email_body,
        }

        try:
            response = requests.post(mailgun_url, auth=auth, data=data)
            response.raise_for_status()
            LOGGER.info(
                "Email successfully sent to %s via Mailgun", ", ".join(self.recipients)
            )
        except requests.RequestException as e:
            LOGGER.error("Mailgun API error: %s", str(e))
            raise
