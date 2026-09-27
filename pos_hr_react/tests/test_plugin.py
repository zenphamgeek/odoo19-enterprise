import subprocess
import unittest
from pathlib import Path


PLUGIN = Path(__file__).parents[1] / "static/src/pos_react_plugin.js"


class PosHrReactPluginTest(unittest.TestCase):
    def test_minimal_employee_cannot_decrement_lines(self):
        script = f"""
        const registrations = [];
        global.React = {{ createElement: () => null }};
        global.window = {{ posReactPlugins: {{ register: (...args) => registrations.push(args) }} }};
        require({str(PLUGIN)!r});
        const policy = registrations.find(([point]) => point === 'action')[2];
        if (policy.canMutateLine({{}}, {{ pluginData: {{ role: 'minimal' }} }})) process.exit(1);
        if (!policy.canMutateLine({{}}, {{ pluginData: {{ role: 'cashier' }} }})) process.exit(2);
        if (!policy.canMutateLine({{}}, {{ pluginData: {{ role: 'manager' }} }})) process.exit(3);
        if (policy.canRefund({{ pluginData: {{ role: 'minimal' }}, locked: false }})) process.exit(4);
        if (policy.canRefund({{ pluginData: {{ role: 'cashier' }}, locked: true }})) process.exit(5);
        if (!policy.canRefund({{ pluginData: {{ role: 'cashier' }}, locked: false }})) process.exit(6);
        """
        subprocess.run(["node", "-e", script], check=True)

    def test_cash_move_uses_rpc_bridge_and_is_hidden_while_locked(self):
        script = f"""
        const registrations = [];
        const elements = [];
        const states = ['out', '12.5', 'Petty cash', ''];
        global.React = {{
            createElement: (type, props, ...children) => {{ const element = {{ type, props: props || {{}}, children }}; elements.push(element); return element; }},
            useState: () => [states.shift(), () => {{}}],
        }};
        global.window = {{ posReactPlugins: {{ register: (...args) => registrations.push(args) }} }};
        require({str(PLUGIN)!r});
        const cashMove = registrations.find(([, id]) => id === 'pos_hr_react.cash_move')[2];
        if (cashMove.isVisible({{ pluginData: {{ employee: {{ id: 7 }} }}, locked: true }})) process.exit(1);
        if (!cashMove.isVisible({{ pluginData: {{ employee: {{ id: 7 }} }}, locked: false }})) process.exit(2);
        const calls = [];
        cashMove.component({{
            sessionId: 9,
            locked: false,
            pluginData: {{ employee: {{ id: 7 }} }},
            rpc: (...args) => {{ calls.push(args); return Promise.resolve(); }},
            closeAction: () => {{}},
        }}).type({{
            context: {{
                sessionId: 9,
                locked: false,
                pluginData: {{ employee: {{ id: 7 }} }},
                rpc: (...args) => {{ calls.push(args); return Promise.resolve(); }},
                closeAction: () => {{}},
            }},
        }});
        const form = elements.find(element => element.type === 'form');
        await form.props.onSubmit({{ preventDefault: () => {{}} }});
        const [model, method, args] = calls[0] || [];
        if (model !== 'pos.session' || method !== 'pos_react_try_cash_in_out') process.exit(3);
        if (JSON.stringify(args) !== JSON.stringify([9, 'out', 12.5, 'Petty cash'])) process.exit(4);
        if (!elements.some(element => element.type === 'button' && element.props.type === 'submit')) process.exit(5);
        """
        subprocess.run(["node", "--input-type=module", "-e", script], check=True)
