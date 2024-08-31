from setuptools import setup, find_packages

with open("requirements.txt", encoding="utf_16") as f:
    required = f.read().splitlines()

setup(
    name = "edinet-explorer",
    version = "0.1.0",
    description = "A Python-based GUI application for data collection from EDINET",
    author = "Peijun Liu",
    author_email = "vincentlpj.ou@gmail.com",
    url = "https://github.com/vincent-lpj/edinet-explorer",
    packages = ["edinet_explorer"],
    install_requires = required,
    entry_points = {
        "console_scripts" : [
            'edinet-explorer=edinet_explorer.main:main'
        ],
    },
)