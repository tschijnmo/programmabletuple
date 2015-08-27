"""
Unit test for the programmable tuple metaclass
"""


import unittest
import itertools

from programmabletuple import ProgrammableTuple, ProgrammableExpr


#
# The programmable tuples class definition
# ========================================
#
# Some utility functions
# ----------------------
#


def _get_full_name(first_name, last_name):
    """Gets the full name"""
    return ', '.join([last_name, first_name])


def _get_sui(self):
    """Gets the age in conventional Asian way

    Here the new borns starts at one year old.
    """
    return self.age + 1


#
# The actual classes
# ------------------
#


class PersonPT(ProgrammableTuple, auto_defining=True):

    """A toy person class

    It just has three simple fields, first name, last name, and age,
    the full name is also given in a data field.

    The defining fields are going to be assigned automatically.

    """

    __data_fields__ = [
        'full_name',
    ]

    def __init__(self, first_name, last_name, age):
        """Initialize a person

        The full name will be set as well.
        """
        self.full_name = _get_full_name(first_name, last_name)

    sui = property(_get_sui)


class PersonPE(ProgrammableExpr):

    """A toy person class as programmable expression

    It is just like the above class. Just the defining fields are going to be
    assigned manually and it is not a tuple subclass.

    """

    __data_fields__ = [
        'full_name',
    ]

    def __init__(self, first_name, last_name, age):
        """Initialize a person

        The full name will be set as well.
        """
        self.first_name = first_name
        self.last_name = last_name
        self.age = age
        self.full_name = _get_full_name(first_name, last_name)

    sui = property(_get_sui)



#
# Subclass definition
# ===================
#


class JohnsonsPT(PersonPT):

    """Members of the Johnson family"""

    def __init__(self, first_name, age):
        self.super().__init__(first_name, 'Johnson', age)

    def is_johnsons(self):
        return True


class JohnsonsPE(PersonPE):

    """Members of the Johnson family"""

    def __init__(self, first_name, age):
        self.super().__init__(first_name, 'Johnson', age)

    def is_johnsons(self):
        return True


#
# The tests
# =========
#


class ImmutableClassTest(unittest.TestCase):

    """Test suite for the programmable tuple metaclass"""

    def setUp(self):

        self.jsmith_pt = PersonPT('John', 'Smith', 49)
        self.jsmith_pe = PersonPE('John', 'Smith', 49)
        self.jsmiths = [self.jsmith_pt, self.jsmith_pe]
        self.ajohnson_pt = JohnsonsPT('Andy', 8)
        self.ajohnson_pe = JohnsonsPE('Andy', 8)

    #
    # Tests of the essential behaviour of programmable tuples
    #

    def test_access(self):
        """Tests the access of the fields of the person"""

        for jsmith in self.jsmiths:
            self.assertEqual(jsmith.first_name, 'John')
            self.assertEqual(jsmith.last_name, 'Smith')
            self.assertEqual(jsmith.age, 49)
            self.assertEqual(jsmith.full_name, 'Smith, John')

    def test_method(self):
        """Tests if the method defined in the class can be called"""

        for jsmith in self.jsmiths:
            self.assertEqual(jsmith.sui, 50)

    def test_immutability(self):
        """Tests if the attributes are really not mutable"""

        def mutate_pt():
            self.jsmith_pt.age = 15
        def mutate_pe():
            self.jsmith_pe.age = 15

        self.assertRaises(AttributeError, mutate_pt)
        self.assertRaises(AttributeError, mutate_pe)

    def test_subclassing(self):
        """Tests if the subclassing is working properly"""

        for andy in [self.ajohnson_pt, self.ajohnson_pe]:
            self.assertEqual(andy.first_name, 'Andy')
            self.assertEqual(andy.last_name, 'Johnson')
            self.assertEqual(andy.age, 8)
            self.assertEqual(andy.sui, 9)
            self.assertEqual(andy.full_name, 'Johnson, Andy')
            self.assertTrue(andy.is_johnsons())

    def test_hashing(self):
        """Tests the correctness of hashing and equality testing"""

        equal_ones = []  # Each entry is a list of equal ones. Different
        # entries are not equal.
        for i in self.jsmiths:
            equal_ones.append([
                i, type(i)('John', 'Smith', 49)
            ])
            equal_ones.append([type(i)('John', 'Smith', 3)])

        for i, v in enumerate(equal_ones):

            # Assert that each pair within the chunk are equal and the same
            # hash.
            for j, k in itertools.combinations(v, 2):
                self.assertEqual(hash(j), hash(k))
                self.assertEqual(j, k)
                continue

            # Assert than each member of the chunk is not equal and has
            # different hash with anything else.
            for j in v:
                for k in itertools.chain.from_iterable(equal_ones[i + 1:]):
                    self.assertNotEqual(hash(j), hash(k))
                    self.assertNotEqual(j, k)
                    continue
                continue

            # Continue to the next chunk.
            continue

    #
    # Tests of the utilities in the mixin class
    #

    def test_update(self):
        """Tests updating a defining attribute"""

        for jsmith in self.jsmiths:
            doug = jsmith._update(first_name='Doug')
            self.assertEqual(doug.first_name, 'Doug')
            self.assertEqual(doug.last_name, 'Smith')
            self.assertEqual(doug.full_name, 'Smith, Doug')
            self.assertEqual(doug.age, 49)

    def test_replace(self):
        """Tests forced replacement of an attribute"""

        for jsmith in self.jsmiths:
            doug_inconsistent = jsmith._replace(first_name='Doug')
            self.assertEqual(doug_inconsistent.first_name, 'Doug')
            self.assertEqual(doug_inconsistent.last_name, 'Smith')
            self.assertEqual(doug_inconsistent.full_name, 'Smith, John')

    def test_formating(self):
        """Tests the formatting as repr and str"""

        # We need to test all combinations, repr and str, with PT and PE.
        repr_args = "(first_name='John', last_name='Smith', age=49)"
        str_args = "(first_name=John, last_name=Smith, age=49)"

        for head, person in [
            ('PersonPT', self.jsmith_pt), ('PersonPE', self.jsmith_pe)
        ]:
            self.assertEqual(repr(person), head + repr_args)
            self.assertEqual(str(person), head + str_args)
            continue

    def test_asdict(self):
        """Tests the asdict methods

        Here only the naive encoding and decoding are tested, not the
        complicated recursive cases.
        """

        for jsmith in self.jsmiths:

            # Tests the conversion to dictionaries.
            def_dict = jsmith._asdict()
            full_dict = jsmith._asdict(full=True)

            for i in [def_dict, full_dict]:
                self.assertEqual(i['first_name'], 'John')
                self.assertEqual(i['last_name'], 'Smith')
                self.assertEqual(i['age'], 49)

            self.assertEqual(len(def_dict), 3)

            self.assertEqual(full_dict['full_name'], 'Smith, John')
            self.assertEqual(len(full_dict), 4)

            # Tests the loading from dictionaries.
            resolved_jsmith = jsmith._load_from_dict(def_dict)
            self.assertEqual(jsmith, resolved_jsmith)
            resolved_jsmith = jsmith._load_from_dict(full_dict, full=True)
            self.assertEqual(jsmith, resolved_jsmith)
