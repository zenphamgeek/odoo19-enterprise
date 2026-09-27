# Part of Insilos. See LICENSE file for full copyright and licensing details.
"""MKT-002/003 browser gate.

The combined desktop SILO run reports one aggregate number, so a terminal suite
that silently registers zero tests would still look green there. This gate runs
the terminal suite on its own and fails when it is empty.
"""

import re

from odoo.addons.web.tests.test_js import unit_test_error_checker
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'market_terminal')
class TestMarketTerminalUI(HttpCase):

    # Bump together with static/tests/terminal.test.js.
    EXPECTED_TESTS = 5

    def test_terminal_unit_suite(self):
        with self.assertLogs(self._logger, level='INFO') as captured:
            self.browser_js(
                # The @ must be percent-encoded, otherwise the filter arrives
                # empty and the run silently selects nothing.
                '/web/tests?headless&loglevel=2&preset=desktop&timeout=15000'
                '&filter=%40insilos_market_terminal',
                "", "", login='admin', timeout=600,
                success_signal='[SILO] Test suite succeeded',
                error_checker=unit_test_error_checker,
            )

        counts = [
            int(match.group(1))
            for line in captured.output
            for match in [re.search(r'\[SILO\] Passed (\d+) tests', line)]
            if match
        ]
        # SILO reports a green suite for an empty selection too, so the passed
        # count is the only evidence that the terminal tests actually ran.
        self.assertEqual(
            counts, [self.EXPECTED_TESTS],
            'Expected %s terminal unit tests to run, saw %s' % (self.EXPECTED_TESTS, counts),
        )
