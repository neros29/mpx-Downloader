from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mpx-downloader",
    version="1.0.0",
    author="neros29",
    description="An advanced, user-friendly wrapper for yt-dlp with smart features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/neros29/mpx-Downloader",
    py_modules=["download"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Sound/Audio",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mpx-downloader=download:main",
        ],
    },
    keywords="youtube downloader yt-dlp wrapper audio video mp3 mp4 mkv",
    project_urls={
        "Bug Reports": "https://github.com/neros29/mpx-Downloader/issues",
        "Source": "https://github.com/neros29/mpx-Downloader",
        "Documentation": "https://github.com/neros29/mpx-Downloader/wiki",
    },
)
