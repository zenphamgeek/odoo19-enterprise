# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

{
    'name': 'Insilos Pub/Sub Event Bridge',
    'version': '20.0.2.3.0',
    'category': 'Productivity/Integrations',
    'summary': 'Google Cloud Pub/Sub & Hermes AI Bi-Directional Event Bus Gateway',
    'description': """
Insilos Pub/Sub Event Bridge — EDA Control Center
===================================================
Enterprise Event-Driven Architecture (EDA) Gateway connecting Google Cloud Pub/Sub
and Hermes AI Agent to Insilos Enterprise Workflows:

**Inbound Pipeline:**
- Real-time Gmail push notification callback receiver (/api/v1/pubsub/ingest).
- Automated AI-parsed entity dispatch into CRM Leads, Purchase Orders, HSE SDS, and Logistics IDP.
- Idempotency control & message deduplication with unique event_id constraint.
- Dead Letter Queue (DLQ) retry with exponential backoff up to 3 retries.

**Outbound Pipeline:**
- ERP model event publishing to external systems via outbound rules.
- Configurable webhook targets with retry and delivery tracking.

**Automation & Routing:**
- Regex-based sender filter and keyword matching for precision rule targeting.
- Call forwarding, Telegram alerts, email notifications, and multi-action combos.

**Observability:**
- Event log analytics with graph and pivot views.
- Channel health monitoring with automated stale-heartbeat detection.
- Full audit trail with X-Request-ID traceability.
    """,
    'author': 'Insilos Team',
    'website': 'https://insilos.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'crm',
        'purchase',
        'stock',
        'project',
        'account',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/pubsub_sequence.xml',
        'data/pubsub_cron.xml',
        'views/is_pubsub_channel_views.xml',
        'views/is_pubsub_event_log_views.xml',
        'views/is_pubsub_automation_rule_views.xml',
        'views/is_pubsub_forward_log_views.xml',
        'views/is_pubsub_outbound_event_views.xml',
        'views/is_pubsub_outbound_rule_views.xml',
        'views/is_pubsub_dashboard_views.xml',
        'views/menu_views.xml',
        'views/is_pubsub_onboarding_views.xml',
    ],
    'demo': [
        'data/pubsub_demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
