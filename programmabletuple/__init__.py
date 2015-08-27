"""
==================
Programmable tuple
==================

"""


import functools
import itertools
import collections


#
# The metaclass
# =============
#
# The public metaclass
# --------------------
#


class ProgrammableTupleMeta(type):

    """Programmable tuple metaclass

    This is the meta-class for programmable tuple classes. The basic idea of
    the implementation is that for each programmable tuple class, a mutable
    proxy class is generated that imitates its behaviour as much as possible.
    The actual initializer will be invoked with objects of this proxy class
    as ``self``. Then after the user-defined initialization, the values for
    the various fields are read from this proxy object and set into the
    actual programmable tuple. In this meta-class, the core functionality of
    defining the proxy class and wrapping the user-defined init function is
    performed. The definition of utility methods are in the mixin class
    :py:class:`_UtilMethodsMixin` definition.

    """

    def __new__(mcs, name, bases, nmspc, auto_defining=False):
        """Generates a new type instance for programmable tuple class"""

        # Make a shallow copy of the original namespace. This new copy can be
        # used for the new programmable tuple class, while the original copy
        # is going to be given to the proxy class.
        new_nmspc = dict(nmspc)

        # Fields determination.
        fields, defining_count = _determine_fields(bases, new_nmspc)

        # Prepare the proxy class for initialization.
        proxy_class = _form_proxy_class(name, bases, nmspc, auto_defining)

        # Patch the initialization methods.
        new_nmspc['__new__'] = _form_new_method(proxy_class)
        new_nmspc['__init__'] = _form_init_method(proxy_class.__init__)

        # Set empty slots for tuple subclasses, since all the information is
        # going to be handled by the tuple. Or we need a slot for the actual
        # content.
        if any(issubclass(i, tuple) for i in bases):
            slots = []
        else:
            slots = ['__content__']
        new_nmspc['__slots__'] = slots

        # Initialize the programmable tuple class.
        cls = type.__new__(mcs, name, bases, new_nmspc)

        # Update some fields in the new class, since they are going to be used.
        cls.__fields__ = fields
        cls.__defining_count__ = defining_count
        cls.__Proxy_Class__ = proxy_class

        # Return the new class
        return cls

    def __init__(cls, *args, **_):
        """Initializer

        It just calls the initializer in the base class with all keyword
        arguments dropped.
        """

        super().__init__(*args)


#
# The private functions
# ---------------------
#
# Fields determination
# ^^^^^^^^^^^^^^^^^^^^
#


def _determine_fields(bases, nmspc):
    """Determines the fields for the new programmable tuple

    :param tuple bases: The base classes of the new class
    :param dict nmspc: The name space dictionary for the new class
    :returns: The ordered dictionary of all the fields of the new class, field
        names as keys and the location as values. The order is consistent
        with the order of the fields. And the number of defining fields.
    """

    # Get all the data fields
    #
    # It need to contain all the fields that the base classes have got.
    # Fields that are still defining fields are going to be removed later.
    fields = set()
    for base in _gen_programmable_tuple_bases(bases):
        fields.update(base.__fields__)
        continue

    # The new data fields that is added for this class
    if '__data_fields__' in nmspc:
        fields.update(nmspc['__data_fields__'])

    # Get all the defining fields
    try:
        init_meth = nmspc['__init__']
        init_argnames = _get_argnames(init_meth)
    except KeyError:
        defining_fields = []
        defining_count = 0
    except AttributeError:
        raise ValueError('Initializer needs to be a function.')
    else:
        defining_fields = init_argnames[1:]
        defining_count = len(defining_fields)

    # Remove the defining fields that is already added as data fields from
    # base classes.
    data_fields = sorted(fields.difference(defining_fields))

    # Assemble the ordered dictionary of all fields
    fields = collections.OrderedDict()
    for idx, fn in enumerate(itertools.chain(defining_fields, data_fields)):
        fields[fn] = idx
        continue

    return fields, defining_count


#
# Proxy class formation
# ^^^^^^^^^^^^^^^^^^^^^
#


def _form_proxy_class(name, bases, orig_nmspc, auto_defining):
    """Forms a proxy class for initializing programmable tuple

    The generated proxy class will have got all the behaviour of the new
    class and its base classes. Just it is a regular mutable class. Its
    instances can be used in the invocation of the initializer and act as the
    ``self``. Then the actual defining and data fields can be read from the
    proxy object and set in the actual immutable class instance.

    :param str name: The name of the new named tuple class
    :param tuple bases: The basis of the new named tuple class
    :param dict orig_nmspc: The name space dictionary of the named tuple class
        before any tweaking by the programmable tuple metaclass.
    :param bool auto_defining: If the defining attributes are going to be
        automatically assigned.
    """

    # Retrieve the proxy classes for the base classes.
    proxy_bases = tuple(
        i.__Proxy_Class__ for i in _gen_programmable_tuple_bases(bases)
    )

    # Derive the new proxy class from the proxy classes of the bases.
    proxy_class = type(
        '{}ProxyClass'.format(name),
        proxy_bases if len(proxy_bases) > 0 else (object, ),
        orig_nmspc
    )

    # Decorate the initializer if automatic assignment of defining class is
    # requested.
    if auto_defining:
        proxy_class.__init__ = _add_auto_defining(proxy_class.__init__)

    # HACK: Patch a local version of the built-in super function so that any
    # calling with programmable tuple class will in fact be dispatched to the
    # corresponding proxy class. This should be fixed when ways to better
    # control the resolution of ``__class__`` cell is found.
    def patched_super(self, cls=proxy_class):
        """Patched super function for initialization"""
        if isinstance(cls, ProgrammableTupleMeta):
            cls = cls.__Proxy_Class__
        return super(cls, self)
    proxy_class.super = patched_super

    return proxy_class


def _add_auto_defining(init):
    """Decorates __init__ to assign defining fields automatically

    After the decoration, all the arguments will be assigned as attributes of
    ``self`` before the invocation of the actual initializer.
    """

    @functools.wraps(init)
    def decorated(self, *args, **kwargs):
        """The decorated initializer"""

        # Get the names of the defining fields.
        argnames = _get_argnames(init)

        # Assign all the values given to the initializer.
        for field, value in itertools.chain(
                zip(argnames[1:], args),
                kwargs.items()
        ):
            setattr(self, field, value)

        # Invoke the actual initializer.
        init(self, *args, **kwargs)

    return decorated


#
# Initialization methods patching
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#


def _form_new_method(proxy_class):
    """Forms the __new__ method for the class

    The function returned from this function, which should be used as the
    __new__ method of the programmable tuple class, will be the core of how
    the programmable tuples work. Basically a proxy object will be created to
    be initialized by the user-given initializer. Then the values of the
    fields are going to be read from the attributes of this proxy object to
    form the actual immutable object.

    """

    @functools.wraps(proxy_class.__init__)
    def new_meth(cls, *args, **kwargs):
        """Set a new object of the programmable tuple class"""

        # Initialize the proxy object by user-defined initializer.
        proxy = proxy_class(*args, **kwargs)

        # Get the values of all the fields.
        values = _get_field_values(
            cls.__fields__, lambda fn: getattr(proxy, fn), AttributeError
        )

        # Make the actual programmable tuple from the proxy object.
        return _make_programmable_tuple(cls, values)

    return new_meth


def _form_init_method(proxy_init):
    """Decorate the user-given initialization function

    Although the actual actions of the user-given initializer is moved to the
    initialization of the proxy object, we would still like to see the
    docstring for the initializer during development.

    More importantly, since the default Python ``super`` is slightly awkward
    to use inside the initializer, we want to be able to call the initializer
    of super class directly. So this function could decorate the given
    initializer into a version that is automatically disabled when called on
    a programmable tuple object.

    """

    @functools.wraps(proxy_init)
    def decorared(self, *args, **kwargs):
        """The decorated initializer"""
        if isinstance(type(self), ProgrammableTupleMeta):
            # When it is automatically called after the creation of a
            # programmable tuple, do nothing.
            pass
        else:
            # When it is probably called explicitly by a subclass
            # initializer, do the action.
            proxy_init(self, *args, **kwargs)

    return decorared


#
# Utilities
# ^^^^^^^^^
#


def _get_argnames(func):
    """Gets the names of the argument of a function"""
    return func.__code__.co_varnames[0:func.__code__.co_argcount]


def _gen_programmable_tuple_bases(raw_bases):
    """Generates the programmable tuple bases

    For subclassing programmable tuples, we need to read some information
    from only the bases which are programmable tuples themselves. This
    function will filter only the programmable tuple subclasses to read the
    information.
    """

    for base in raw_bases:
        if isinstance(base, ProgrammableTupleMeta):
            yield base
        continue

    return


#
# The base programmable tuple class
# =================================
#
# The base of the bases
# ---------------------
#


class _UtilMethodsMixin(object):

    """
    Mixin class for utility methods of programmable tuple base classes

    This class will define utility methods for working with programmable
    tuples. Most of the utility methods directly parallels those for the
    ``namedtuple`` class.

    This class is going to be mixed in into the two public base classes to
    provide the utilities.

    """

    __slots__ = []  # Disable dict.

    #
    # Attribute access
    #

    def __getattr__(self, attr):
        """Gets the attribute of the given name"""
        try:
            return self.__content__[self.__fields__[attr]]
        except KeyError:
            raise KeyError(
                'Invalid attribute {}'.format(attr)
            )

    def __setattr__(self, attr, value):
        """Raises Attribute Error for attempts to mutate"""
        if attr == '__content__':
            super().__setattr__(attr, value)
        else:
            raise AttributeError(
                'Cannot mutate attributes of programmable tuples'
            )

    #
    # Hashing and equality testing
    #

    def __hash__(self):
        """The default hash

        The tuple of the class and the defining fields values are going to be
        hashed.
        """

        return hash(
            (self.__class__, ) + self._defining_values
        )

    def __eq__(self, other):
        """Equality comparison

        Two programmable tuple objects are considered equal when

        1. They are of the same class.
        2. All of their defining fields have equal values.

        """

        return (
            self.__class__ == other.__class__ and
            self._defining_values == other._defining_values
        )

    #
    # Generation of objects of the same type
    #

    def _update(self, **kwargs):
        """Updates defining attributes

        A programmable tuple of the same class is going to be returned,
        just with the defining fields given in the keyword arguments replaced
        by their new given value. After the new values of the defining fields
        are formed, the initialization process will be performed.
        """

        # Make the updated result.
        result = type(self)(*(map(
            kwargs.pop,
            self._gen_defining_field_names(),
            self.__content__
        )))

        # Check for any unused invalid keyword arguments.
        if kwargs:
            raise ValueError(
                'Got unexpected field names {}'.format(list(kwargs.keys()))
            )

        return result

    def _replace(self, **kwargs):
        """Simply replace a field in the programmable tuple

        Different from the :py:meth:`_update` method, by using this method,
        the initialization process will **not** be performed and a new
        programmable tuple of the same class will be forcefully formed with
        the given fields replaced.
        """

        # Get the values of all the fields
        values_dict = {}
        for fn in self._gen_field_names():
            if fn in kwargs:
                val = kwargs.pop(fn)
            else:
                val = getattr(self, fn)
            values_dict[fn] = val
            continue
        if kwargs:
            raise ValueError(
                'Got unexpected field names {}'.format(list(kwargs.keys()))
            )

        # Make the result directly.
        result = self._make(**values_dict)
        return result

    @classmethod
    def _make(cls, **kwargs):
        """Makes a new programmable tuple object directly

        This method will bypass all the initialization process and make a
        programming tuple object according to the keyword arguments given.
        Note that **all** the fields should be present in the keyword
        arguments.

        :param kwargs: The values of all the fields, including defining and
            data fields.
        :returns: The programmable tuple object with the given fields.
        """

        # Try to get the values of all the fields.
        values = _get_field_values(cls.__fields__, kwargs.pop, KeyError)

        # Check the existance of any unused arguments.
        if len(kwargs) > 0:
            raise ValueError('Invalid field(s) {} for {}'.format(
                tuple(kwargs.keys()), cls.__name__
            ))

        # Make the programmable tuple.
        return _make_programmable_tuple(cls, values)

    #
    # Simple string formatting
    #

    def _format(self, children_fmt, include_fn):
        """Formats itself as a string

        This is an internal function going to be used by both the default
        ``__repr__`` and default ``__str__`` methods.

        :param str children_fmt: The format string for the children,
            the children needs to have a field name of ``val``.
        :param bool include_fn: if the field name is going to be included.
        :returns: A string formatted for the values of all the defining fields.
        """

        # Get the format for each of the children.
        if include_fn:
            full_children_fmt = '{fn}=' + children_fmt
        else:
            full_children_fmt = children_fmt

        # Format the children.
        children = ', '.join(
            full_children_fmt.format(fn=fn, val=val)
            for fn, val in zip(
                self._gen_defining_field_names(), self.__content__
            )
        )

        return '{}({})'.format(self.__class__.__name__, children)

    def __repr__(self, include_fn=True):
        """Returns the formatted string able to be evaluated"""
        return self._format(children_fmt='{val!r}', include_fn=include_fn)

    def __str__(self, include_fn=True):
        """Returns a nicely formatted string"""
        return self._format(children_fmt='{val!s}', include_fn=include_fn)

    #
    # Dictionary forming and parsing
    #

    def _asdict(self, full=False, class_tags=False):
        """Returns an dictionary which maps field names to values

        This method will convert a programmable tuple into a dictionary,
        with keys being the names of the fields and values being the
        corresponding value. For fields that are programmable tuple, they are
        going to be cast into dictionary recursively. In this way,
        this method can be used for serialization into JSON or YAML.

        :param bool full: If the data fields are going to be contained as
            well, by default only the defining fields are contained.
        :param Mapping class_tags: The mapping from class to a string,
            which is going to be assigned to the ``__class__`` attributes of
            the dictionaries. By default, the ``__class__`` attribute will
            not be added. But when it is added, it is required that the
            mapping contains all the classes that is needed.
        :returns: The dictionary for the current programmable tuple.
        """

        # Get the field names to be added to the dictionary.
        if full:
            included_fields = self._gen_field_names()
        else:
            included_fields = self._gen_defining_field_names()

        # Populate the dictionary.
        dict_ = {}
        for fn in included_fields:
            val = getattr(self, fn)
            if isinstance(type(val), ProgrammableTupleMeta):
                # Recurse for programmable tuple children.
                val = val._asdict(full=full, class_tags=class_tags)
            dict_[fn] = val
            continue

        # Add the class attribute.
        if class_tags:
            dict_['__class__'] = class_tags[type(self)]

        return dict_

    @classmethod
    def _load_from_dict(cls, dict_, full=False, class_tags=None,
                        top=True):
        """Loads a programmable tuple object from its dictionary form

        This method is the opposite of the method :py:meth:`_asdict`. It will
        also recursively resolve the nested dictionaries when they were in
        fact serialized from programmable tuples.

        :param dict dict_: The dictionary to load.
        :param bool full: If the data fields are going to be read and used as
            well. By default, the programmable tuple objects are going to be
            initialized from only the defining fields.
        :param Mapping class_tags: The mapping from class tags in the
            ``__class__`` string to the actual class.
        :param bool top: If we are at the top of the recursion tree.
        :returns: The programmable tuple from parsing the dictionary.
        """

        # Resolve the class of the current object.
        try:
            class_tag = dict_['__class__']
        except KeyError:
            # When the class tag is not given in the dictionary.
            if top:
                # Try to use the current class if we are at top.
                obj_class = cls
            else:
                # When we are not at the top, return a copy of the dictionary
                # directly.
                return dict(dict_)
        else:
            # When a class tag is given, try to resolve the class tag.
            if class_tag in class_tags:
                obj_class = class_tags[class_tag]
            else:
                raise ValueError(
                    'The class for tag {} cannot be resolved'.format(class_tag)
                )

        # Now we have the class, and next need to read the values of the
        # fields.
        if full:

            # When a full construction is to be performed, we need to get the
            # dictionary of all the fields.
            content = {}
            for i, v in dict_.items():
                # Skip the special class tag.
                if i == '__class__':
                    continue
                # Implicit else.
                if isinstance(v, dict):
                    # Recurse for dictionaries.
                    val = cls._load_from_dict(
                        v, full=True, class_tags=class_tags, top=False
                    )
                else:
                    val = v
                content[i] = val
                continue
            # Return the result.
            return obj_class._make(**content)

        else:

            # When we disable full loading, we only need to pick up the
            # values of the defining attributes.
            defining = {}
            for fn in obj_class._gen_defining_field_names():
                try:
                    val = dict_[fn]
                except KeyError:
                    raise ValueError((
                        'The definition property {} of class {} is '
                        'not given').format(fn, obj_class)
                    )
                if isinstance(val, dict):
                    val = cls._load_from_dict(
                        val, full=False, class_tags=class_tags, top=False
                    )
                defining[fn] = val
                continue
            # Return the result.
            return obj_class(**defining)

    #
    # Pickling support
    #

    def __getnewargs__(self):
        """Gets the arguments to be used for the new function"""
        return self._defining_values

    # Disable the getting and setting of states for pickling.
    __getstate__ = lambda _: False
    __setstate__ = lambda _, state_: False

    #
    # Utility methods
    #

    @classmethod
    def _gen_field_names(cls):
        """Gets an iterator of the field names of the class"""
        return cls.__fields__.keys()

    @classmethod
    def _gen_defining_field_names(cls):
        """The names of all the defining fields

        An iterator is going to be returned for names of all the defining
        names of the class.
        """
        return itertools.islice(
            cls.__fields__.keys(), 0, cls.__defining_count__
        )

    @property
    def _defining_values(self):
        """The values of the defining attributes

        A tuple for the values of the defining fields in order.
        """
        return tuple(
            self.__content__[0:self.__defining_count__]
        )


#
# Public base classes
# -------------------
#


class ProgrammableTuple(
    _UtilMethodsMixin, tuple, metaclass=ProgrammableTupleMeta
):
    """The programmable tuple base class

    This is an abstract base class for the programmable tuples. Users can
    just derive from this base class to make the class a programmable tuple
    class.

    """

    @property
    def __content__(self):
        """Return the content tuple

        This is to make the content tuple of both subclass of tuple and
        non-subclass of tuple able to be retrieved in a uniform fashion.
        """
        return self


class ProgrammableExpr(_UtilMethodsMixin, metaclass=ProgrammableTupleMeta):
    """The programmable expression base class

    This base class is similar to the :py:class:`ProgrammableTuple` class,
    just it is not a subclass of tuple. So it can be used when the desired
    data structure is not intended to behave like a tuple. The resulted class
    looks like expressions in the Wolfram language but with object-oriented
    programmability added.


    """

    pass


#
# The utility functions
# =====================
#
# These are utility functions useful for both the meta-class and the base
# class.
#


def _get_field_values(fields, query, non_exist_exc):
    """Gets the values of all the fields

    :param OrderedDict fields: The ordered dictionary for the fields.
    :param Callable query: A callable function going to be called with the
        field name to get the value.
    :param non_exist_exc: The exception class for failed field value query.
    :returns: A list of the values of all the fields in order.
    """

    values = []
    for i in fields.keys():
        try:
            values.append(query(i))
        except non_exist_exc:
            raise AttributeError(
                'Attribute {} is not set'.format(i)
            )
        continue

    return values


def _make_programmable_tuple(cls, data_values):
    """Makes a programmable tuple object

    This function will actually make a programmable tuple object of the given
    class according to the sequence of values for the fields. It is the
    function that is actually used to make the object during the
    initialization process. It can also be used for other purposes where we
    already got values of all the fields and the initialization process needs
    to be skipped.

    :param cls: The class of the programmable tuple.
    :param data_values: A sequence of values for all the fields of the
        programmable tuple.
    :returns: A value of the programmable tuple with the given data fields.
    """

    if issubclass(cls, tuple):
        # For subclass of tuples.
        #
        # Create the tuple.
        tp = tuple.__new__(cls, data_values)
    else:
        # For non-subclass of tuples.
        content = tuple(data_values)
        tp = object.__new__(cls)
        tp.__content__ = content

    return tp
