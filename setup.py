from setuptools import setup, find_packages

setup(
    name="investing-agent",
    version="0.1.0",
    packages=find_packages(include=['investing_agent*']),
    python_requires=">=3.10",
)