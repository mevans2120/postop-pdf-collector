"""Alert management and notification system."""

import smtplib
import json
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import requests


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class Alert:
    """Alert data structure."""
    name: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    tags: Dict[str, Any]
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            "name": self.name,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "details": self.details or {}
        }


class AlertRule:
    """Base class for alert rules."""
    
    def __init__(self, name: str, severity: AlertSeverity):
        """Initialize alert rule.
        
        Args:
            name: Rule name
            severity: Alert severity
        """
        self.name = name
        self.severity = severity
    
    def check(self, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Check if alert should be triggered.
        
        Args:
            metrics: Current metrics
            
        Returns:
            Alert if triggered, None otherwise
        """
        raise NotImplementedError


class ThresholdAlertRule(AlertRule):
    """Alert rule based on metric threshold."""
    
    def __init__(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        operator: str = ">",
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """Initialize threshold rule.
        
        Args:
            name: Rule name
            metric_name: Metric to check
            threshold: Threshold value
            operator: Comparison operator (>, <, >=, <=, ==, !=)
            severity: Alert severity
        """
        super().__init__(name, severity)
        self.metric_name = metric_name
        self.threshold = threshold
        self.operator = operator
    
    def check(self, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Check if metric exceeds threshold."""
        value = self._get_metric_value(metrics, self.metric_name)
        if value is None:
            return None
        
        triggered = False
        if self.operator == ">":
            triggered = value > self.threshold
        elif self.operator == "<":
            triggered = value < self.threshold
        elif self.operator == ">=":
            triggered = value >= self.threshold
        elif self.operator == "<=":
            triggered = value <= self.threshold
        elif self.operator == "==":
            triggered = value == self.threshold
        elif self.operator == "!=":
            triggered = value != self.threshold
        
        if triggered:
            return Alert(
                name=self.name,
                message=f"{self.metric_name} is {value} (threshold: {self.operator} {self.threshold})",
                severity=self.severity,
                timestamp=datetime.utcnow(),
                tags={"metric": self.metric_name},
                details={"value": value, "threshold": self.threshold}
            )
        
        return None
    
    def _get_metric_value(self, metrics: Dict, path: str) -> Optional[float]:
        """Get metric value from nested dictionary."""
        parts = path.split(".")
        current = metrics
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return float(current) if current is not None else None


class RateAlertRule(AlertRule):
    """Alert rule based on rate of change."""
    
    def __init__(
        self,
        name: str,
        metric_name: str,
        rate_threshold: float,
        window_seconds: int = 60,
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """Initialize rate rule.
        
        Args:
            name: Rule name
            metric_name: Metric to check
            rate_threshold: Rate threshold (per second)
            window_seconds: Time window for rate calculation
            severity: Alert severity
        """
        super().__init__(name, severity)
        self.metric_name = metric_name
        self.rate_threshold = rate_threshold
        self.window_seconds = window_seconds
        self.previous_value = None
        self.previous_time = None
    
    def check(self, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Check if rate exceeds threshold."""
        # Implementation would track rate over time
        # Simplified for demonstration
        return None


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize alert manager.
        
        Args:
            config: Alert configuration
        """
        self.config = config or {}
        self.rules: List[AlertRule] = []
        self.alerts: List[Alert] = []
        self.channels: Dict[AlertChannel, Any] = {}
        
        # Configure channels
        self._configure_channels()
    
    def _configure_channels(self):
        """Configure notification channels."""
        # Email configuration
        if "email" in self.config:
            self.channels[AlertChannel.EMAIL] = self.config["email"]
        
        # Slack configuration
        if "slack" in self.config:
            self.channels[AlertChannel.SLACK] = self.config["slack"]
        
        # Webhook configuration
        if "webhook" in self.config:
            self.channels[AlertChannel.WEBHOOK] = self.config["webhook"]
        
        # Always enable log channel
        self.channels[AlertChannel.LOG] = True
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule.
        
        Args:
            rule: Alert rule to add
        """
        self.rules.append(rule)
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check all rules against current metrics.
        
        Args:
            metrics: Current metrics
        """
        for rule in self.rules:
            alert = rule.check(metrics)
            if alert:
                self.trigger_alert(alert)
    
    def trigger_alert(self, alert: Alert):
        """Trigger an alert and send notifications.
        
        Args:
            alert: Alert to trigger
        """
        # Add to alerts list
        self.alerts.append(alert)
        
        # Send notifications based on severity
        if alert.severity == AlertSeverity.CRITICAL:
            channels = [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.LOG]
        elif alert.severity == AlertSeverity.ERROR:
            channels = [AlertChannel.SLACK, AlertChannel.LOG]
        elif alert.severity == AlertSeverity.WARNING:
            channels = [AlertChannel.LOG]
        else:
            channels = [AlertChannel.LOG]
        
        for channel in channels:
            if channel in self.channels:
                self._send_notification(channel, alert)
    
    def _send_notification(self, channel: AlertChannel, alert: Alert):
        """Send notification to a channel.
        
        Args:
            channel: Notification channel
            alert: Alert to send
        """
        try:
            if channel == AlertChannel.LOG:
                self._send_log_notification(alert)
            elif channel == AlertChannel.EMAIL:
                self._send_email_notification(alert)
            elif channel == AlertChannel.SLACK:
                self._send_slack_notification(alert)
            elif channel == AlertChannel.WEBHOOK:
                self._send_webhook_notification(alert)
        except Exception as e:
            logger.error(f"Failed to send {channel.value} notification: {e}")
    
    def _send_log_notification(self, alert: Alert):
        """Send alert to log."""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.INFO: logging.INFO,
        }[alert.severity]
        
        logger.log(
            log_level,
            f"ALERT: {alert.name} - {alert.message}",
            extra={"alert": alert.to_dict()}
        )
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification."""
        config = self.channels[AlertChannel.EMAIL]
        
        msg = MIMEMultipart()
        msg["From"] = config["from"]
        msg["To"] = ", ".join(config["to"])
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.name}"
        
        body = f"""
        Alert: {alert.name}
        Severity: {alert.severity.value}
        Time: {alert.timestamp}
        
        Message: {alert.message}
        
        Details:
        {json.dumps(alert.details, indent=2)}
        
        Tags:
        {json.dumps(alert.tags, indent=2)}
        """
        
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            if config.get("smtp_tls"):
                server.starttls()
            if config.get("smtp_user") and config.get("smtp_password"):
                server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)
    
    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification."""
        config = self.channels[AlertChannel.SLACK]
        
        color = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.ERROR: "danger",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "good",
        }[alert.severity]
        
        payload = {
            "attachments": [{
                "color": color,
                "title": alert.name,
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Time", "value": str(alert.timestamp), "short": True},
                ],
                "footer": "PostOp PDF Collector",
                "ts": int(alert.timestamp.timestamp())
            }]
        }
        
        response = requests.post(config["webhook_url"], json=payload)
        response.raise_for_status()
    
    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification."""
        config = self.channels[AlertChannel.WEBHOOK]
        
        response = requests.post(
            config["url"],
            json=alert.to_dict(),
            headers=config.get("headers", {})
        )
        response.raise_for_status()
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent alerts
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp > cutoff]


# Default alert rules
def create_default_rules() -> List[AlertRule]:
    """Create default alert rules."""
    return [
        # High error rate
        ThresholdAlertRule(
            name="High Error Rate",
            metric_name="errors.count",
            threshold=100,
            operator=">",
            severity=AlertSeverity.ERROR
        ),
        
        # Low collection success rate
        ThresholdAlertRule(
            name="Low Collection Success Rate",
            metric_name="collection.success_rate",
            threshold=0.5,
            operator="<",
            severity=AlertSeverity.WARNING
        ),
        
        # Database connection failures
        ThresholdAlertRule(
            name="Database Connection Failures",
            metric_name="database.connection_errors",
            threshold=5,
            operator=">",
            severity=AlertSeverity.CRITICAL
        ),
        
        # High memory usage
        ThresholdAlertRule(
            name="High Memory Usage",
            metric_name="system.memory_percent",
            threshold=90,
            operator=">",
            severity=AlertSeverity.WARNING
        ),
        
        # Slow API response
        ThresholdAlertRule(
            name="Slow API Response",
            metric_name="api.response_time_p95",
            threshold=5000,  # 5 seconds
            operator=">",
            severity=AlertSeverity.WARNING
        ),
    ]