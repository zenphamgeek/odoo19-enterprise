# -*- coding: utf-8 -*-
"""
Insilos Logistics IDP & Legal Real-Time Notification Service
Dispatches UI Toast Notifications (bus.bus), Chatter Logs (mail.message),
and Scheduled Activities (mail.activity).
"""
import logging
from odoo import fields

_logger = logging.getLogger(__name__)

def push_ui_notification(env, user_ids, title, message, notif_type='info', sticky=False, action=None):
    """
    Bắn Toast Notification thời gian thực lên giao diện người dùng qua bus.bus.
    notif_type: 'info' | 'warning' | 'danger' | 'success'
    """
    if not user_ids:
        return
    try:
        users = env['res.users'].browse(user_ids)
        partners = users.mapped('partner_id')
        payload = {
            'type': notif_type,
            'title': title,
            'message': message,
            'sticky': sticky,
        }
        if action:
            payload['action'] = action
            
        for partner in partners:
            env['bus.bus']._sendone(partner, 'simple_notification', payload)
    except Exception as exc:
        _logger.warning("Failed to dispatch bus.bus UI notification: %s", exc)

def notify_case_event(case, event_type, title, message, notif_type='info', sticky=False):
    """
    Thông báo sự kiện vòng đời Case:
    1. Push Toast lên UI của Case Owner / Logistics Managers.
    2. Ghi nhật ký vào Chatter của Case.
    """
    env = case.env
    # 1. Ghi log vào Chatter
    try:
        case.message_post(body=f"<b>[{title}]</b> {message}")
    except Exception as exc:
        _logger.warning("Failed to post message to case chatter: %s", exc)
        
    # 2. Tìm danh sách User nhận thông báo (Owner + Managers)
    target_users = set()
    if case.owner_id:
        target_users.add(case.owner_id.id)
        
    managers = env.ref('insilos_logistics_idp.group_logistics_manager', raise_if_not_found=False)
    if managers and hasattr(managers, 'users'):
        for u in managers.users:
            target_users.add(u.id)
            
    if target_users:
        push_ui_notification(env, list(target_users), title, message, notif_type=notif_type, sticky=sticky)

def notify_legal_event(env, title, message, notif_type='warning', sticky=True):
    """
    Thông báo biến động pháp lý / biểu thuế mới cho toàn bộ nhân sự phụ trách Logistics.
    """
    target_users = set()
    managers = env.ref('insilos_logistics_idp.group_logistics_manager', raise_if_not_found=False)
    if managers and hasattr(managers, 'users'):
        for u in managers.users:
            target_users.add(u.id)
    operators = env.ref('insilos_logistics_idp.group_logistics_operator', raise_if_not_found=False)
    if operators and hasattr(operators, 'users'):
        for u in operators.users:
            target_users.add(u.id)
            
    if not target_users:
        target_users.add(env.uid)
        
    push_ui_notification(env, list(target_users), title, message, notif_type=notif_type, sticky=sticky)
