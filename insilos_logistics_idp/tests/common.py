from uuid import uuid4

from psycopg2 import IntegrityError


def unique_fixture(value):
    return '%s-%s' % (value, uuid4().hex)


def assert_unique_constraint(test, create):
    with test.assertRaises(IntegrityError), test.cr.savepoint():
        create()


def new_logistics_test_user(new_test_user, env, **values):
    return new_test_user(env, email=False, **values)
