
programmabletuple
=================

Python metaclass for making named tuples with the programmability of user-
defined classes

.. image:: https://travis-ci.org/tschijnmo/programmabletuple.svg?branch=master
    :target: https://travis-ci.org/tschijnmo/programmabletuple

.. image:: https://coveralls.io/repos/tschijnmo/programmabletuple/badge.png
    :target: https://coveralls.io/r/tschijnmo/programmabletuple 

.. image:: https://badge.fury.io/py/programmabletuple.svg
    :target: http://badge.fury.io/py/programmabletuple

In essence, the programmable tuple metaclass in this module is able to make
user-defined classes in Python has got the immutability of named tuple while
retaining the programmability of user-defined classes. Merely minimal change
to the code for class definition is needed, and a lot feature from class
definition, like methods and inheritance, are supported.

The basic motivation for this is to make code more secure and less error- prone
for objects that does not frequently need to be mutated during its life time.
Frequently in Python code, we have got structures (any structure) holding
references to instances of user-defined classes, which by default are all
mutable. But sometimes the correctness of the behaviour of the structure would
depend on the assumption that the objects that these references point to will
not be mutated. A solution to this problem is to make copies of the instances
into the structure rather than just hold a reference and share the actual
object. In this way, other parts of the code could safely mutate the states of
the instances without any undesirable side effect. However, the copying comes
with cost. For cases where the the objects referenced will almost definitely be
mutated, this cost is necessary. But for cases where the objects are unlikely
to be mutated in the majority of cases, the copying might cease to be an
economical choice. So the basic idea of this metaclass is that we could have a
means to enforce the references to be pointing the the same value, while we can
still make new instances out of the old ones if they really need to be mutated.
It can be construed as an attempt to make Python more functional while
maintaining its object-orientated aspect. The resulted programmable tuple
resembles a hybrid of the Haskell record and the user-defined class in Python.

Basic usage
-----------

Fields
^^^^^^

The programmable tuple is directly modelled after the named tuple class in the
standard library. So unlike plain user-defined classes, the instances could
only have a set of pre-defined fields for each class. Since instances cannot
be changed after the initialization, all the information about instances of an
immutable class needs to be given to the initializer. So the arguments of the
initializer uniquely define values of the programmable tuple. Hence they are
called the defining fields of the class. Besides the defining fields,
additional fields can be added to the class instances to hold some other
essential data. These fields are going to be termed the data fields. This can
be achieved by assigning a list of names to the ``__data_fields__`` attribute
of the class, in the same way as the ``__slots__`` attribute is used. And the
actual value for the data fields can be set in the initializer in the same way
as normal. For example, to define an programmable tuple for people to store
their first and last name, and we would like the instances to carry the full
name with comma separation for alphabetization, we can just define

.. code:: python

    class Person(metaclass=ProgrammableTuple):
        __data_fields__ = ['full_name']
        def __init__(self, first_name, last_name):
            self.full_name = ', '.join([last_name, first_name])

Then in this way, if we make an instance by running ``Person('John',
'Smith')``, the values of all the fields, defining fields and data fields, can
all be able to be retrieved by using the dot notation, like ``p.full_name``.
Note that if some fields are desired to be hold private, the same underscore
convention of python could be used. Just it is not advised to keep defining
attributes private.

For the fields, there are two keyword arguments that can be used for the class
creation. The ``auto_defining`` argument, which is True by default, controls
the automatic assignment of the defining fields to the ``self`` object in the
initializer before the actual invocation of the user-defined initializer. For
fields that is not explicitly given a value in the initializer,
``default_attr`` argument can be set to a function that returns the default
value to set when given the name of the field as a string.

Note that although there is no compulsory requirement that the values set to
the defining fields should match the argument that is given to the initializer,
it is advised that at least the defining fields can be used to reproduce the
object. For instance, for a class named ``A`` with fields ``a`` and ``b``, it
is a good practice to keep ``A(spam.a, spam.b) == spam`` for any instance
``spam`` of the class ``A``, while ``spam.a`` does not need to match the
argument ``a`` that was used for creating ``spam``. Frequently the argument
will accept a wide range of types for the argument, but a specific form is
going to be stored as the attribute. This form can be termed the canonical form
for that argument. For example, the initializer could allow any iterator for a
defining field, but it is better to cast it to a tuple to be stored in the
immutable object. Then the tuple form of the elements is the canonical form of
that argument. It does not need to match that actual argument used for its
creation but it is always able to reproduce the value. For cases where most of
the defining fields are just taken to be the value from the argument, the
``auto_defining`` option can be set to ``True`` to save the lines of code. But
for cases where almost all arguments need to be cast and specifically assigned,
that option can be turned off to save of overhead of the automatic assignments.

Methods
^^^^^^^

Methods can also be defined for programmable tuples with exactly the same
syntax as the normal user-defined classes. Just here the only place where
``self`` could be mutated is in the ``__init__`` method, any attempt to mutate
``self`` would cause an error in any other method. So the methods here should
be ones that concentrates more on the return value rather than mutating the
state of the object. Due to this apparent deviation from the classical
Smalltalk-style object-orientated programming, the methods normally could be
clearly defined outside the class as a normal function, and then then we can
forward them into the class for convenience. For instance, if we have got a
class for symbolic mathematical expressions and a function to compute the
derivative with respect to a symbol, we could do

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
the argument to be used as ``self`` needs to be put in the first slot. Of
course methods can be kept in the class only as normal if it is desirable.

Non-destructive update
^^^^^^^^^^^^^^^^^^^^^^

Frequently we need values of user-defined class that is different from an
existing value by relatively small amount. With mutable class, frequently this
is achieved by mutating the instance. However, here the instances are no
longer mutable. So methods to update instances non-destructively are provided.
Note that these methods will return new instances with the field updated and
leave the original value intact, in the same way as the Haskell records works.

Basically two methods are provided for this purpose, ``_update`` and
``_replace``. Both of them takes keyword arguments with the keys being the name
of the field to be updated and values being the new value. But for the
``_update`` method, only defining fields are able to be updated, and more
importantly, a new instance will be created **by using the updated defining
fields through the initializer**. At the same time, the ``_replace`` method
will just perform a plain replacement of a particular field without going
through the initializer again, and it works for both defining and data fields.

Both of these two methods are named with an initial underscore, this is not
only an attempt to be consistent with the named tuple in the standard library,
but an encourage to use them only in methods as well. Then then wrapping
methods could carry the actual semantics of the update operation.

Inheritance
^^^^^^^^^^^

Programmable tuple classes can inherit from other programmable tuple classes.
And this inheritance has been made to be as similar to the plain mutable
classes as possible. Instances of subclass are instances of the corresponding
superclass and has access to all the methods of the superclass. There is just
one notable difference, in the initializer, the built-in ``super`` function is
not working as before. To call the initializer of superclass, we can either
use ``self.super().__init__`` instead, or we can name the superclass
explicitly, like ``SuperClass.__init__(self, args)``.

Miscellaneous
^^^^^^^^^^^^^

Instances of an programmable tuples with all the defining fields hashable are
hashable. The default hashing function is the default hashing of the tuple
formed by the class identity and the defining fields.

Instances are all picklable.

As the named tuple, classes of this metaclass will carry an ``_asdict`` method
to convert the instance to dictionary. The method comes with two keyword
arguments, ``full`` can be used to make the dictionary contain the data fields
as well, and ``ordered`` can be used to return an ordered dictionary instead.
Both of the two default to false.
