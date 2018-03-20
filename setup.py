from distutils.core import setup

setup(
    name='autoscorum',
    version='0.0.1',
    packages=['autoscorum', 'scorum', 'scorumbase'],
    long_description=open('README.md').read(),
    entry_points={
          'console_scripts': [
              'wallet_app = app.wallet_app:main'
          ]
      },
)
