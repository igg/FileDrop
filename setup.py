from setuptools import find_packages, setup

setup(
	name='filedrop',
	version='1.0.0',
	packages=find_packages(include=[
		'filedrop',
	]),

	include_package_data=True,
	zip_safe=False,
	install_requires=[
		'uwsgi',
		'flask',
		'boto3',
		'requests',
    ],
)