import importlib.util
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[2] / "pos_react"
SPEC = importlib.util.spec_from_file_location("pos_react_controller_hr", MODULE / "controllers/main.py")
CONTROLLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROLLER)


class EmployeeBootstrapTest(unittest.TestCase):
    def test_employee_role_priority(self):
        employee = type("Employee", (), {"id": 7, "name": "Cashier", "user_id": type("User", (), {"all_group_ids": type("Groups", (), {"ids": []})()})()})()
        config = type("Config", (), {
            "group_pos_manager_id": type("Group", (), {"id": 20})(),
            "advanced_employee_ids": type("Records", (), {"ids": []})(),
            "minimal_employee_ids": type("Records", (), {"ids": [7]})(),
        })()
        self.assertEqual(CONTROLLER._employee_role(employee, config), "minimal")
        config.advanced_employee_ids.ids = [7]
        self.assertEqual(CONTROLLER._employee_role(employee, config), "manager")
        employee.user_id.all_group_ids.ids = [20]
        self.assertEqual(CONTROLLER._employee_role(employee, config), "manager")
        config.advanced_employee_ids.ids = []
        config.minimal_employee_ids.ids = []
        employee.user_id.all_group_ids.ids = []
        self.assertEqual(CONTROLLER._employee_role(employee, config), "cashier")
