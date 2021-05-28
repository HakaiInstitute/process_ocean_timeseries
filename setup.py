from setuptools import setup

setup(
    name="process_ocean_data",
    version="0.1.0",
    description="Package use to process and QC ocean data ",
    url="https://github.com/HakaiInstitute/process-ocean-timeseries",
    author="Jessy Barrette",
    author_email="jessy.barrette@hakai.org",
    license="MIT",
    packages=["process_ocean_data"],
    include_package_data=True,
    install_requires=[
        "numpy",
        "xarray",
        "requests",
        "pandas",
        "xmltodict",
        "tqdm",
        "pytz",
        "ioos_qc @ git+https://github.com/HakaiInstitute/ioos_qc.git@development",
        "seabird @ git+https://github.com/cioos-siooc/seabird.git@cioos_dev",
        "utm",
        "beautifulsoup4",
        "scipy",
        "matplotlib", 'plotly', 'ipywidgets',
        "NetCDF4", 'IPython'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    zip_safe=True,
)
