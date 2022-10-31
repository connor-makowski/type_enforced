from distutils.core import setup

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
  name = 'type_enforced',
  packages = ['type_enforced'],
  version = '0.0.14',
  license='MIT',
  description = 'A type enforcer for python type annotations',
  long_description=long_description,
  long_description_content_type='text/markdown',
  author = 'Connor Makowski',
  author_email = 'connor.m.makowski@gmail.com',
  url = 'https://github.com/connor-makowski/type_enforced',
  download_url = 'https://github.com/connor-makowski/type_enforced/dist/type_enforced-0.0.14.tar.gz',
  keywords = [],
  install_requires=[],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
  python_requires=">=3.6, <4",
)
