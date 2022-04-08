from distutils.core import setup

setup(
    name="avt_fresh",
    author="Zev Averbach",
    author_email="zev@averba.ch",
    version="0.0.3",
    license="MIT",
    python_requires=">3.10.0",
    keywords='freshbooks API',
    install_requires=[
      'requests',
      'python-dotenv',
    ],
    packages=[
        "avt_fresh",
    ],
)
