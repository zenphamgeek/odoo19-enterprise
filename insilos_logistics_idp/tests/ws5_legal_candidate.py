import importlib.util
import json
import socket
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'services/legal_candidate_adapter.py'
SPEC = importlib.util.spec_from_file_location('ws5_legal_candidate_adapter', MODULE_PATH)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


class LegalCandidateAdapterTest(unittest.TestCase):
    def assert_tier4_containment(self, result):
        self.assertEqual((result['source_tier'], result['legal_authority'], result['verification'],
                          result['verdict'], result['activation_allowed']),
                         ('early_warning_tier_4', False, 'unverified', 'REVIEW', False))

    def response(self, *, status=200, content_type='application/json', body=b'{}', length=None):
        response = Mock(status=status)
        headers = {'Content-Type': content_type}
        if length is not None:
            headers['Content-Length'] = str(length)
        response.getheader.side_effect = lambda key, default=None: headers.get(key, default)
        response.read.return_value = body
        return response

    def test_ssrf_dns_rejects_non_public_and_empty_answers(self):
        with patch.object(ADAPTER.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaisesRegex(ADAPTER.ValidationError, 'not public'):
                ADAPTER._validate_addresses(ADAPTER.HOST)
        with patch.object(ADAPTER.socket, 'getaddrinfo', return_value=[]):
            with self.assertRaisesRegex(ADAPTER.ValidationError, 'no answers'):
                ADAPTER._validate_addresses(ADAPTER.HOST)

    def test_redirect_mime_and_size_fail_closed(self):
        for response, message in (
            (self.response(status=302), 'redirects'),
            (self.response(content_type='text/html'), 'MIME'),
            (self.response(length=ADAPTER.MAX_BYTES + 1), 'maximum bytes'),
            (self.response(body=b'x' * (ADAPTER.MAX_BYTES + 1)), 'maximum bytes'),
        ):
            connection = Mock()
            connection.getresponse.return_value = response
            with patch.object(ADAPTER, '_validate_addresses', return_value=('8.8.8.8',)), \
                    patch.object(ADAPTER, '_PinnedHTTPSConnection', return_value=connection):
                with self.assertRaisesRegex(ADAPTER.ValidationError, message):
                    ADAPTER._request('/api/documents')

    def test_timeout_retries_then_dead_letter_without_payload_leak(self):
        with patch.object(ADAPTER, '_request', side_effect=socket.timeout('secret-token')):
            result = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'})
        self.assertEqual((result['machine_status'], result['attempt_count'], result['dead_letter']),
                         ('DEAD_LETTER', 3, True))
        self.assertEqual(result['error_code'], 'TimeoutError')
        self.assertNotIn('secret-token', json.dumps(result))

    def test_pagination_dedupe_hashes_and_tier4_review_are_deterministic(self):
        pages = [
            json.dumps({'data': [{'id': 2, 'title': 'B'}, {'id': 1, 'title': 'A'}],
                        'meta': {'nextPage': 2}}).encode(),
            json.dumps({'data': [{'title': 'A', 'id': 1}], 'meta': {}}).encode(),
        ]
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        with patch.object(ADAPTER, '_request', side_effect=pages) as request:
            first = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'}, now=now)
        with patch.object(ADAPTER, '_request', side_effect=pages):
            second = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'}, now=now)
        self.assertEqual([item['source_key'] for item in first['candidates']], ['1', '2'])
        self.assertEqual(first, second)
        self.assertIn('page=2', request.call_args_list[1].args[0])
        self.assertEqual(len(first['body_sha256']), 2)
        self.assertRegex(first['request_fingerprint'], r'^[0-9a-f]{64}$')
        self.assertEqual((first['source_tier'], first['verdict'], first['activation_allowed'],
                          first['legal_authority'], first['machine_status']),
                         ('early_warning_tier_4', 'REVIEW', False, False, 'FETCHED_REVIEW'))

    def test_conflicting_duplicate_is_removed_and_reviewed(self):
        body = json.dumps({'data': [{'id': 1, 'title': 'A'}, {'id': 1, 'title': 'B'}]}).encode()
        with patch.object(ADAPTER, '_request', return_value=body):
            result = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'})
        self.assertEqual(result['candidates'], [])
        self.assertEqual((result['error_code'], result['machine_status']),
                         ('conflicting_source_version_hash', 'REVIEW'))

    def test_conflicted_key_is_tombstoned_for_later_duplicates(self):
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        for titles in (('A', 'B', 'A'), ('A', 'B', 'B')):
            body = json.dumps({'data': [{'id': 1, 'title': title} for title in titles]}).encode()
            with patch.object(ADAPTER, '_request', return_value=body):
                result = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'}, now=now)
            self.assertEqual(result['candidates'], [])
            self.assertEqual((result['error_code'], result['machine_status'], result['verdict'],
                              result['source_tier'], result['activation_allowed']),
                             ('conflicting_source_version_hash', 'REVIEW', 'REVIEW',
                              'early_warning_tier_4', False))

    def test_conflicted_key_is_tombstoned_across_pages(self):
        pages = [
            json.dumps({'data': [{'id': 1, 'title': 'A'}], 'meta': {'nextPage': 2}}).encode(),
            json.dumps({'data': [{'id': 1, 'title': 'B'}, {'id': 1, 'title': 'A'}]}).encode(),
        ]
        with patch.object(ADAPTER, '_request', side_effect=pages):
            result = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'})
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['error_code'], 'conflicting_source_version_hash')

    def test_conflict_output_is_permutation_equivalent(self):
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        outputs = []
        for titles in (('A', 'B', 'A'), ('B', 'A', 'B'), ('A', 'B', 'C')):
            body = json.dumps({'data': [{'id': 1, 'title': title} for title in titles]}).encode()
            with patch.object(ADAPTER, '_request', return_value=body):
                result = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'}, now=now)
            outputs.append((result['candidates'], result['content_sha256'], result['error_code']))
        self.assertEqual(outputs, [outputs[0]] * len(outputs))

    def test_invalid_pagination_and_governance_metadata_fail_closed(self):
        body = json.dumps({'data': [], 'meta': {'nextPage': 1}}).encode()
        with patch.object(ADAPTER, '_request', return_value=body):
            result = ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, {'keyword': 'hải quan'})
        self.assertEqual((result['error_code'], result['machine_status']), ('invalid_pagination', 'REVIEW'))
        self.assertEqual({key: result[key] for key in (
            'license_terms', 'retention_terms', 'content_owner', 'independent_oracle_status')}, {
                'license_terms': 'pending', 'retention_terms': 'pending',
                'content_owner': 'pending', 'independent_oracle_status': 'pending'})

    def test_provider_payload_cannot_escalate_containment_on_any_result_path(self):
        escalation = {
            'id': 1, 'source_tier': 'authoritative_tier_1', 'legal_authority': True,
            'verification': 'verified', 'verdict': 'PASS', 'activation_allowed': True,
        }
        for error, dead_letter in ((None, False), ('provider_error', False),
                                   ('retry_exhausted', True), ('conflict', False)):
            result = ADAPTER._result('fingerprint', [escalation], [b'{}'], None,
                                     error, ADAPTER.RETRIES if dead_letter else 1, dead_letter)
            self.assert_tier4_containment(result)

    def test_registry_rejects_config_containment_escalation(self):
        config = ADAPTER._CONFIG
        policy = json.loads((config / 'compliance_policy.json').read_text())
        pack = json.loads((config / 'vn_legal_candidate_pack.json').read_text())
        mutations = (
            ('provider', 'source_tier', 'authoritative_tier_1'),
            ('provider', 'legal_authority', True),
            ('provider', 'verification', 'verified'),
            ('provider', 'auto_activation', True),
            ('option', 'source_tier', 'authoritative_tier_1'),
            ('option', 'legal_authority', True),
            ('option', 'verification', 'verified'),
            ('option', 'activation', True),
            ('option', 'automatic_activation', True),
            ('option', 'expected_terminal_status', 'pass'),
        )
        for target, key, value in mutations:
            changed_policy = json.loads(json.dumps(policy))
            changed_pack = json.loads(json.dumps(pack))
            record = (changed_policy['provider_registry'][ADAPTER.REGISTRY_KEY]
                      if target == 'provider' else changed_pack['source_options'][ADAPTER.REGISTRY_KEY])
            record[key] = value
            with patch.object(ADAPTER.Path, 'read_text', side_effect=(
                    json.dumps(changed_policy), json.dumps(changed_pack))):
                with self.assertRaisesRegex(ADAPTER.ValidationError, 'configuration is invalid'):
                    ADAPTER._registry()

    def test_query_rejects_arbitrary_url_and_secret_fields(self):
        for query in ({'keyword': 'x', 'url': 'http://127.0.0.1'}, {'keyword': 'x', 'token': 'secret'}):
            with self.assertRaises(ADAPTER.ValidationError):
                ADAPTER.fetch_candidates(ADAPTER.REGISTRY_KEY, query)


if __name__ == '__main__':
    unittest.main()
