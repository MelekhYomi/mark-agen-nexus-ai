"""
Email Service - SendGrid Integration
Handles all email notifications including transactional emails,
marketing campaigns, and automated notifications.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
import base64

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    SendGrid email service for transactional and marketing emails.
    Supports templates, attachments, and batch sending.
    """
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME
        self.client = SendGridAPIClient(self.api_key)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Send a single email with optional attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text fallback
            from_name: Custom sender name
            reply_to: Reply-to email address
            attachments: List of attachment dicts with 'content', 'filename', 'type'
        
        Returns:
            Dict with status_code, body, and headers
        """
        try:
            from_email_obj = Email(
                email=self.from_email,
                name=from_name or self.from_name
            )
            to_email_obj = To(email=to_email)
            
            content = Content("text/html", html_content)
            
            mail = Mail(from_email_obj, to_email_obj, subject, content)
            
            if text_content:
                mail.add_content(Content("text/plain", text_content))
            
            if reply_to:
                mail.reply_to = Email(email=reply_to)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    file_content = FileContent(attachment['content'])
                    file_name = FileName(attachment['filename'])
                    file_type = FileType(attachment.get('type', 'application/octet-stream'))
                    disposition = Disposition('attachment')
                    
                    attachment_obj = Attachment(
                        file_content, file_name, file_type, disposition
                    )
                    mail.attachment = attachment_obj
            
            # Send email
            response = self.client.send(mail)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            
            return {
                "status_code": response.status_code,
                "body": response.body,
                "headers": response.headers,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {
                "status_code": 500,
                "error": str(e),
                "success": False
            }
    
    async def send_template_email(
        self,
        to_email: str,
        template_id: str,
        dynamic_template_data: Dict,
        from_name: Optional[str] = None
    ) -> Dict:
        """
        Send email using SendGrid dynamic template.
        
        Args:
            to_email: Recipient email
            template_id: SendGrid template ID
            dynamic_template_data: Template variables
            from_name: Custom sender name
        
        Returns:
            Dict with response data
        """
        try:
            from_email_obj = Email(
                email=self.from_email,
                name=from_name or self.from_name
            )
            to_email_obj = To(email=to_email)
            
            mail = Mail(from_email_obj, to_email_obj)
            mail.template_id = template_id
            mail.dynamic_template_data = dynamic_template_data
            
            response = self.client.send(mail)
            
            logger.info(f"Template email sent to {to_email}: {template_id}")
            
            return {
                "status_code": response.status_code,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to send template email to {to_email}: {str(e)}")
            return {
                "status_code": 500,
                "error": str(e),
                "success": False
            }
    
    async def send_batch_emails(
        self,
        recipients: List[Dict],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict:
        """
        Send batch emails to multiple recipients.
        
        Args:
            recipients: List of dicts with 'email' and optional 'name'
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content
        
        Returns:
            Dict with success count and errors
        """
        success_count = 0
        errors = []
        
        for recipient in recipients:
            result = await self.send_email(
                to_email=recipient['email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_name=recipient.get('name')
            )
            
            if result['success']:
                success_count += 1
            else:
                errors.append({
                    'email': recipient['email'],
                    'error': result['error']
                })
        
        return {
            'total': len(recipients),
            'success': success_count,
            'errors': errors,
            'success_rate': (success_count / len(recipients)) * 100 if recipients else 0
        }
    
    # ========================================================================
    # NOTIFICATION EMAILS
    # ========================================================================
    
    async def send_welcome_email(self, to_email: str, user_name: str) -> Dict:
        """Send welcome email to new users"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #7c5cff;">Welcome to Nexus AI, {user_name}! 🎉</h1>
            <p>We're excited to have you on board. Your 5 AI agents are ready to help you grow your brand.</p>
            
            <h2>What's Next?</h2>
            <ul>
                <li>Connect your social media accounts</li>
                <li>Set up your first campaign</li>
                <li>Watch your AI agents work their magic</li>
            </ul>
            
            <p style="margin-top: 30px;">
                <a href="{settings.FRONTEND_URL}/dashboard" 
                   style="background: #7c5cff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Go to Dashboard
                </a>
            </p>
            
            <p style="margin-top: 30px; color: #666; font-size: 12px;">
                Need help? Reply to this email or visit our help center.
            </p>
        </div>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Welcome to Nexus AI! 🚀",
            html_content=html_content
        )
    
    async def send_approval_notification(
        self,
        to_email: str,
        user_name: str,
        approval_title: str,
        approval_type: str,
        workspace_name: str
    ) -> Dict:
        """Send notification when approval is needed"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #7c5cff;">Action Required: Approval Needed</h1>
            <p>Hi {user_name},</p>
            <p>Your AI agent has created a new {approval_type} that requires your approval:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">{approval_title}</h3>
                <p style="margin-bottom: 0;">Workspace: {workspace_name}</p>
            </div>
            
            <p>Please review and approve or reject this action in your dashboard.</p>
            
            <p style="margin-top: 30px;">
                <a href="{settings.FRONTEND_URL}/approvals" 
                   style="background: #7c5cff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Review Approvals
                </a>
            </p>
        </div>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Action Required: {approval_title}",
            html_content=html_content
        )
    
    async def send_campaign_report(
        self,
        to_email: str,
        user_name: str,
        campaign_name: str,
        metrics: Dict
    ) -> Dict:
        """Send campaign performance report"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #7c5cff;">Campaign Report: {campaign_name}</h1>
            <p>Hi {user_name},</p>
            <p>Here's how your campaign performed:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px;"><strong>Impressions:</strong></td>
                        <td style="padding: 8px;">{metrics.get('impressions', 0):,}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px;"><strong>Clicks:</strong></td>
                        <td style="padding: 8px;">{metrics.get('clicks', 0):,}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px;"><strong>CTR:</strong></td>
                        <td style="padding: 8px;">{metrics.get('ctr', 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px;"><strong>Conversions:</strong></td>
                        <td style="padding: 8px;">{metrics.get('conversions', 0):,}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px;"><strong>ROAS:</strong></td>
                        <td style="padding: 8px;">{metrics.get('roas', 0):.2f}x</td>
                    </tr>
                </table>
            </div>
            
            <p>Keep up the great work!</p>
        </div>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Campaign Report: {campaign_name}",
            html_content=html_content
        )
    
    async def send_payment_confirmation(
        self,
        to_email: str,
        user_name: str,
        amount: float,
        currency: str,
        invoice_id: str
    ) -> Dict:
        """Send payment confirmation email"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #10b981;">Payment Confirmed ✓</h1>
            <p>Hi {user_name},</p>
            <p>Your payment has been successfully processed:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 8px;"><strong>Amount:</strong></td>
                        <td style="padding: 8px;">{currency} {amount:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px;"><strong>Invoice ID:</strong></td>
                        <td style="padding: 8px;">{invoice_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px;"><strong>Date:</strong></td>
                        <td style="padding: 8px;">{datetime.utcnow().strftime('%B %d, %Y')}</td>
                    </tr>
                </table>
            </div>
            
            <p>Thank you for your subscription!</p>
        </div>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Payment Confirmation - Invoice {invoice_id}",
            html_content=html_content
        )
    
    async def send_password_reset(
        self,
        to_email: str,
        user_name: str,
        reset_token: str
    ) -> Dict:
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #7c5cff;">Password Reset Request</h1>
            <p>Hi {user_name},</p>
            <p>We received a request to reset your password. Click the button below to reset it:</p>
            
            <p style="margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background: #7c5cff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            
            <p style="color: #666; font-size: 12px;">
                This link will expire in 1 hour. If you didn't request this, please ignore this email.
            </p>
        </div>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Password Reset Request",
            html_content=html_content
        )
    
    async def send_weekly_digest(
        self,
        to_email: str,
        user_name: str,
        metrics: Dict
    ) -> Dict:
        """Send weekly performance digest"""
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #7c5cff;">Your Weekly Growth Report 📊</h1>
            <p>Hi {user_name},</p>
            <p>Here's how your brand grew this week:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Key Metrics</h3>
                <ul>
                    <li><strong>New Followers:</strong> +{metrics.get('new_followers', 0)}</li>
                    <li><strong>Total Reach:</strong> {metrics.get('reach', 0):,}</li>
                    <li><strong>Engagements:</strong> {metrics.get('engagements', 0):,}</li>
                    <li><strong>Ad ROAS:</strong> {metrics.get('roas', 0):.2f}x</li>
                    <li><strong>Website Traffic:</strong> +{metrics.get('traffic_growth', 0)}%</li>
                </ul>
            </div>
            
            <p>Keep growing! Your AI agents are working hard for you.</p>
        </div>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Your Weekly Growth Report 📊",
            html_content=html_content
        )


# Singleton instance
email_service = EmailService()