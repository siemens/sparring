#!env python
from distutils.core import setup
setup(name='sparring',
      author='Thomas Penteker',
      author_email='tek@serverop.de',
      version='0.0a',
      description='Network simulation for malware analysis',
      license='GPLv3',
      platforms='linux2',
      url='https://github.com/thomaspenteker/sparring',
      packages=['sparring','sparring.applications', 'sparring.lib', 'sparring.transports', 'sparring.utils'],
      package_dir={'sparring': 'sparring',
                   'sparring.applications': 'sparring/applications',
                   'sparring.transports': 'sparring/transports',
                   'sparring.utils': 'sparring/utils',
                   'sparring.lib': 'sparring/lib'},
      data_files=[('/usr/share/sparring', ['sparring/scripts/transparent.sh']),
                  ('/usr/share/sparring', ['sparring/scripts/halffull.sh'])],

)
