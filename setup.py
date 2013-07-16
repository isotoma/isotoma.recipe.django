import os

from setuptools import setup, find_packages

version = '3.1.6'

def read_file(name):
    return open(os.path.join(os.path.dirname(__file__),
                             name)).read()

readme = read_file('README.rst')
changes = read_file('CHANGES.txt')

setup(name='isotoma.recipe.django',
      version=version,
      description="Buildout recipe for Django",
      long_description='\n\n'.join([readme, changes]),
      classifiers=[
        'Framework :: Buildout',
        'Framework :: Django',
        'Topic :: Software Development :: Build Tools',
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: BSD License',
        ],
      packages=find_packages(exclude=['ez_setup']),
      package_data = {'isotoma.recipe.django': ['templates/*.tmpl']},
      keywords='django buildout recipe isotoma',
      author='Tom Wardill',
      author_email='tom.wardill@isotoma.com',
      maintainer='Alex Holmes',
      maintainer_email='alex.holmes@isotoma.com',
      url='http://github.com/isotoma/isotoma.recipe.django',
      license='BSD',
      zip_safe=False,
      install_requires=[
        'zc.buildout',
        'zc.recipe.egg',
        'Django',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [zc.buildout]
      default = isotoma.recipe.django.recipe:Recipe
      """,
      )
