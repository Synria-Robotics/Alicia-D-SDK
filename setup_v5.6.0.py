#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alicia-D SDK v5.6.0 Setup Script

重构后的机械臂SDK安装脚本
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README_V5.6.0.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Alicia-D机械臂SDK v5.6.0 - 重构版本"

# 读取requirements文件
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [
        'numpy>=1.19.0',
        'scipy>=1.7.0',
        'pyserial>=3.5',
        'matplotlib>=3.3.0',
        'pydantic>=1.8.0'
    ]

setup(
    name="alicia-d-sdk-v5-6-0",
    version="5.6.0",
    author="Alicia-D Team",
    author_email="team@alicia-d.com",
    description="Alicia-D机械臂SDK v5.6.0 - 重构版本",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/alicia-d/sdk",
    project_urls={
        "Bug Tracker": "https://github.com/alicia-d/sdk/issues",
        "Documentation": "https://github.com/alicia-d/sdk/wiki",
        "Source Code": "https://github.com/alicia-d/sdk",
    },
    packages=find_packages(where="alicia_d_sdk_v5.6.0"),
    package_dir={"": "alicia_d_sdk_v5.6.0"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "mypy>=0.800",
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=0.5.0",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=0.5.0",
            "sphinx-autodoc-typehints>=1.12.0",
        ],
        "test": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
            "pytest-mock>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "alicia-d-demo=examples_v5.6.0.01_basic_usage:main",
            "alicia-d-advanced=examples_v5.6.0.02_advanced_control:main",
            "alicia-d-arch=examples_v5.6.0.03_architecture_demo:main",
        ],
    },
    keywords=[
        "robotics",
        "robot-arm",
        "motion-control",
        "trajectory-planning",
        "kinematics",
        "hardware-driver",
        "alicia-d",
        "mechanical-arm",
    ],
    include_package_data=True,
    zip_safe=False,
    platforms=["any"],
    license="MIT",
)