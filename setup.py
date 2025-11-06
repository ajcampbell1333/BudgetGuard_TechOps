"""
Setup script for BudgetGuard TechOps
"""

from setuptools import setup, find_packages

setup(
    name="budgetguard-techops",
    version="0.1.0",
    description="BudgetGuard TechOps - NIM Deployment Automation Tool",
    author="BudgetGuard Team",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "boto3>=1.28.0",
        "azure-identity>=1.14.0",
        "azure-mgmt-containerinstance>=10.0.0",
        "azure-mgmt-containerservice>=27.0.0",
        "google-cloud-compute>=1.14.0",
        "google-cloud-container>=2.21.0",
        "google-cloud-billing>=1.11.0",
        "pyyaml>=6.0",
        "colorlog>=6.8.0",
    ],
    entry_points={
        "console_scripts": [
            "budgetguard-techops=budgetguard_techops:main",
        ],
    },
    python_requires=">=3.8",
)

