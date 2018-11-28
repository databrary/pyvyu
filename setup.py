import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='pyvyu',
    version='0.0.1',
    author='Datavyu',
    author_email='info@datavyu.org',
    description='Datavyu file parser',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/databrary/pyvyu',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent"
    ]
)
