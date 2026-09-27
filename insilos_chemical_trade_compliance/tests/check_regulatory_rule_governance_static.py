# -*- coding: utf-8 -*-
# Part of Insilos. See LICENSE file for full copyright and licensing details.

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = (ROOT / 'models' / 'is_chemical_regulatory_rule.py').read_text()
LEGAL_DOCUMENT_SOURCE = (
    ROOT.parent / 'insilos_hse_compliance' / 'models' / 'is_hse_legal_document.py'
).read_text()


def method(source, class_name, method_name):
    module = ast.parse(source)
    klass = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


def calls_attribute(node, attribute):
    return any(
        isinstance(item, ast.Attribute) and item.attr == attribute
        for item in ast.walk(node)
    )


def main():
    trustworthy = method(RULE_SOURCE, 'ChemicalRegulatoryRule', '_has_trustworthy_legal_document')
    evaluate = method(RULE_SOURCE, 'ChemicalRegulatoryRule', 'evaluate_chemical_obligations')
    activate = method(LEGAL_DOCUMENT_SOURCE, 'HSELegalDocument', 'action_activate')
    assert calls_attribute(trustworthy, 'has_governed_provenance')
    assert "document.state == 'active'" in ast.unparse(trustworthy)
    assert calls_attribute(evaluate, '_has_trustworthy_legal_document')
    assert 'sudo' not in ast.unparse(activate)
    assert any(isinstance(item, ast.Name) and item.id == 'UserError' for item in ast.walk(activate))


if __name__ == '__main__':
    main()
