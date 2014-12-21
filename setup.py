#!/usr/bin/env python

from setuptools import setup

setup(name='programmabletuple',
      version='0.2.0',
      description='Python metaclass for making named tuples with programmability',
      long_description=open('README.rst').read(),
      author='Tschijnmo TSCHAU',
      author_email='tschijnmotschau@gmail.com',
      url='https://github.com/tschijnmo/programmabletuple',
      license='MIT',
      packages=['programmabletuple', ],
      classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
     )

