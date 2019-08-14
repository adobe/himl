from setuptools import setup
from hierarchical_yaml.__version__ import __version__


setup(
    name='hierarchical-yaml',
    version=__version__,
    description='A hierarchical config using yaml in Python',
    long_description=__doc__,
    long_description_content_type='text/markdown',
    url='https://github.com/adobe/hierarchical-yaml',
    author='Adobe',
    author_email='',
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
    packages=['hierarchical_yaml'],
    include_package_data=True,
    install_requires=[
        'pathlib2',
        'deepmerge',
        'lru_cache',
        'pyyaml',
        'backports.functools_lru_cache',
        'boto3'],
    entry_points={}
)
