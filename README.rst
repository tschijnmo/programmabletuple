immutableclass
==============

Python metaclass for making instances of user-defined classes immutable

.. image:: https://travis-ci.org/tschijnmo/immutableclass.svg?branch=master
    :target: https://travis-ci.org/tschijnmo/immutableclass

This module provides a metaclass for to make the instances of user-defined
classes immutable. Its basic functionality is modelled after the
:py:cls:`collections.namedtuple`, but it offers more object-orientation and
programmability.

Basically, here instances of immutable classes are frozen once they are
initialized. Any attempt to mutate the state of the instance will cause an
error. Otherwise they are designed to behave as similar to the common mutable
instances as possible.

Basic usage
-----------

Fields
^^^^^^

Since all the information about setting the instances of the immutable classes
needs to be given to the initializer, the arguments of the initializer uniquely
defines an value of the immutable class. Hence they are called the defining
fields of the class. Besides the defining fields, additional fields can be
added to the class instances to hold data that is essential for them. This can
be achieved by assigning a list of names for the data fields to the
``__fields__`` attribute of the class, in the same way as the ``__slots__``
attribute is used. And the actual value for the data fields can be set in the
initializer in the same way as normal. For example, to define an immutable
class for people to store they first and last name, and we would like the
instances to carry the full name with comma separation for alphabetization, we
can just define

.. code:: python

    class Person(metaclass=ImmutableClass):
        __fields__ = ['full_name']
        def __init__(self, first_name, last_name):
            self.full_name = ', '.join([last_name, first_name])

Then in this way, if we make an instance by running ``Person('John',
'Smith')``, the values of all the fields, defining fields and data fields, can
all be able to be retrieved by using the dot notation. Note that if some fields
are desired to be hold private, the same underscore convention of python could
just be used. Just it is not advised to keep defining attribute private.

Methods
^^^^^^^

Methods can also be defined for immutable classes with exactly the same syntax
as the normal mutable class. Just here the only place where ``self`` could be
mutated is in the ``__init__`` method, any attempt to mutate ``self`` would
cause an error in any other method. So the methods here should be ones that
concentrates more on the return value rather than mutating the state of the
object. Due to this apparent deviation from the classical Smalltalk-style
object-orientated programming, the methods could be defined outside the class
as a normal function, and then get forwarded into the class for convenience.
For instance, if we have got a class for symbolic mathematical expressions and
a function to compute the derivative with respect to a symbol, we could do

.. code:: python

    def diff_expr(expr, symb):
        """Compute the derivative w.r.t. a symbol"""
        ... ...

    class Expr(metaclass=ImmutableClass):
        ... ...
        diff = diff_expr
        ... ...

In this way, to differentiate an expression ``e`` with respect to a symbol
``x``, we could do both ``e.diff(x)`` and ``diff_expr(e, x)``. It only needs to
be noted that for functions that is intended to be used as a method as well,
the argument to be used as ``self`` needs to be put in the first slot.
