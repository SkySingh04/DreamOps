"""Slack notification service for posting incident analyses as thread replies."""

import httpx

from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
config = get_config()


class SlackNotifier:
    """Service for posting incident analysis to Slack as thread replies under PagerDuty messages."""

    def __init__(self):
        self.webhook_url = config.slack_webhook_url
        self.bot_token = config.slack_bot_token
        self.channel = config.slack_channel
        self.channel_id = config.slack_channel_id
        self.enabled = config.slack_enabled or bool(self.webhook_url) or bool(self.bot_token)

    async def find_pagerduty_message(self, incident_title: str, lookback_minutes: int = 60) -> str | None:
        """
        Find the PagerDuty message in the channel that matches the incident.

        Args:
            incident_title: The incident title to search for
            lookback_minutes: How far back to search (default 60 minutes)

        Returns:
            The thread_ts of the PagerDuty message, or None if not found
        """
        if not self.bot_token or not self.channel_id:
            logger.warning("Bot token or channel ID not configured - cannot search for PagerDuty message")
            return None

        try:
            import time
            oldest = str(int(time.time()) - (lookback_minutes * 60))

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://slack.com/api/conversations.history",
                    params={
                        "channel": self.channel_id,
                        "oldest": oldest,
                        "limit": 100
                    },
                    headers={
                        "Authorization": f"Bearer {self.bot_token}"
                    },
                    timeout=10.0
                )

                data = response.json()
                if not data.get("ok"):
                    logger.error(f"Slack API error: {data.get('error')}")
                    return None

                messages = data.get("messages", [])

                # Search for PagerDuty message matching our incident
                # PagerDuty messages typically come from "PagerDuty" bot and contain the incident title
                for msg in messages:
                    # Check if it's from PagerDuty (bot_id or username)
                    is_pagerduty = (
                        msg.get("username") == "PagerDuty" or
                        msg.get("bot_profile", {}).get("name") == "PagerDuty" or
                        "pagerduty" in msg.get("username", "").lower()
                    )

                    # Check message text or attachments for incident title
                    msg_text = msg.get("text", "").lower()

                    # Also check attachments (PagerDuty often uses these)
                    attachments_text = ""
                    for att in msg.get("attachments", []):
                        attachments_text += att.get("text", "").lower() + " "
                        attachments_text += att.get("fallback", "").lower() + " "
                        attachments_text += att.get("title", "").lower() + " "

                    # Also check blocks
                    blocks_text = ""
                    for block in msg.get("blocks", []):
                        if block.get("type") == "section":
                            text_obj = block.get("text", {})
                            blocks_text += text_obj.get("text", "").lower() + " "

                    combined_text = msg_text + attachments_text + blocks_text

                    # Extract key words from incident title for matching
                    title_lower = incident_title.lower()
                    title_words = [w for w in title_lower.split() if len(w) > 3]

                    # Check if enough title words match (at least 50% or 2 words)
                    matching_words = sum(1 for word in title_words if word in combined_text)
                    min_matches = max(2, len(title_words) // 2)

                    if is_pagerduty and matching_words >= min_matches:
                        logger.info(f"Found PagerDuty message for incident: {incident_title[:50]}...")
                        return msg.get("ts")

                    # Also match if it's from PagerDuty and contains specific identifiers
                    if is_pagerduty:
                        # Check for common patterns like pod names, namespaces, etc.
                        if any(keyword in combined_text for keyword in ["oomkilled", "crashloop", "pod", "deployment"]):
                            if any(word in combined_text for word in title_words[:3]):
                                logger.info(f"Found PagerDuty message (pattern match) for: {incident_title[:50]}...")
                                return msg.get("ts")

                logger.info(f"No matching PagerDuty message found for: {incident_title[:50]}...")
                return None

        except Exception as e:
            logger.error(f"Error searching for PagerDuty message: {e}")
            return None

    async def post_incident_analysis(
        self,
        incident_id: str,
        title: str,
        severity: str,
        analysis: str,
        thread_ts: str | None = None,
        auto_find_thread: bool = True
    ) -> dict:
        """
        Post incident analysis to Slack, preferably as a thread reply under the PagerDuty message.

        Args:
            incident_id: Unique incident identifier
            title: Incident title
            severity: Incident severity (critical, high, medium, low)
            analysis: AI-generated analysis (markdown format)
            thread_ts: Optional thread timestamp to reply to
            auto_find_thread: If True and thread_ts not provided, search for PagerDuty message

        Returns:
            Response dict with success status and thread_ts for follow-up messages
        """
        if not self.enabled:
            logger.warning("Slack notifications disabled - no credentials configured")
            return {"success": False, "error": "Slack not configured"}

        # Try to find the PagerDuty message to reply to
        if not thread_ts and auto_find_thread:
            thread_ts = await self.find_pagerduty_message(title)
            if thread_ts:
                logger.info(f"Will reply to PagerDuty thread: {thread_ts}")

        # Map severity to emoji and color
        severity_map = {
            "critical": {"emoji": ":red_circle:", "color": "#FF0000"},
            "high": {"emoji": ":large_orange_circle:", "color": "#FF8C00"},
            "medium": {"emoji": ":large_yellow_circle:", "color": "#FFD700"},
            "low": {"emoji": ":large_blue_circle:", "color": "#0000FF"},
            "info": {"emoji": ":white_circle:", "color": "#808080"},
        }

        sev_info = severity_map.get(severity.lower(), severity_map["info"])

        # Truncate analysis if too long for Slack (max ~3000 chars per block)
        max_analysis_length = 2900
        if len(analysis) > max_analysis_length:
            analysis = analysis[:max_analysis_length] + "\n\n... [truncated - view full report in dashboard]"

        # Build Slack message payload - simplified for thread replies
        if thread_ts:
            # Simpler format for thread replies
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":robot_face: *AI Analysis Complete*\n\n{analysis}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Severity: {sev_info['emoji']} {severity.upper()} | ID: `{incident_id}`"
                        }
                    ]
                }
            ]
        else:
            # Full format for standalone messages
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{sev_info['emoji']} AI Analysis: {title[:100]}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n`{incident_id}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{severity.upper()}"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*AI Analysis:*\n{analysis}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": ":robot_face: Generated by DreamOps AI Agent"
                        }
                    ]
                }
            ]

        payload = {
            "blocks": blocks,
            "attachments": [
                {
                    "color": sev_info["color"],
                    "fallback": f"AI Analysis: {title}"
                }
            ]
        }

        # Add thread_ts for threading
        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient() as client:
                if self.bot_token and self.channel_id:
                    # Use bot token (preferred - supports threading properly)
                    payload["channel"] = self.channel_id
                    response = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.bot_token}"
                        },
                        timeout=10.0
                    )

                    data = response.json()
                    if data.get("ok"):
                        reply_type = "thread reply" if thread_ts else "new message"
                        logger.info(f"Posted AI analysis to Slack as {reply_type} for {incident_id}")
                        return {
                            "success": True,
                            "thread_ts": data.get("ts"),
                            "channel": data.get("channel"),
                            "is_thread_reply": bool(thread_ts)
                        }
                    else:
                        logger.error(f"Slack API error: {data.get('error')}")
                        return {"success": False, "error": data.get("error")}

                elif self.webhook_url:
                    # Fallback to webhook (limited threading support)
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        logger.info(f"Posted AI analysis to Slack via webhook for {incident_id}")
                        return {"success": True, "message": "Posted to Slack via webhook"}
                    else:
                        logger.error(f"Slack webhook error: {response.status_code} - {response.text}")
                        return {"success": False, "error": f"Slack error: {response.status_code}"}

        except httpx.TimeoutException:
            logger.error("Timeout posting to Slack")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Error posting to Slack: {e}")
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "No Slack credentials configured"}

    async def post_resolution_update(
        self,
        incident_id: str,
        title: str,
        resolution: str,
        thread_ts: str | None = None,
        auto_find_thread: bool = True
    ) -> dict:
        """Post a resolution update to an existing Slack thread."""
        if not self.enabled:
            return {"success": False, "error": "Slack not configured"}

        # Try to find the PagerDuty message to reply to
        if not thread_ts and auto_find_thread:
            thread_ts = await self.find_pagerduty_message(title)

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":white_check_mark: *Resolution Update*\n\n{resolution[:2000]}"
                }
            }
        ]

        payload = {"blocks": blocks}

        if thread_ts:
            payload["thread_ts"] = thread_ts

        try:
            async with httpx.AsyncClient() as client:
                if self.bot_token and self.channel_id:
                    payload["channel"] = self.channel_id
                    response = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.bot_token}"
                        },
                        timeout=10.0
                    )
                    data = response.json()
                    return {"success": data.get("ok", False)}

                elif self.webhook_url:
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10.0
                    )
                    return {"success": response.status_code == 200}

        except Exception as e:
            logger.error(f"Error posting resolution to Slack: {e}")
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "No Slack credentials configured"}


# Singleton instance
_slack_notifier: SlackNotifier | None = None


def get_slack_notifier() -> SlackNotifier:
    """Get the Slack notifier singleton."""
    global _slack_notifier
    if _slack_notifier is None:
        _slack_notifier = SlackNotifier()
    return _slack_notifier
