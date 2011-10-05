from setuptools import setup, find_packages


setup(
    name='test_project',
    description='A test project',
    long_description='foo bar baz',
    classifiers=[],
    keywords='',
    author='None McNone',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Django',
    ],
)
