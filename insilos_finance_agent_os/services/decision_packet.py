# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Decision packet — bản ghi bất biến của một quyết định (E07).

Một packet trả lời được ba câu hỏi mà hội đồng kiểm toán sẽ hỏi sau sáu
tháng: lúc đó agent *thấy* gì (inputs, mỗi cái có ref), nó *nói* gì
(recommendation), và ai *quyết* gì (context). Packet ghi thành JSON attachment
trên chính work item — zero-schema, và evidence sống cùng vòng đời record
mà governance đã bảo vệ sẵn.

Tính bất biến không đến từ một cột "đừng sửa nhé" mà từ hash: `packet_hash`
là SHA-256 của nội dung canonical. `verify` tính lại từ byte đang lưu; sửa
một ký tự trong attachment là hash lệch. `diff` so hai packet theo từng
input — để trả lời câu hỏi thứ tư: "giữa hai lần khuyến nghị, *cái gì* đã
đổi?".

Replay ở đây là **replay đối chiếu**: chạy lại builder với inputs hiện tại
và diff với packet đã lưu. Không hứa tái tạo bit-perfect quá khứ — dữ liệu
nguồn đã trôi — mà chỉ ra chính xác chỗ trôi.
"""

import hashlib
import json

from odoo.exceptions import UserError

PACKET_VERSION = 1
ATTACHMENT_PREFIX = 'decision_packet'


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _hash(payload):
    return hashlib.sha256(_canonical(payload).encode()).hexdigest()


def build(inputs, recommendation, context):
    """Dựng packet từ inputs đã có nguồn. Fact mồ côi bị từ chối cả gói.

    `inputs`: list dict, mỗi cái bắt buộc `ref` (record hay lineage
    fingerprint). `recommendation`: dict tự do của skill. `context`: ai/lúc
    nào/mode gì.
    """
    orphans = [i for i in inputs if not str(i.get('ref') or '').strip()]
    if orphans:
        raise UserError(
            'Decision packet refused: %d input(s) carry no source ref.' % len(orphans))
    body = {
        'version': PACKET_VERSION,
        'inputs': sorted(inputs, key=_canonical),
        'recommendation': recommendation,
        'context': context,
    }
    return {'packet_hash': _hash(body), **body}


def attach(env, work_item, packet):
    """Ghi packet lên work item. Tên file chứa hash — trùng nội dung thì trùng tên."""
    work_item.ensure_one()
    name = '%s_%s.json' % (ATTACHMENT_PREFIX, packet['packet_hash'][:16])
    return env['ir.attachment'].create({
        'name': name,
        'raw': json.dumps(packet, sort_keys=True, ensure_ascii=False, indent=2).encode(),
        'res_model': work_item._name,
        'res_id': work_item.id,
    })


def load(attachment):
    packet = json.loads(attachment.raw.decode())
    verify(packet)
    return packet


def verify(packet):
    """Hash tính lại phải khớp hash đã ghi — một ký tự lệch là từ chối."""
    body = {k: packet[k] for k in ('version', 'inputs', 'recommendation', 'context')}
    expected = _hash(body)
    if packet.get("packet_hash") != expected:
        raise UserError(
            'Decision packet integrity check failed: stored hash %s, recomputed %s.'
            % (packet.get('packet_hash'), expected))
    return True


def diff(old, new):
    """So hai packet theo từng input (khoá theo `ref`) và recommendation.

    Trả về dict chỉ chứa những gì đổi — rỗng nghĩa là replay tái lập nguyên
    trạng.
    """
    changes = {}
    old_inputs = {i['ref']: i for i in old['inputs']}
    new_inputs = {i['ref']: i for i in new['inputs']}
    added = sorted(set(new_inputs) - set(old_inputs))
    removed = sorted(set(old_inputs) - set(new_inputs))
    drifted = sorted(
        ref for ref in set(old_inputs) & set(new_inputs)
        if _canonical(old_inputs[ref]) != _canonical(new_inputs[ref]))
    if added:
        changes['inputs_added'] = added
    if removed:
        changes['inputs_removed'] = removed
    if drifted:
        changes['inputs_drifted'] = {
            ref: {'was': old_inputs[ref], 'now': new_inputs[ref]} for ref in drifted}
    if _canonical(old['recommendation']) != _canonical(new['recommendation']):
        changes['recommendation'] = {'was': old['recommendation'], 'now': new['recommendation']}
    return changes


def replay(env, attachment, rebuild):
    """Chạy lại quyết định và đối chiếu với packet đã lưu.

    `rebuild(env)` trả về `(inputs, recommendation, context)` từ trạng thái
    hiện tại. Kết quả: packet cũ đã verify, packet mới, và diff giữa hai.
    """
    old = load(attachment)
    inputs, recommendation, context = rebuild(env)
    new = build(inputs, recommendation, context)
    return {'stored': old, 'replayed': new, 'drift': diff(old, new)}
