from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in onelead/__init__.py
from onelead import __version__ as version

setup(
	name="OneLead",
	version=version,
	description="Lead Capture from Various Sources like Google Ads, Meta(Facebook) Ads, etc.",
	author="RedSoft ERP",
	author_email="dev@redsoftware.in",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
)