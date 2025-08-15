import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from datetime import datetime

from app.config.config import settings
from app.utils.helpers import get_current_time
from loguru import logger

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.EMAIL_FROM
        self.use_tls = True  # Default to TLS
        self.templates_dir = "./email_templates"  # Default templates directory
        
        # Create templates directory if it doesn't exist
        Path(self.templates_dir).mkdir(parents=True, exist_ok=True)
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates if they don't exist"""
        templates = {
            "booking_confirmation.html": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; }
                    .container { width: 100%; max-width: 600px; margin: 0 auto; }
                    .header { background-color: #4a90e2; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    .footer { background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }
                    .booking-details { background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #4a90e2; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Booking Confirmation</h1>
                    </div>
                    <div class="content">
                        <p>Dear {guest_name},</p>
                        <p>Thank you for choosing our hotel. Your booking has been confirmed.</p>
                        
                        <div class="booking-details">
                            <h3>Booking Details:</h3>
                            <p><strong>Booking ID:</strong> {booking_id}</p>
                            <p><strong>Check-in:</strong> {checkin_date}</p>
                            <p><strong>Check-out:</strong> {checkout_date}</p>
                            <p><strong>Room Type:</strong> {room_type}</p>
                            <p><strong>Room Number:</strong> {room_number}</p>
                            <p><strong>Total Amount:</strong> {total_amount}</p>
                        </div>
                        
                        <p>If you have any questions or need to make changes to your reservation, please contact us.</p>
                        <p>We look forward to welcoming you!</p>
                        
                        <p>Best regards,<br>Hotel Management Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply to this message.</p>
                        <p>&copy; {current_year} Hotel Management System. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            "invoice.html": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; }
                    .container { width: 100%; max-width: 600px; margin: 0 auto; }
                    .header { background-color: #4a90e2; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    .footer { background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }
                    .invoice { background-color: #f9f9f9; padding: 15px; margin: 15px 0; }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #f2f2f2; }
                    .total-row { font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Invoice</h1>
                    </div>
                    <div class="content">
                        <p>Dear {guest_name},</p>
                        <p>Please find your invoice details below:</p>
                        
                        <div class="invoice">
                            <h3>Invoice Details:</h3>
                            <p><strong>Invoice Number:</strong> {invoice_number}</p>
                            <p><strong>Booking ID:</strong> {booking_id}</p>
                            <p><strong>Date:</strong> {invoice_date}</p>
                            
                            <h4>Items:</h4>
                            <table>
                                <tr>
                                    <th>Description</th>
                                    <th>Quantity</th>
                                    <th>Unit Price</th>
                                    <th>Amount</th>
                                </tr>
                                {invoice_items}
                                <tr class="total-row">
                                    <td colspan="3">Subtotal</td>
                                    <td>{subtotal}</td>
                                </tr>
                                {tax_rows}
                                {discount_rows}
                                <tr class="total-row">
                                    <td colspan="3">Total</td>
                                    <td>{total_amount}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <p>Thank you for choosing our hotel.</p>
                        <p>Best regards,<br>Hotel Management Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply to this message.</p>
                        <p>&copy; {current_year} Hotel Management System. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            "password_reset.html": """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; }
                    .container { width: 100%; max-width: 600px; margin: 0 auto; }
                    .header { background-color: #4a90e2; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; }
                    .footer { background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }
                    .reset-button { display: inline-block; background-color: #4a90e2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
                    .code-box { background-color: #f9f9f9; padding: 15px; margin: 15px 0; text-align: center; font-size: 24px; letter-spacing: 5px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset</h1>
                    </div>
                    <div class="content">
                        <p>Dear {user_name},</p>
                        <p>We received a request to reset your password. If you didn't make this request, you can ignore this email.</p>
                        
                        <p>To reset your password, click the button below:</p>
                        <p style="text-align: center;">
                            <a href="{reset_link}" class="reset-button">Reset Password</a>
                        </p>
                        
                        <p>Alternatively, you can use the following code:</p>
                        <div class="code-box">{reset_code}</div>
                        
                        <p>This code will expire in {expiry_hours} hours.</p>
                        
                        <p>Best regards,<br>Hotel Management Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply to this message.</p>
                        <p>&copy; {current_year} Hotel Management System. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        for filename, content in templates.items():
            file_path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    f.write(content)
                logger.info(f"Created default email template: {filename}")
    
    async def send_email(self, 
                        to_email: Union[str, List[str]], 
                        subject: str, 
                        body: str, 
                        cc: Optional[Union[str, List[str]]] = None,
                        bcc: Optional[Union[str, List[str]]] = None,
                        attachments: Optional[List[str]] = None,
                        is_html: bool = True) -> bool:
        """Send an email"""
        # Convert single email to list
        if isinstance(to_email, str):
            to_email = [to_email]
        
        # Convert cc and bcc to lists if they are strings
        if cc and isinstance(cc, str):
            cc = [cc]
        if bcc and isinstance(bcc, str):
            bcc = [bcc]
        
        # Create message
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = ", ".join(to_email)
        message["Subject"] = subject
        
        if cc:
            message["Cc"] = ", ".join(cc)
        
        if bcc:
            message["Bcc"] = ", ".join(bcc)
        
        # Attach body
        if is_html:
            message.attach(MIMEText(body, "html"))
        else:
            message.attach(MIMEText(body, "plain"))
        
        # Attach files
        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as file:
                        part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                    
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                    message.attach(part)
                else:
                    logger.warning(f"Attachment not found: {attachment_path}")
        
        try:
            # Create secure connection and send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                # Combine all recipients
                all_recipients = to_email
                if cc:
                    all_recipients.extend(cc)
                if bcc:
                    all_recipients.extend(bcc)
                
                server.sendmail(self.sender_email, all_recipients, message.as_string())
            
            logger.info(f"Email sent successfully to {', '.join(to_email)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    async def send_template_email(self, 
                                 template_name: str, 
                                 to_email: Union[str, List[str]], 
                                 subject: str, 
                                 template_data: Dict[str, Any],
                                 cc: Optional[Union[str, List[str]]] = None,
                                 bcc: Optional[Union[str, List[str]]] = None,
                                 attachments: Optional[List[str]] = None) -> bool:
        """Send an email using a template"""
        template_path = os.path.join(self.templates_dir, template_name)
        
        if not os.path.exists(template_path):
            logger.error(f"Email template not found: {template_name}")
            return False
        
        try:
            # Read template
            with open(template_path, "r") as f:
                template_content = f.read()
            
            # Add current year to template data
            if "current_year" not in template_data:
                template_data["current_year"] = str(datetime.now().year)
            
            # Replace placeholders
            for key, value in template_data.items():
                placeholder = "{" + key + "}"
                template_content = template_content.replace(placeholder, str(value))
            
            # Send email
            return await self.send_email(
                to_email=to_email,
                subject=subject,
                body=template_content,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                is_html=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send template email: {str(e)}")
            return False
    
    async def send_booking_confirmation(self, booking_data: Dict[str, Any], guest_email: str) -> bool:
        """Send booking confirmation email"""
        return await self.send_template_email(
            template_name="booking_confirmation.html",
            to_email=guest_email,
            subject="Booking Confirmation",
            template_data=booking_data
        )
    
    async def send_invoice(self, invoice_data: Dict[str, Any], guest_email: str, invoice_pdf_path: Optional[str] = None) -> bool:
        """Send invoice email"""
        attachments = [invoice_pdf_path] if invoice_pdf_path and os.path.exists(invoice_pdf_path) else None
        
        return await self.send_template_email(
            template_name="invoice.html",
            to_email=guest_email,
            subject=f"Invoice #{invoice_data.get('invoice_number', '')}",
            template_data=invoice_data,
            attachments=attachments
        )
    
    async def send_password_reset(self, user_email: str, user_name: str, reset_link: str, reset_code: str, expiry_hours: int = 24) -> bool:
        """Send password reset email"""
        template_data = {
            "user_name": user_name,
            "reset_link": reset_link,
            "reset_code": reset_code,
            "expiry_hours": expiry_hours
        }
        
        return await self.send_template_email(
            template_name="password_reset.html",
            to_email=user_email,
            subject="Password Reset Request",
            template_data=template_data
        )
    
    async def send_system_alert(self, subject: str, message: str, admin_emails: List[str]) -> bool:
        """Send system alert to administrators"""
        alert_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ width: 100%; max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .alert {{ background-color: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #e74c3c; }}
                .footer {{ background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>System Alert</h1>
                </div>
                <div class="content">
                    <div class="alert">
                        <h3>{subject}</h3>
                        <p>{message}</p>
                        <p><strong>Time:</strong> {get_current_time().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    <p>Please take appropriate action.</p>
                </div>
                <div class="footer">
                    <p>This is an automated alert from the Hotel Management System.</p>
                    <p>&copy; {datetime.now().year} Hotel Management System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=admin_emails,
            subject=f"ALERT: {subject}",
            body=alert_html,
            is_html=True
        )