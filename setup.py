from setuptools import setup, find_packages

setup(
    name="process_ocean_data",
    version="0.1.0",
    description="Package use to process and QC ocean data ",
    url="https://github.com/HakaiInstitute/process-ocean-timeseries",
    author="Jessy Barrette",
    author_email="jessy.barrette@hakai.org",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy",
        "xarray",
        "requests",
        "pandas",
        "xmltodict",
        "tqdm",
        "pytz",
        "seabird @ git+https://github.com/cioos-siooc/seabird.git@cioos_dev",
        "utm",
        "beautifulsoup4",
        "matplotlib",
        "plotly",
        "ipywidgets",
        "NetCDF4",
        "IPython",
    ],
    extras={
        "processing": [
            "ioos_qc @ git+https://github.com/HakaiInstitute/ioos_qc.git@development"
        ],
        "adcp_processing": ["pycurrents_ADCP_processing"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    zip_safe=True,
)
