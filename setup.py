import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.md', encoding="utf-8") as f:
    _readme = f.read()

_mydir = os.path.abspath(os.path.dirname(sys.argv[0]))
_requires = [ r for r in open(os.path.sep.join((_mydir,'requirements.txt')), "r").read().split('\n') if len(r)>1 ]

setup(
    name='himl',
    version="0.7.0",
    description='A hierarchical config using yaml',
    long_description=_readme + '\n\n',
    long_description_content_type='text/markdown',
    url='https://github.com/adobe/himl',
    author='Adobe',
    author_email='noreply@adobe.com',
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    license='Apache2',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    packages=['himl'],
    include_package_data=True,
    install_requires=_requires,
    entry_points={
        'console_scripts': [
            'himl = himl.main:run',
            'himl-config-merger = himl.config_merger:run'
        ]
    }
)
