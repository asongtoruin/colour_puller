from distutils.core import setup

setup(
    name='Colour Puller',
    version='0.1.0',
    description='Utilities for extracting colour palettes from Spotify album artwork',
    author='Adam Ruszkowski',
    packages=['colour_puller'],
    install_requires=[
        'numpy',
        'pillow',
        'scipy',
        'scikit-learn'
    ]
)