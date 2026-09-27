# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing terms.

import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class PubSubScheduledAction(models.Model):
    _name = 'is.pubsub.scheduled.action'
    _description = 'Pub/Sub Cron Helpers & Dead Letter Queue Manager'

    # ── Dead Letter Queue: retry failed events ──────────────────────────
    @api.model
    def _cron_retry_dead_letters(self):
        """Re-process events that failed, up to max_retries=3 with exponential backoff."""
        EventLog = self.env['is.pubsub.event.log']
        failed_events = EventLog.search([
            ('state', '=', 'failed'),
            ('retry_count', '<', 3),
        ], limit=50, order='create_date asc')

        if not failed_events:
            _logger.info("⚡ [DLQ Cron] No dead-letter events to retry.")
            return

        _logger.info("⚡ [DLQ Cron] Found %d dead-letter events for retry.", len(failed_events))

        for event in failed_events:
            try:
                event.with_context(requeue_reason='Automatic DLQ retry').action_requeue_event()
            except Exception as exc:
                event.sudo().write({
                    'error_message': _("DLQ Retry #%d failed: %s") % (event.retry_count, exc),
                })
                _logger.error("DLQ Retry failed for event %s: %s", event.event_id, exc)

    # ── Channel Health Check ────────────────────────────────────────────
    @api.model
    def _cron_channel_health_check(self):
        """Detect stale channels (no heartbeat > 2h) and set state=error."""
        Channel = self.env['is.pubsub.channel']
        cutoff = fields.Datetime.now() - timedelta(hours=2)
        stale_channels = Channel.search([
            ('state', '=', 'active'),
            ('last_heartbeat', '<', cutoff),
        ])

        for ch in stale_channels:
            ch.sudo().write({
                'state': 'error',
                'last_status_message': _(
                    "Health degraded: no heartbeat since %s (>2h threshold)."
                ) % fields.Datetime.to_string(ch.last_heartbeat),
            })
            _logger.warning("⚠️ [Health] Channel '%s' marked degraded — stale heartbeat.", ch.name)

        # Send Telegram alert for degraded channels
        if stale_channels:
            self._send_health_telegram_alert(stale_channels)

        _logger.info("⚡ [Health Cron] Checked %d active channels, %d degraded.",
                      Channel.search_count([('state', '=', 'active')]) + len(stale_channels),
                      len(stale_channels))

    def _send_health_telegram_alert(self, channels):
        """Send Telegram alert when channels go stale."""
        token = self.env['ir.config_parameter'].sudo().get_param('insilos_pubsub.telegram_bot_token')
        chat_id = self.env['ir.config_parameter'].sudo().get_param('insilos_pubsub.telegram_health_chat_id', '1431349185')
        if not token:
            return

        import requests
        names = ', '.join(channels.mapped('name'))
        msg = (
            f"⚠️ <b>[PUBSUB HEALTH ALERT]</b>\n"
            f"<b>Degraded Channels:</b> {names}\n"
            f"<b>Reason:</b> No heartbeat for >2 hours.\n"
            f"<b>Action:</b> Check GCP subscription or network connectivity."
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'},
                timeout=5,
            )
        except Exception as exc:
            _logger.warning("Health Telegram alert failed: %s", exc)

    # ── Stats Aggregation ───────────────────────────────────────────────
    @api.model
    def _cron_stats_aggregate(self):
        """Compute hourly event throughput and update channel stats cache."""
        Channel = self.env['is.pubsub.channel']
        EventLog = self.env['is.pubsub.event.log']
        one_hour_ago = fields.Datetime.now() - timedelta(hours=1)

        total_recent = EventLog.search_count([('create_date', '>=', one_hour_ago)])
        failed_recent = EventLog.search_count([
            ('create_date', '>=', one_hour_ago),
            ('state', '=', 'failed'),
        ])
        _logger.info(
            "⚡ [Stats Cron] Last 1h: %d events ingested, %d failed.",
            total_recent, failed_recent,
        )

        # Refresh heartbeat on active channels that received events
        for ch in Channel.search([('state', '=', 'active')]):
            latest_event = EventLog.search([
                ('create_date', '>=', one_hour_ago),
            ], limit=1, order='create_date desc')
            if latest_event:
                ch.sudo().write({
                    'last_heartbeat': fields.Datetime.now(),
                    'last_status_message': _(
                        "Stats refresh: %d events in last hour (%d failed)."
                    ) % (total_recent, failed_recent),
                })
