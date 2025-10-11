try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.md', encoding="utf-8") as f:
    _readme = f.read()

_install_requires = [
    'deepmerge==1.1.1',
    'lru_cache==0.2.3',
    'backports.functools_lru_cache==2.0.0',
    'pathlib2==2.3.7',
    'pyyaml==6.0.2',
]

_extras_require = {
    's3': [
        'boto3==1.34.6',
    ],
    'vault': [
        'hvac==1.2.1',
    ],
}
_extras_require['all'] = [dep for deps in _extras_require.values() for dep in deps]

setup(
    name='himl',
    version="0.16.4",
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    packages=['himl'],
    include_package_data=True,
    install_requires=_install_requires,
    extras_require=_extras_require,
    entry_points={
        'console_scripts': [
            'himl = himl.main:run',
            'himl-config-merger = himl.config_merger:run'
        ]
    }
)
