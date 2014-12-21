"""
Definition of a metaclass for making named tuple with programmability

The basic idea of the implementation is that for each programmable tuple class,
a proxy class is generated that imitates its behaviour as much as possible. The
objects of this proxy class is going to be used for the initializer, then the
values for the various fields are read and set into the actual programmable
tuple.

"""

import functools
import itertools
import collections


#
# The metaclass
# =============
#

class ProgrammableTuple(type):

    """Programmable tuple metaclass"""

    def __new__(mcs, name, bases, nmspc, default_attr=lambda _: None):

        """Generates a new type instance for the programmable tuple class"""

        # Make a shallow copy of the original namespace. The new copy can be
        # used for the new programmable tuple class, while the original copy
        # is going to be for the proxy class.
        new_nmspc = dict(nmspc)

        # Fields determination
        # --------------------

        fields, defining_count = _determine_fields(bases, new_nmspc)
        # Update the corresponding fields in the name space
        new_nmspc['__fields__'] = fields
        new_nmspc['__slots__'] = ()  # prevent new attribute assignment
        new_nmspc['__defining_count__'] = defining_count

        # Initializer definition
        # ----------------------

        # Prepare the proxy class in initialization function
        ProxyClass = _generate_proxy_class(
            name, bases, nmspc
            )
        new_nmspc['__Proxy_Class__'] = ProxyClass

        # Define the new method
        @functools.wraps(ProxyClass.__init__)
        def new_meth(cls, *args, **kwargs):
            """Set a new object of the programmable tuple class"""
            # Initialize the proxy by user initializer
            proxy = ProxyClass(*args, **kwargs)
            # Make the actual programmable tuple from the proxy object
            return tuple.__new__(
                cls, (getattr(proxy, i, default_attr(i)) for i in fields)
                )

        # Register the new method
        new_nmspc['__new__'] = new_meth
        new_nmspc['__init__'] = _decorate_immutable_init(ProxyClass.__init__)

        # Utility methods
        # ---------------

        # Attribute access
        #
        # Generate a dictionary here and let the actual method access it in the
        # closure. Going to be used by several methods.
        attr_idxes = {
            name: idx for idx, name in enumerate(fields)
            }

        def getattr_meth(self, attr):
            """Gets the attribute of the given name"""
            try:
                return self[attr_idxes[attr]]
            except KeyError:
                raise KeyError(
                    'Invalid attribute %s' % attr
                    )

        # Register the attribute getter
        new_nmspc['__getattr__'] = getattr_meth

        # Update method
        def update_meth(self, **kwargs):
            """Updates defining attributes"""
            result = self.__class__(
                *(map(kwargs.pop, fields[0:defining_count], self))
                )
            if kwargs:
                raise ValueError(
                    'Got unexpected field names %r' % list(kwargs)
                    )
            return result

        new_nmspc['_update'] = update_meth

        # Replace method
        def replace_meth(self, **kwargs):
            """Simply replace a field in the programmable tuple"""
            result = tuple.__new__(
                self.__class__,
                map(kwargs.pop, fields, self)
                )
            if kwargs:
                raise ValueError(
                    'Got unexpected field names %r' % list(kwargs)
                    )
            return result

        new_nmspc['_replace'] = replace_meth

        # repr method
        def repr_meth(self):
            """Returns the nicely formmatted string"""
            return self.__class__.__name__ + '(' + (
                ', '.join(
                    '%s=%r' % (i, j)
                    for i, j in zip(fields[0:defining_count], self)
                    )
                ) + ')'

        if '__repr__' not in new_nmspc:
            new_nmspc['__repr__'] = repr_meth
        if '__str__' not in new_nmspc:
            new_nmspc['__str__'] = repr_meth

        # hash method
        if '__hash__' not in new_nmspc:
            new_nmspc['__hash__'] = lambda x: hash(
                (id(x.__class__), ) + x[0:defining_count]
                )

        # Better error for attempts to mutate
        def setattr_meth(self, attr, value):
            """Raises Attribute Error for attempts to mutate"""
            raise AttributeError(
                'Cannot mutate attributes of immutable objects'
                )

        new_nmspc['__setattr__'] = setattr_meth

        # Dictionary returning
        def asdict_meth(self, full=False, ordered=False):

            """Returns an dictionary which maps field names to values

            :param bool full: If the data fields are going to be contained as
                well, by default only the defining fields are contained.
            :param bool ordered: If OrderedDict or plain dictionary is going to
                be used for holding the return value. By default a plain
                dictionary is going to be used.

            """

            included_fields = fields if full else fields[0:defining_count]
            container = collections.OrderedDict if ordered else dict

            return container(
                zip(included_fields, self)
                )

        new_nmspc['_asdict'] = asdict_meth

        # Pickling support
        # ----------------

        new_nmspc['__getnewargs__'] = lambda self: self[0:defining_count]
        new_nmspc['__getstate__'] = lambda self: False
        new_nmspc['__setstate__'] = lambda self, state: False

        # Class generation
        # ----------------
        #
        # Set the base to tuple for the bottom classes in inheritance trees
        if len(bases) == 0:
            bases = (tuple, )

        # Return the new class
        return type.__new__(mcs, name, bases, new_nmspc)

    def __init__(cls, *args, **kwargs):
        super(ProgrammableTuple, cls).__init__(*args)


#
# The utility functions
# =====================
#

def _get_argnames(func):
    """Gets the names of the argument of a function"""
    return func.__code__.co_varnames[0:func.__code__.co_argcount]


def _determine_fields(bases, nmspc):

    """Determines the required fields for the new immutable classs

    :param tuple bases: The base classes of the new class
    :param dict nmspc: The name space dictionary for the new class
    :returns: The tuple of all the fields of the new class, and the number of
        defining fields.

    """

    # Get all the data fields
    #
    # It need to contain all the fields that the base classes have got.
    # Fields that are still defining fields are going to be removed later.
    fields = set()
    for base in bases:
        if isinstance(base, ProgrammableTuple):
            fields.update(base.__fields__)
        elif base == object:
            continue
        else:
            raise TypeError(
                'Type %s is not an immutable class' % base
                )
    # The new data fields that is added for this class
    if '__data_fields__' in nmspc:
        fields.update(nmspc['__data_fields__'])

    # Get all the defining fields
    try:
        init_meth = nmspc['__init__']
        init_argnames = _get_argnames(init_meth)
    except KeyError:
        raise ValueError('Initializer needs to be explicitly given.')
    except AttributeError:
        raise ValueError('Initializer needs to be a function.')
    defining_fields = init_argnames[1:]
    defining_count = len(defining_fields)

    # Assemble the list of all fields
    #
    # Remove the defining fields that is already added as data fields from
    # base classes.
    data_fields = tuple(fields.difference(defining_fields))
    # Assemble the tuple of all fields
    fields = defining_fields + data_fields

    return fields, defining_count


def _decorate_proxy_init(init):

    """Decorates the initialization function to be used for proxy class

    After the decoration, all the arguments will be assigned as attributes of
    ``self`` before the invocation of the actual initializer.

    """

    @functools.wraps(init)
    def decorated(self, *args, **kwargs):
        """The decorated initializer"""

        argnames = _get_argnames(init)

        for field, value in itertools.chain(
                zip(argnames[1:], args),
                kwargs.items()
                ):
            setattr(self, field, value)

        init(self, *args, **kwargs)

    return decorated


def _decorate_immutable_init(proxy_init):

    """Decorate the initialization function to be used for the immutable class

    To facilitate the calling of the initialization function of the base
    class, the initialization function is still put in the actual immutable
    class, although its actual function is already moved into the new method.
    In order to avoid it trying to taint the programmable tuple and causing
    error, this function can be used for wrapping an proxy initialization
    function into an function that can be safely set as the initializer for
    the immutable class without problem.

    :param proxy_init: The initializer for the proxy class
    :returns: The decorated initializer that can be set for programmable tuple
        classes

    """

    @functools.wraps(proxy_init)
    def decorared(self, *args, **kwargs):
        """The decorated initializer"""
        if isinstance(self.__class__, ProgrammableTuple):
            pass
        else:
            return proxy_init(self, *args, **kwargs)

    return decorared


def _generate_proxy_class(name, bases, orig_nmspc):

    """Generate a initialize proxy class for the programmable tuple

    The generated proxy class will have got all the behaviour of the new class
    and its base classes. Just it is a regular mutable class. Its instances
    can be used in the invocation of the initializer and act as the ``self``.
    Then the actual defining and data fields can be read from the proxy and
    set in the actual immutable class instance.

    :param str name: The name of the new named tuple class
    :param tuple bases: The basis of the new named tuple class
    :param orig_nmspc: The name space dictionary of the named tuple class
        before any twicking by this metaclass.

    """

    # The proxy class for each named tuple class will be stored in the
    # __Proxy_Class__ attribute by convention.
    proxy_bases = tuple(i.__Proxy_Class__ for i in bases)
    ProxyClass = type(
        '%sProxyClass' % name,
        proxy_bases if len(proxy_bases) >= 1 else (object, ),
        orig_nmspc
        )

    # Decorated initializer will set all the defining fields
    proxy_init_meth = _decorate_proxy_init(
        getattr(ProxyClass, '__init__')
        )
    setattr(ProxyClass, '__init__', proxy_init_meth)

    def proxy_super_meth(self):
        """Returns the super class of the Proxy class"""
        return super(ProxyClass, self)
    setattr(ProxyClass, 'super', proxy_super_meth)

    return ProxyClass
