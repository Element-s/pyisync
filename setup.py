from setuptools import setup, find_packages

version = '0.5'

classifiers = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.4',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Software Development :: Libraries :: Python Modules',
    "Topic :: Communications :: File Sharing",
    'Topic :: System :: Archiving :: Backup',
    'Topic :: System :: Monitoring',
    ]
    
    
setup(name='pyisync',
      version=version,
      description="Real-time sync file tool by pyinotify+rsync",
      long_description="""pyisync is real-time sync files tool written in Python. It implements the client which watches 
      files changes and transfer changed files to server by rsync.""",
      classifiers=classifiers,
      keywords='inotify rsync real-time sync',
      author='Element-s',
      author_email='qxligleam@gmail.com',
      url='https://github.com/Element-s/pyisync',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'pyinotify'
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
