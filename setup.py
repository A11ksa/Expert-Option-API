from setuptools import setup, find_packages

# Read the README file for long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ExpertOptionsToolsV2",
    version="2.0.0",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    install_requires=[
        "websockets>=11.0.3",
        "pandas>=1.5.0",
        "rich>=13.0.0",  # Used in test1.py for colored console output
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "black>=24.0",
            "isort>=5.12",
        ]
    },
    author="Ahmed",
    author_email="ar123ksa@gmail.com",
    description="A Python library for interacting with the Expert Option trading platform via WebSocket API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/A11ksa/Expert-Option-API",
    project_urls={
        "Source": "https://github.com/A11ksa/Expert-Option-API",
        "Bug Tracker": "https://github.com/A11ksa/Expert-Option-API/issues",
        "Documentation": "https://github.com/A11ksa/Expert-Option-API/wiki",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Finance",
    ],
    python_requires=">=3.8",
    keywords="expertoption, trading, websocket, api, finance, binary-options",
    license="MIT",
)