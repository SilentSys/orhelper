import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="orhelper",
    version="0.1.3",
    author="Andrei Popescu",
    author_email="Popescu.Andrei.David@gmail.com",
    description="OrHelper is a module which aims to facilitate interacting and scripting with OpenRocket from Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SilentSys/orhelper",
    packages=setuptools.find_packages(),
    install_requires=[
        "jpype1>=0.6.3",
        "numpy"
    ],
    python_requires='>=3.6',
)