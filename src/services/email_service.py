"""
Email Service - SafeSend
خدمة البريد الإلكتروني - SafeSend

Handles sending emails via SMTP with proper formatting.
يدير إرسال البريد الإلكتروني عبر SMTP مع تنسيق مناسب.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# SMTP Configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@safesend.io")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() == "true"

def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None
) -> bool:
    """
    Send an email via SMTP.
    إرسال بريد إلكتروني عبر SMTP.
    
    Args:
        to_email: Recipient email / البريد المستلم
        subject: Email subject / عنوان البريد
        body_html: HTML body / محتوى HTML
        body_text: Plain text body (optional) / محتوى نصي (اختياري)
    
    Returns:
        bool: True if sent successfully
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("email.smtp_not_configured", to=to_email, subject=subject)
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        
        if body_text:
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        
        if SMTP_USE_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        server.quit()
        
        logger.info("email.sent", to=to_email, subject=subject)
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("email.auth_failed", to=to_email)
        return False
    except smtplib.SMTPConnectError:
        logger.error("email.connection_failed", host=SMTP_HOST)
        return False
    except Exception as e:
        logger.error("email.send_failed", error=str(e), to=to_email)
        return False


def send_verification_email(to_email: str, verification_url: str, username: str = "") -> bool:
    """
    Send email verification link.
    إرسال رابط التحقق من البريد الإلكتروني.
    """
    subject = "SafeSend - تحقق من بريدك الإلكتروني / Verify Your Email"
    
    body_html = f"""
    <div style="font-family: Tahoma, Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px; background: #f8fafc; border-radius: 16px; direction: rtl;">
        <div style="text-align: center; padding: 16px 0;">
            <h1 style="color: #1a73e8; margin: 0;">🛡️ SafeSend</h1>
        </div>
        <div style="background: white; padding: 24px; border-radius: 12px;">
            <h2 style="margin: 0 0 12px; font-size: 18px;">مرحباً {username or 'بك'} 👋</h2>
            <p style="color: #555; line-height: 1.6;">شكراً لتسجيلك في SafeSend. يرجى تأكيد بريدك الإلكتروني بالضغط على الزر أدناه:</p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{verification_url}" style="background: #1a73e8; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block;">تأكيد البريد الإلكتروني</a>
            </div>
            <p style="color: #888; font-size: 12px;">الرابط صالح لمدة 24 ساعة. إذا لم تقم بالتسجيل، تجاهل هذا البريد.</p>
        </div>
        <p style="text-align: center; color: #aaa; font-size: 11px; margin-top: 12px;">SafeSend - منصة الوساطة المالية الرقمية</p>
    </div>
    """
    
    body_text = f"مرحباً {username or 'بك'}، شكراً لتسجيلك. لتأكيد بريدك: {verification_url}"
    
    return send_email(to_email, subject, body_html, body_text)


def send_password_reset_email(to_email: str, reset_url: str, username: str = "") -> bool:
    """
    Send password reset link.
    إرسال رابط إعادة تعيين كلمة المرور.
    """
    subject = "SafeSend - إعادة تعيين كلمة المرور / Password Reset"
    
    body_html = f"""
    <div style="font-family: Tahoma, Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px; background: #f8fafc; border-radius: 16px; direction: rtl;">
        <div style="text-align: center; padding: 16px 0;">
            <h1 style="color: #1a73e8; margin: 0;">🔐 SafeSend</h1>
        </div>
        <div style="background: white; padding: 24px; border-radius: 12px;">
            <h2 style="margin: 0 0 12px; font-size: 18px;">إعادة تعيين كلمة المرور</h2>
            <p style="color: #555; line-height: 1.6;">تلقينا طلباً لإعادة تعيين كلمة المرور لحساب <strong>{username or 'لديك'}</strong>. اضغط الزر أدناه لإعادة التعيين:</p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{reset_url}" style="background: #1a73e8; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block;">إعادة تعيين كلمة المرور</a>
            </div>
            <p style="color: #888; font-size: 12px;">الرابط صالح لمدة ساعة. إذا لم تطلب إعادة التعيين، تجاهل هذا البريد.</p>
        </div>
        <p style="text-align: center; color: #aaa; font-size: 11px; margin-top: 12px;">SafeSend - منصة الوساطة المالية الرقمية</p>
    </div>
    """
    
    body_text = f"تلقينا طلباً لإعادة تعيين كلمة المرور. استخدم الرابط: {reset_url}"
    
    return send_email(to_email, subject, body_html, body_text)


__all__ = [
    'send_email',
    'send_verification_email',
    'send_password_reset_email'
]
