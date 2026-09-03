import os
import time
import smtplib
import cv2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import core.config_manager as config_mgr
from core.framework import framework

class GmailNotifierService:
    """
    OSGi Service Bundle: Gmail SMTP Alert & Notification Engine.
    Subscribes to 'UNKNOWN_PERSON_ALERT' events on the EventBus.
    Sends emails with snapshot attachments via Gmail SMTP.
    """
    def __init__(self):
        self.last_alert_time = 0

    def start(self):
        """Activates the service and subscribes to EventBus."""
        framework.event_bus.subscribe("UNKNOWN_PERSON_ALERT", self.handle_alert)
        print("[OSGi Plugin] GmailNotifierService ACTIVE & subscribed to UNKNOWN_PERSON_ALERT.")

    def stop(self):
        """Deactivates the service and unsubscribes from EventBus."""
        framework.event_bus.unsubscribe("UNKNOWN_PERSON_ALERT", self.handle_alert)
        print("[OSGi Plugin] GmailNotifierService RESOLVED (Unsubscribed).")

    def handle_alert(self, alert_data):
        """Handles alert event triggered by AI Analytics plugin."""
        smtp_cfg = config_mgr.load_smtp_config()
        if not smtp_cfg.get("enabled"):
            return

        now = time.time()
        cooldown = smtp_cfg.get("cooldown_seconds", 180)
        if now - self.last_alert_time < cooldown:
            print(f"[Gmail Notifier] Alert skipped (Cooldown active: {int(cooldown - (now - self.last_alert_time))}s remaining).")
            return

        sender = smtp_cfg.get("sender_email")
        password = smtp_cfg.get("app_password")
        recipient = smtp_cfg.get("recipient_email")

        if not sender or not password or not recipient:
            print("[Gmail Notifier] Cannot send email: Sender, Password, or Recipient missing.")
            return

        # Extract snapshot image
        frame = alert_data.get("frame")
        camera_name = alert_data.get("camera", "Camera")
        timestamp_str = alert_data.get("timestamp", time.strftime("%H:%M:%S"))

        snapshot_path = None
        if frame is not None:
            filename = f"alert_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            snapshot_path = os.path.join(config_mgr.ALERTS_DIR, filename)
            cv2.imwrite(snapshot_path, frame)

        # Send email asynchronously
        self.last_alert_time = now
        self._send_email_async(sender, password, recipient, camera_name, timestamp_str, snapshot_path)

    def _send_email_async(self, sender, password, recipient, camera_name, timestamp_str, snapshot_path):
        """Performs SMTP transmission in background thread."""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"🚨 SECURITY ALERT: Unknown Person Detected on {camera_name}"
            msg['From'] = sender
            msg['To'] = recipient

            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #070b13; color: #ffffff; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: #141b2d; border: 1px solid #ef4444; border-radius: 12px; padding: 20px;">
                    <h2 style="color: #ef4444;">🚨 SECURITY ALERT: UNKNOWN PERSON DETECTED</h2>
                    <p><strong>Camera:</strong> {camera_name}</p>
                    <p><strong>Timestamp:</strong> {timestamp_str}</p>
                    <p style="color: #94a3b8;">An unrecognized person was detected by VisionGuard AI Analytics. The snapshot image is attached below.</p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))

            # Attach snapshot image
            if snapshot_path and os.path.exists(snapshot_path):
                with open(snapshot_path, 'rb') as f:
                    img_data = f.read()
                    image = MIMEImage(img_data, name=os.path.basename(snapshot_path))
                    msg.attach(image)

            print(f"[Gmail Notifier] Transmitting alert email to {recipient} via smtp.gmail.com:587...")
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
            server.quit()
            print(f"[Gmail Notifier] ✅ Email alert successfully delivered to {recipient}!")

        except Exception as e:
            print(f"[Gmail Notifier] ❌ SMTP Error: {e}")

# Register service into OSGi framework
notifier_service = GmailNotifierService()
framework.register_service("gmail_notifier_service", notifier_service)
