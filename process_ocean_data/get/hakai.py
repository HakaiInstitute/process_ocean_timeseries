from hakai_api import Client
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

data_type_to_endpoint_mapping = {
    "ctd_casts": "",
    "ctd_data": "",
    "stations": "",
    "nutrients": "",
    "chla": "",
    "hplc": "",
    "poms": "",
}


class query:
    def __init__(
        self,
        endpoint: str,
        limit: int = 20,
        constraints: Tuple(list, str) = None,
        variables: list = None,
        api_root: str = None,
        distinct: bool = False,
        sort: list = None,
        offset: int = None,
        page: int = None,
        count: bool = False,
        data_type: str = None,
    ):
        self.client = Client()
        self.api_root = api_root or self.client.api_root
        self.endpoint = endpoint
        self.limit = limit
        self.constraints = constraints
        self.variables = variables
        self.distinct = distinct
        self.sort = sort
        self.offset = offset
        self.page = page
        self.count = count
        if endpoint is None and data_type:
            if data_type in data_type_to_endpoint_mapping:
                self.endpoint = data_type_to_endpoint_mapping[
                    "data_type_to_endpoint_mapping"
                ]
            else:
                logger.error(
                    f"Unknown {data_type}, available data_types are {data_type_to_endpoint_mapping.keys()}"
                )

        return self

    def get_endpoint_from_data_type(self, data_type: str):
        if data_type in data_type_to_endpoint_mapping:
            self.endpoint = data_type_to_endpoint_mapping[
                "data_type_to_endpoint_mapping"
            ]
            return self
        logger.error(
            f"Unknown {data_type}, available data_types are {data_type_to_endpoint_mapping.keys()}"
        )

    def url(self, meta: bool = False):
        url = f"{self.api_root}/{self.endpoint}?limit={self.limit}"
        if self.constraints:
            if type(self.constraints) is list:
                url += "&" + "&".join(self.constraints)
            else:
                url += f"&{self.constraints}"
        if self.variables:
            url += "&fields=" + ",".join(self.variables)

        if meta:
            # Return only related variables metadata if meta is True
            return f"{url}&meta" if self.variables else f"{url}meta"

        if self.distinct:
            url += "&distinct"
        if self.sort:
            url += f"&sort={','.join(self.sort)}"
        if self.offset:
            url += f"&offset={self.offset}"
        if self.page:
            url += f"&page={self.page}"
        if self.count:
            url += "&count"
        return url.replace("?&", "?")

    def meta(self):
        return self.client.get(self.url(meta=True))

    def dataframe(self):
        response = self.client.get(self.url())
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        response.raise_for_status()
