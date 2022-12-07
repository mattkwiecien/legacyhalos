#!/usr/bin/env python

# Supports:
# - python setup.py install
# - python setup.py test
#
# Does not support:
# - python setup.py version

import os, glob
from setuptools import setup, find_packages

def _get_version():
    import subprocess
    version = subprocess.check_output('git rev-parse HEAD', shell=True)
    version = version.decode('utf-8').replace('\n', '')
    return version

# Get the SHA of the current commit as the "version"
version = _get_version()

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup_kwargs=dict(
    name='legacyhalos',
    url='https://github.com/moustakas/legacyhalos',
    # version=version,
    author='John Moustakas',
    author_email='jmoustakas@siena.edu',
    #packages=[],
    license=license,
    description='Stellar mass content of dark matter halos in DESI Legacy Surveys imaging.',
    long_description=readme,
)

# /Users/matt/opt/anaconda3/bin/python3.8 -c 
# '
# import io, os, sys, setuptools, tokenize; 
# sys.argv[0] = '"'"'/Users/matt/Repos/legacyhalos/setup.py'"'"'; 
# __file__='"'"'/Users/matt/Repos/legacyhalos/setup.py'"'"';
# f = getattr(tokenize, '"'"'open'"'"', open)(__file__) 
#     if os.path.exists(__file__) 
#     else io.StringIO('"'"'from setuptools import setup; setup()'"'"');
# code = f.read().replace('"'"'\r\n'"'"', '"'"'\n'"'"');
# f.close();
# exec(compile(code, __file__, '"'"'exec'"'"'))'
# develop --no-deps

#- What to install
setup_kwargs['packages'] = find_packages('py')
setup_kwargs['package_dir'] = {'':'py'}

#- Treat everything in bin/ as a script to be installed
# This currently doesn't work as it attempts to install directory names rather than scri
# setup_kwargs['scripts'] = glob.glob(os.path.join('bin', '*'))

#- Data to include
# setup_kwargs['package_data'] = {
#     'legacyhalos': ['data/*',],
#     'legacyhalos.test': ['data/*',],
# }

#- Testing
setup_kwargs['test_suite'] = 'legacyhalos.test.test_suite'

#- Go!
setup(**setup_kwargs)
