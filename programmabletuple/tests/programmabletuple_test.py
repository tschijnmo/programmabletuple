"""
Unit test for the programmable tuple metaclass
"""

import unittest
import collections

from programmabletuple import ProgrammableTuple


class ImmutableClassTest(unittest.TestCase):

    """Test suite for the programmable tuple metaclass

    A toy person class will be set up, and various aspects of its behaviour
    tested. Also it is going to be subclassed for testing the inheritance.

    """

    def setUp(self):

        class Person(metaclass=ProgrammableTuple,
                     default_attr=lambda n: n):

            """A toy person class

            It just has three simple fields, first name, last name, and age,
            the full name is also given in a data field.

            """

            __data_fields__ = [
                'full_name',
                'nothing',
                ]

            def __init__(self, first_name, last_name, age):

                """Initialize a person

                The full name will be set as well.

                """

                self.full_name = ', '.join([last_name, first_name])

            def get_sui(self):

                """Get the age in conventional Asian way

                Here the new borns starts at one year old.

                """

                return self.age + 1

        self.Person = Person
        self.jsmith = Person('John', 'Smith', 49)

    def test_access(self):

        """Tests the access of the fields of the person"""

        jsmith = self.jsmith
        self.assertEqual(jsmith.first_name, 'John')
        self.assertEqual(jsmith.last_name, 'Smith')
        self.assertEqual(jsmith.age, 49)
        self.assertEqual(jsmith.full_name, 'Smith, John')

    def test_method(self):

        """Tests if the method defined in the class can be called"""

        self.assertEqual(self.jsmith.get_sui(), 50)

    def test_inmutability(self):

        """Tests if the attributes are really not mutable"""

        def mutate():
            self.jsmith.age = 15
        self.assertRaises(AttributeError, mutate)

    def test_update(self):

        """Tests updating a defining attribute"""

        doug = self.jsmith._update(first_name='Doug')
        self.assertEqual(doug.first_name, 'Doug')
        self.assertEqual(doug.last_name, 'Smith')
        self.assertEqual(doug.full_name, 'Smith, Doug')
        self.assertEqual(doug.age, 49)

    def test_replace(self):

        """Tests forced replacement of an attribute"""

        doug_incons = self.jsmith._replace(first_name='Doug')
        self.assertEqual(doug_incons.first_name, 'Doug')
        self.assertEqual(doug_incons.last_name, 'Smith')
        self.assertEqual(doug_incons.full_name, 'Smith, John')

    def test_default_attr(self):

        """Tests if the default attribute is assigned as requested"""

        self.assertEqual(self.jsmith.nothing, 'nothing')

    def test_subclassing(self):

        """Tests if the subclassing is working properly"""

        class Johnsons(self.Person):

            """Members of the Johnson family"""

            def __init__(self, first_name, age):
                self.super().__init__(first_name, 'Johnson', age)

            def is_johnsons(self):
                return True

        andy = Johnsons('Andy', 8)

        self.assertEqual(andy.first_name, 'Andy')
        self.assertEqual(andy.last_name, 'Johnson')
        self.assertEqual(andy.age, 8)
        self.assertEqual(andy.get_sui(), 9)
        self.assertEqual(andy.full_name, 'Johnson, Andy')
        self.assertTrue(andy.is_johnsons())

    def test_hashing(self):

        """Tests the correctness of hashing"""

        jsmith2 = self.Person('John', 'Smith', 49)
        young = self.Person('John', 'Smith', 3)

        self.assertEqual(hash(self.jsmith), hash(jsmith2))
        self.assertNotEqual(hash(self.jsmith), hash(young))

    def test_asdict(self):

        """Tests the asdict methods"""

        plain_def_dict = self.jsmith._asdict()
        plain_full_dict = self.jsmith._asdict(full=True)
        ordered_def_dict = self.jsmith._asdict(ordered=True)
        ordered_full_dict = self.jsmith._asdict(full=True, ordered=True)

        for i in [plain_def_dict, plain_full_dict,
                  ordered_full_dict, ordered_full_dict]:
            self.assertEqual(i['first_name'], 'John')
            self.assertEqual(i['last_name'], 'Smith')
            self.assertEqual(i['age'], 49)

        for i in [plain_def_dict, plain_full_dict]:
            self.assertEqual(plain_def_dict.__class__, dict)
        for i in [ordered_def_dict, ordered_full_dict]:
            self.assertEqual(i.__class__, collections.OrderedDict)

        for i in [plain_def_dict, ordered_def_dict]:
            self.assertEqual(len(i), 3)
        for i in [plain_full_dict, ordered_full_dict]:
            self.assertEqual(i['full_name'], 'Smith, John')
