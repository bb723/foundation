from setuptools import setup, find_packages

setup(
    name='foundation',
    version='0.1.0',
    description='Shared foundation package for PropertyOps applications',
    author='PropertyOps',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'foundation': [
            'templates/*.html',
            'static/css/*.css',
            'static/js/*.js',
        ],
    },
   install_requires=[
    'flask>=3.0.0',
    'requests>=2.32.0',
    'python-dateutil>=2.9.0',
    'pyjwt>=2.10.0',
    'cryptography>=44.0.0',
    'msal>=1.31.0',
    'azure-identity>=1.19.0',
    'intuit-oauth>=1.2.6',
    'snowflake-connector-python>=3.12.0',
    'pandas>=2.2.0',  # <-- ADD THIS LINE
],
    python_requires='>=3.10',
)
