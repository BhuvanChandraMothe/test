"""
Setup configuration for SAP OData Connector
"""
from setuptools import setup, find_packages
import os


# Read the long description from README
def read_long_description():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "SAP OData Connector - A powerful Python library for connecting to SAP OData services"

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name='covasant_sap_odata_connector',
    version='1.0.2',
    author='Covasant Technologies',
    author_email='info@covasant.com',  
    description='A powerful Python library for connecting to SAP OData services with OData V2 and V4 support',
    long_description=read_long_description(),
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['tests', 'examples', 'docs', 'demo_output*', 'logs', 'venv', 'test_*']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
        'bigquery': [
            'google-cloud-bigquery>=3.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'sap-odata-connector=covasant_odata.cli:main',  # Optional CLI entry point
        ],
    },
    include_package_data=True,
    package_data={
        'covasant_odata': ['config/*.yaml', 'config/*.json'],
    },
    keywords='sap odata connector api rest data integration etl',
    project_urls={
        
    },
)
