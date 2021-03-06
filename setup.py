from distutils.core import setup

setup(
    name="avt_fresh",
    author="Zev Averbach",
    author_email="zev@averba.ch",
    version="0.0.16",
    license="MIT",
    python_requires=">3.10.0",
    keywords="freshbooks API",
    url="https://github.com/zevaverbach/avt-fresh",
    install_requires=[
        "requests",
        "redis",
    ],
    packages=[
        "avt_fresh",
    ],
)
