from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="micro_gst_assist",
    version="0.1.0",
    description="GST Compliance Automation for Micro-Enterprises (Sub-10-Employee)",
    author="Bizaxl",
    author_email="info@bizaxl.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
