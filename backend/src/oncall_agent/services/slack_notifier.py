"""Slack notification service for posting incident analyses as thread replies."""

import httpx

from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)


class SlackNotifier:
    """Service for posting incident analysis to Slack as thread replies under PagerDuty messages."""

    def __init__(self):
        # Load config fresh each time to pick up env var changes
        config = get_config()
        self.webhook_url = config.slack_webhook_url
        self.bot_token = config.slack_bot_token
        self.channel = config.slack_channel
        self.channel_id = config.slack_channel_id
        self.enabled = config.slack_enabled or bool(self.webhook_url) or bool(self.bot_token)
        logger.info(f"SlackNotifier initialized - enabled: {self.enabled}, bot_token: {'set' if self.bot_token else 'not set'}, channel_id: {self.channel_id}")

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
                        "limit": 50
                    },
                    headers={
                        "Authorization": f"Bearer {self.bot_token}"
                    },
                    timeout=10.0
                )

                data = response.json()
                if not data.get("ok"):
                    logger.error(f"Slack API error searching history: {data.get('error')}")
                    return None

                messages = data.get("messages", [])
                logger.info(f"Found {len(messages)} messages in channel to search")

                # Extract key words from incident title for matching
                title_lower = incident_title.lower()
                # Get significant words (longer than 3 chars, not common words)
                skip_words = {"test", "this", "that", "with", "from", "have", "been"}
                title_words = [w for w in title_lower.split() if len(w) > 3 and w not in skip_words]
                logger.info(f"Searching for title words: {title_words[:5]}")

                for msg in messages:
                    # Get all text content from the message
                    msg_text = msg.get("text", "").lower()

                    # Check attachments (PagerDuty uses these)
                    for att in msg.get("attachments", []):
                        msg_text += " " + att.get("text", "").lower()
                        msg_text += " " + att.get("fallback", "").lower()
                        msg_text += " " + att.get("pretext", "").lower()

                    # Check blocks
                    for block in msg.get("blocks", []):
                        if block.get("type") == "section":
                            text_obj = block.get("text", {})
                            msg_text += " " + text_obj.get("text", "").lower()

                    # Check if this looks like a PagerDuty message
                    is_pagerduty = (
                        "pagerduty" in msg_text or
                        msg.get("username", "").lower() == "pagerduty" or
                        "pagerduty" in msg.get("bot_profile", {}).get("name", "").lower() or
                        "incident" in msg_text and ("triggered" in msg_text or "resolved" in msg_text)
                    )

                    # Count matching words
                    matching_words = sum(1 for word in title_words if word in msg_text)

                    # Log for debugging
                    if matching_words > 0:
                        logger.info(f"Message has {matching_words}/{len(title_words)} matching words, is_pagerduty={is_pagerduty}")

                    # Match if it's from PagerDuty OR has enough keyword matches
                    if is_pagerduty and matching_words >= 2:
                        logger.info(f"Found PagerDuty message for incident! ts={msg.get('ts')}")
                        return msg.get("ts")

                    # Also match if message contains the exact incident title pattern
                    if "test by sky" in msg_text and matching_words >= 1:
                        logger.info(f"Found TEST message matching incident! ts={msg.get('ts')}")
                        return msg.get("ts")

                logger.info(f"No matching PagerDuty message found for: {incident_title[:50]}...")
                return None

        except Exception as e:
            logger.error(f"Error searching for PagerDuty message: {e}")
            return None

    def _extract_concise_analysis(self, analysis: str) -> dict:
        """Extract cause, evidence, and fixes from verbose AI analysis."""
        import re

        result = {
            "cause": "",
            "evidence": "",
            "fixes": []
        }

        # Try to extract root cause
        cause_patterns = [
            r"root cause[:\s]+([^\n]+)",
            r"cause[:\s]+([^\n]+)",
            r"oom[_-]?kill",
            r"crashloop",
            r"memory leak",
            r"cpu throttl",
        ]

        analysis_lower = analysis.lower()

        # Detect cause type
        if "oom" in analysis_lower or "out-of-memory" in analysis_lower or "out of memory" in analysis_lower:
            result["cause"] = "Out of Memory (OOM) - Pod exceeded memory limits"
        elif "crashloop" in analysis_lower:
            result["cause"] = "CrashLoopBackOff - Pod repeatedly crashing"
        elif "imagepull" in analysis_lower:
            result["cause"] = "ImagePullBackOff - Cannot pull container image"
        elif "cpu" in analysis_lower and "throttl" in analysis_lower:
            result["cause"] = "CPU Throttling - Pod hitting CPU limits"
        else:
            # Try to find a cause statement
            for line in analysis.split('\n'):
                if 'cause' in line.lower() and len(line) < 200:
                    result["cause"] = line.strip().lstrip('-*').strip()
                    break

        if not result["cause"]:
            result["cause"] = "Issue detected - see full analysis"

        # Extract kubectl commands as fixes
        kubectl_pattern = r'kubectl\s+[^\n`]+(?=[\n`]|$)'
        commands = re.findall(kubectl_pattern, analysis)

        # Clean up and dedupe commands
        seen = set()
        for cmd in commands[:3]:  # Max 3 commands
            cmd = cmd.strip().rstrip('`').strip()
            if cmd and cmd not in seen and len(cmd) < 150:
                seen.add(cmd)
                result["fixes"].append(cmd)

        # If no kubectl commands, try to find action items
        if not result["fixes"]:
            action_patterns = [
                r"increase.*memory",
                r"scale.*deployment",
                r"restart.*pod",
                r"check.*logs",
            ]
            for pattern in action_patterns:
                if re.search(pattern, analysis_lower):
                    result["fixes"].append(pattern.replace(".*", " ").title())

        return result

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

        # Log current config for debugging
        logger.info(f"Slack config - bot_token: {'set' if self.bot_token else 'not set'}, channel_id: {self.channel_id}")

        # Try to find the PagerDuty message to reply to
        if not thread_ts and auto_find_thread:
            thread_ts = await self.find_pagerduty_message(title)
            if thread_ts:
                logger.info(f"Will reply to PagerDuty thread: {thread_ts}")

        # Map severity to emoji
        severity_emoji = {
            "critical": ":red_circle:",
            "high": ":large_orange_circle:",
            "medium": ":large_yellow_circle:",
            "low": ":large_blue_circle:",
        }.get(severity.lower(), ":white_circle:")

        # Extract concise info from verbose analysis
        extracted = self._extract_concise_analysis(analysis)

        # Build concise message
        fixes_text = ""
        if extracted["fixes"]:
            fixes_text = "\n".join([f"• `{fix}`" for fix in extracted["fixes"]])
        else:
            fixes_text = "• Check full analysis in dashboard"

        # Concise format for Slack
        report_url = f"https://oncall.frai.pro/incidents/{incident_id}"
        message_text = f""":robot_face: *AI Analysis*

*Cause:* {extracted["cause"]}

*Recommended Fixes:*
{fixes_text}

<{report_url}|View Full Report>"""

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message_text
                }
            }
        ]

        payload = {"blocks": blocks}

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


def get_slack_notifier() -> SlackNotifier:
    """Get a fresh Slack notifier instance with latest config."""
    return SlackNotifier()
