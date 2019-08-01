from setuptools import setup

_name = 'multildap'

def readme():
    with open('README.md') as f:
        return f.read()

setup(name=_name,
      version='0.2-rc',
      zip_safe = False,
      description="LDAP client or proxy to multiple LDAP server",
      long_description=readme(),
      long_description_content_type="text/markdown",
      classifiers=['Development Status :: 5 - Production/Stable',
                  'License :: OSI Approved :: BSD License',
                  'Programming Language :: Python :: 2',
                  'Programming Language :: Python :: 3'],
      url='https://github.com/peppelinux/{}'.format(_name),
      author='Giuseppe De Marco',
      author_email='giuseppe.demarco@unical.it',
      license='BSD',
      scripts=['{}/multildapd.py'.format(_name)],
      packages=[_name],
      install_requires=['ldap3', 'gevent'],
     )
