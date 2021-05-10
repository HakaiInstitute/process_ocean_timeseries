import setuptools

setuptools.setup(
    name="process-ocean-data",
    version="0.1.0",
    description="Package use to process and QC ocean data ",
    packages=setuptools.find_packages(),
    install_requires=[
        "numpy",
        "xarray",
        "requests",
        "pandas",
        "rpy2",
        "xmltodict",
        "tqdm",
        "pytz",
        "ioos_qc",
        "seabird",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
