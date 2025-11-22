from setuptools import setup

# The information here can also be placed in setup.cfg - better separation of
# logic and declaration, and simpler if you include description/version in a file.
setup(
    name="Matrix Python Example Adapter",
    version="0.0.1",
    author="Leonne Snel & co",
    author_email="leonne.snel@gmail.com",
    description="Axini AMP Plugin Adapter for matrix text message service",
    package_dir={"": "src"},
    python_requires='>=3.10',
)
