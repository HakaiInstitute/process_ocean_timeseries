"""
Module use to download data from Google Sheet and Files from Google drive links.
"""

from __future__ import print_function

import requests
import io

from tqdm import tqdm

import pandas as pd


def get_from_google_public(file_link, path=None, output="csv"):
    """Simple method to retrieve data from a public google link"""
    if file_link is None:
        return
    elif "spreadsheets" in file_link:
        # Modify file link to retrieve the csv format
        output_extension = "export?format={0}".format(output)
        file_id = file_link.rsplit("/edit", 1)
        if len(file_id) < 2:
            raise RuntimeError("Can" "t recognize the provided link")

        response_spreadsheet = requests.get(
            "{0}/{1}".format(file_id[0], output_extension)
        )
        if output == "csv":
            csv_data = io.StringIO(response_spreadsheet.content.decode("utf-8"))
            return pd.read_csv(csv_data)

        elif output == "xlsx":
            raise RuntimeError("not compatible yet with this format")

    elif "drive" in file_link:

        def download_file_from_google_drive(google_id, destination):
            """Download file from Google Drive with a Public ID"""
            URL = "https://docs.google.com/uc?export=download"

            session = requests.Session()

            response = session.get(URL, params={"id": google_id}, stream=True)
            token = get_confirm_token(response)

            if token:
                params = {"id": google_id, "confirm": token}
                response = session.get(URL, params=params, stream=True)

            save_response_content(response, destination)

        def get_confirm_token(response):
            """Confirm file is available"""
            for key, value in response.cookies.items():
                if key.startswith("download_warning"):
                    return value

            return None

        def save_response_content(response, destination):
            """Method to download file"""
            CHUNK_SIZE = 32768

            with open(destination, "wb") as f:
                for chunk in tqdm(
                    response.iter_content(CHUNK_SIZE),
                    desc="Download {0}: ".format(destination),
                    unit="MB",
                    unit_scale=CHUNK_SIZE / 1024 / 1024,
                ):

                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

        if path:
            link_sections = file_link.rsplit("/", 2)

            if link_sections[-1].startswith("view"):
                download_file_from_google_drive(link_sections[1], path)
        else:
            raise RuntimeError("Please provide a path")
