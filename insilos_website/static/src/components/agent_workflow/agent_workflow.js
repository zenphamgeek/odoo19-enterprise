import { Component, onMounted, onWillUnmount, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';

export class AgentWorkflow extends Component {
    static template = "insilos_website.AgentWorkflow";
    static props = {};

    setup() {
        this.state = useState({ active: 0, playing: true });
        this.steps = [
            {
                name: "Detect",
                eyebrow: "SIGNAL",
                title: "Phát hiện bất thường có ngữ cảnh",
                text: "Kết hợp time-series, sự kiện và lịch sử tài sản để nhận diện tín hiệu đáng chú ý.",
                event: "Bearing temperature drift detected",
            },
            {
                name: "Investigate",
                eyebrow: "EVIDENCE",
                title: "Tập hợp bằng chứng liên quan",
                text: "Agent truy xuất alarm, công việc trước đó, manual, điều kiện vận hành và tác động downstream.",
                event: "12 sources reviewed · 3 drivers ranked",
            },
            {
                name: "Recommend",
                eyebrow: "DECISION",
                title: "Đề xuất hành động và giải thích",
                text: "So sánh phương án theo rủi ro, SLA, nguồn lực và ràng buộc kỹ thuật trước khi đề xuất.",
                event: "Reschedule inspection to 10:30",
            },
            {
                name: "Approve",
                eyebrow: "CONTROL",
                title: "Giữ con người trong vòng kiểm soát",
                text: "Áp dụng role, quyền duyệt, citation, audit trail và quy tắc escalation cho quyết định quan trọng.",
                event: "Supervisor approval requested",
            },
            {
                name: "Act",
                eyebrow: "WORKFLOW",
                title: "Đưa quyết định vào hệ thống thực thi",
                text: "Tạo hoặc cập nhật work order, dispatch, notification và theo dõi kết quả để cải thiện mô hình.",
                event: "WO-221 updated · technician notified",
            },
        ];
        this.timer = null;

        onMounted(() => {
            const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            if (!reducedMotion) {
                this.start();
            } else {
                this.state.playing = false;
            }
        });

        onWillUnmount(() => this.stop());
    }

    get activeStep() {
        return this.steps[this.state.active];
    }

    selectStep(index) {
        this.state.active = index;
        this.restartIfPlaying();
    }

    togglePlayback() {
        this.state.playing = !this.state.playing;
        if (this.state.playing) {
            this.start();
        } else {
            this.stop();
        }
    }

    start() {
        this.stop();
        this.timer = window.setInterval(() => {
            this.state.active = (this.state.active + 1) % this.steps.length;
        }, 3400);
    }

    stop() {
        if (this.timer) {
            window.clearInterval(this.timer);
            this.timer = null;
        }
    }

    restartIfPlaying() {
        if (this.state.playing) {
            this.start();
        }
    }
}

registry.category("public_components").add("insilos_website.AgentWorkflow", AgentWorkflow);
