from setuptools import setup

setup(name='atomic-charge',
      version='0.2',
      description="Seeding-only BitTorrent Client",
      url="https://github.com/Janno/atomic-charge",
      long_description=open("README").read(),
      classifiers=[
          'Topic :: Communications :: File Sharing',
      ],
      py_modules=['atomic_charge'],
      install_requires=['bittorrent-bencode'],
)
