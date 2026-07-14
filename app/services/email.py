from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import get_settings


def send_verification_email(recipient: str, code: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError("邮件服务尚未配置，请设置 SMTP_HOST、SMTP_USERNAME 和 SMTP_PASSWORD")

    message = EmailMessage()
    message["Subject"] = "DataPulse 注册验证码"
    message["From"] = settings.smtp_from_email or settings.smtp_username
    message["To"] = recipient
    message.set_content(
        f"您好！\n\n您正在注册 DataPulse 智能决策平台。\n\n"
        f"验证码：{code}\n\n"
        f"验证码将在 {settings.email_code_expire_minutes} 分钟后失效，请勿转发给他人。\n"
        "如果这不是您的操作，请忽略此邮件。"
    )
    message.add_alternative(
        f"""<!doctype html><html><body style="margin:0;background:#f3f6fa;font-family:Arial,'Microsoft YaHei',sans-serif;color:#172033">
        <div style="max-width:520px;margin:32px auto;background:#fff;border-radius:14px;overflow:hidden;border:1px solid #e4eaf1">
          <div style="padding:24px 30px;background:#111d31;color:#fff"><b style="font-size:18px">DataPulse</b><span style="margin-left:10px;color:#7f91aa;font-size:12px">智能决策平台</span></div>
          <div style="padding:32px 30px"><h2 style="margin:0 0 14px;font-size:20px">验证您的邮箱</h2><p style="font-size:14px;color:#69788c;line-height:1.8">您正在注册 DataPulse，请输入以下验证码完成邮箱验证：</p>
          <div style="margin:26px 0;padding:18px;text-align:center;background:#edf5ff;border-radius:10px;color:#287bd7;font-size:30px;font-weight:bold;letter-spacing:8px">{code}</div>
          <p style="font-size:12px;color:#8e99a8">验证码将在 {settings.email_code_expire_minutes} 分钟后失效，请勿转发给他人。</p></div>
        </div></body></html>""",
        subtype="html",
    )

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
