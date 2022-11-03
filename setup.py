import setuptools

reqs = ['six', 'grpcio==1.37.1', 'grpcio-tools==1.37.1', 'pyyaml', 'paramiko', 'scp']
setuptools.setup(install_requires=reqs)