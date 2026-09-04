#!/usr/bin/env python3
"""
Setup script for heybro CLI package.

This package provides AI-powered command-line assistant functionality
with support for multiple providers (OpenAI, AWS Bedrock, etc.).
"""

from setuptools import setup, find_packages
import os
import sys

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'readme.md'), encoding='utf-8') as f:
    long_description = f.read()

# Core dependencies
CORE_DEPENDENCIES = [
    'click>=8.0.0',
    'prompt-toolkit>=3.0.0',
    'boto3>=1.26.0',
    'openai>=1.0.0',
    'requests>=2.25.0',
    'colorama>=0.4.4',
    'packaging>=21.0',
    'mcp>=0.9.0',
]

# Development dependencies
DEV_DEPENDENCIES = [
    'pytest>=7.0.0',
    'pytest-cov>=4.0.0',
    'black>=22.0.0',
    'isort>=5.0.0',
    'flake8>=5.0.0',
    'pylint>=2.15.0',
    'mypy>=1.0.0',
    'build>=0.8.0',
    'twine>=4.0.0',
]

# Optional dependencies for specific features
AWS_DEPENDENCIES = [
    'boto3>=1.26.0',
    'awscli>=1.25.0',
]

OPENAI_DEPENDENCIES = [
    'openai>=1.0.0',
]

# All optional dependencies
ALL_DEPENDENCIES = DEV_DEPENDENCIES + AWS_DEPENDENCIES + OPENAI_DEPENDENCIES

setup(
    # Package metadata
    name='heybro',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='AI-powered command-line assistant with multi-provider support',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/heybro',
    license='MIT',
    
    # Package configuration
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    include_package_data=True,
    package_data={
        'heybro_app': ['bedrock_models.json'],
    },
    zip_safe=False,
    
    # Dependencies
    python_requires='>=3.8',
    install_requires=CORE_DEPENDENCIES,
    extras_require={
        'dev': DEV_DEPENDENCIES,
        'aws': AWS_DEPENDENCIES,
        'openai': OPENAI_DEPENDENCIES,
        'all': ALL_DEPENDENCIES,
    },
    
    # Entry points
    entry_points={
        'console_scripts': [
            'heybro=heybro_app.cli:main',
        ],
    },
    
    # Classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    
    # Keywords
    keywords='cli ai assistant openai aws bedrock mcp shell automation',
    
    # Project URLs
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/heybro/issues',
        'Source': 'https://github.com/yourusername/heybro',
        'Documentation': 'https://github.com/yourusername/heybro/blob/main/USER_GUIDE.md',
    },
)