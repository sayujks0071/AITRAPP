"""Simple notification service (Telegram webhook)."""
import os
import requests
import structlog

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    
    def channels(self):
        channels = []
        if self.token and self.chat_id:
            channels.append("telegram")
        if self.slack_webhook:
            channels.append("slack")
        return channels
    
    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id) or bool(self.slack_webhook)
    
    def _send_telegram(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": self.chat_id, "text": message},
            timeout=5
        )
        resp.raise_for_status()

    def _send_slack(self, message: str) -> None:
        resp = requests.post(
            self.slack_webhook,
            json={"text": message},
            timeout=5
        )
        resp.raise_for_status()

    def send(self, message: str, level: str = "INFO") -> None:
        if not self.is_configured():
            return
        try:
            prefix = f"[{level}] " if level else ""
            payload = f"{prefix}{message}"
            if self.token and self.chat_id:
                self._send_telegram(payload)
            if self.slack_webhook:
                self._send_slack(payload)
        except Exception as e:
            logger.warning("Notification send failed", error=str(e))
