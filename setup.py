import os
from setuptools import setup, find_packages
from typing import Optional

def _munge_req(r):
    for sym in ["~", "=", "<", ">", ",", "!", "!"]:
        r = r.split(sym)[0]
    return 

__version__: Optional[str] = None
pth = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "py/legacyhalos", "version.py"
)
with open(pth, "r") as fp:
    exec(fp.read())

pth = os.path.join(os.path.dirname(os.path.realpath(__file__)), "environment.yml")
rqs = []
with open(pth, "r") as fp:
    start = False
    for line in fp.readlines():
        if line.strip() == "dependencies:":
            start = False
        if start:
            if "- pip:" in line.strip():
                continue
            r = line.strip()[3:].strip()
            rqs.append(_munge_req(r))

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name="legacyhalos",
    url="https://github.com/moustakas/legacyhalos",
    version=__version__,
    description='Stellar mass content of dark matter halos in DESI Legacy Surveys imaging.',
    author='John Moustakas',
    author_email='jmoustakas@siena.edu',    
    packages=find_packages('py'),
    package_dir={'':'py'},
    include_package_data=True,
    scripts=[],
    install_requires=rqs,
    license=license,
    long_description=readme,
    test_suite='legacyhalos.test.test_suite'
)

#- Treat everything in bin/ as a script to be installed
# This currently doesn't work as it attempts to install directory names rather than scri
# setup_kwargs['scripts'] = glob.glob(os.path.join('bin', '*'))

#- Data to include
# setup_kwargs['package_data'] = {
#     'legacyhalos': ['data/*',],
#     'legacyhalos.test': ['data/*',],
# }
