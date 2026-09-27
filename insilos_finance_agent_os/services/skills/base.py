# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""Execution mode cho skill — chỗ duy nhất quyết định skill được ghi gì (E04).

Bốn mức, xếp theo quyền tăng dần:

    READ        không ghi gì
    REPORT      ghi evidence: attachment + message vào record đã có
    DRAFT       tạo bản nháp, buộc người xem preview trước khi confirm
    CONTROLLED  hành động governed: preview + idempotency, và mọi ghi vẫn đi
                qua đúng model domain — nghĩa là stage gate của domain vẫn
                đứng nguyên giữa skill và hậu quả

Cái được gác ở đây là **trần quyền**: skill mode READ gọi helper ghi sẽ nổ
ngay tại decorator, không phụ thuộc vào việc tác giả skill nhớ luật. Còn trần
dưới — CONTROLLED không vượt được approval — không nằm ở lớp này mà ở stage
gate của addon domain, và test sẽ chứng minh skill KHÔNG vượt được, thay vì
tin rằng nó không thử.
"""

from functools import wraps

from odoo.exceptions import UserError

from .. import capability

READ = 'READ'
REPORT = 'REPORT'
DRAFT = 'DRAFT'
CONTROLLED = 'CONTROLLED'

_ORDER = (READ, REPORT, DRAFT, CONTROLLED)

# Registry: skill name -> mode. Điền bởi decorator, đọc bởi test khoá danh sách.
SKILL_MODES = {}


def skill(mode):
    """Khai một hàm là skill với execution mode cố định.

    Hàm nhận `env` làm tham số đầu. Mode nào có quyền ghi thì trước khi chạy
    phải qua `capability.assert_writable` — tenant read-only chặn tại đây,
    trước khi skill kịp làm gì.
    """
    if mode not in _ORDER:
        raise ValueError('Unknown execution mode: %s' % mode)

    def decorate(func):
        SKILL_MODES[func.__name__] = mode

        @wraps(func)
        def wrapper(env, *args, **kwargs):
            if mode != READ:
                capability.assert_writable(env)
            ctx = SkillContext(env, mode)
            return func(ctx, *args, **kwargs)

        wrapper.execution_mode = mode
        return wrapper

    return decorate


class SkillContext:
    """Env bọc trong trần quyền của mode.

    Skill không cầm `env` trần: nó cầm context, và mọi đường ghi đi qua các
    helper có kiểm mode. `ctx.env` vẫn mở cho ĐỌC — giới hạn đọc là việc của
    ACL/record rule, không phải của lớp này.
    """

    __slots__ = ('env', 'mode')

    def __init__(self, env, mode):
        self.env = env
        self.mode = mode

    def _need(self, minimum, action):
        if _ORDER.index(self.mode) < _ORDER.index(minimum):
            raise UserError(
                'Skill mode %s cannot %s: requires at least %s.'
                % (self.mode, action, minimum)
            )

    # -- REPORT trở lên -------------------------------------------------

    def post_evidence(self, record, body, attachment_name=None, attachment_raw=None):
        """Ghi evidence vào record đã có: message, kèm attachment nếu có."""
        self._need(REPORT, 'post evidence')
        attachment_ids = []
        if attachment_name is not None:
            attachment = self.env['ir.attachment'].create({
                'name': attachment_name,
                'raw': attachment_raw or b'',
                'res_model': record._name,
                'res_id': record.id,
            })
            attachment_ids = [attachment.id]
        return record.message_post(body=body, attachment_ids=attachment_ids)

    # -- DRAFT trở lên ---------------------------------------------------

    def create_draft(self, model_name, values):
        """Tạo bản ghi nháp trên model domain. Không tự confirm."""
        self._need(DRAFT, 'create a draft')
        return self.env[model_name].create(values)

    # -- CONTROLLED ------------------------------------------------------

    def run_governed(self, record, method_name, *args, **kwargs):
        """Gọi một governed action trên model domain.

        Cố ý KHÔNG sudo, KHÔNG đổi user: nếu stage gate hay ACL của domain
        từ chối thì exception đó đi thẳng ra ngoài. Skill được phép *xin*,
        không được phép *tự cấp*.
        """
        self._need(CONTROLLED, 'run a governed action')
        return getattr(record, method_name)(*args, **kwargs)
