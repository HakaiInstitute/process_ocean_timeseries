import pandas as pd
import xarray as xr


class server:
    def __init__(self, server):
        self.server = server


class query:
    def __init__(
        self,
        server,
        protocol,
        datasetID,
        format="csv",
        variables=None,
        constraints=None,
        groupby=None,
        agg=None,
        distinct=False,
    ):
        self.server = server
        self.protocol = protocol
        self.datasetID = datasetID
        self.output_format = format
        self.variables = variables
        self.constraints = constraints
        self.groupby = groupby
        self.agg = agg
        self.distinct = distinct

    def url(self, **kwargs):
        """Generate ERDDAP url query"""
        if kwargs:
            for key, value in kwargs.items():
                eval(f"self.{key}={value}")
        url = f"{self.server}/{self.protocol}/{self.datasetID}.{self.output_format}"

        # Generate filter parameters
        if self.variables:
            url += ",".join(self.variables)
        if self.filters:
            url += f"&{self.filters}"
        if self.agg and self.groupby:
            url += f"&order{self.agg}({','.join(self.groupby)})"
        if self.distinct:
            url += ["&distinct()"]
        return url

    def get_dataframe(self):
        url = self.query_url(output_format="csv")
        return pd.read_csv(url, skiprows=[2])

    def get_dataset(self):
        url = self.query_url(output_format="nc")
        return xr.open_dataset(url)

    def metadata(self):
        url = "{self.server}/info/{self.dataset_id}/index.csv"
        meta_table = pd.read_csv(
            url, index_col=["Row Type", "Variable Name", "Attribute Name"]
        )
        return {
            var: {attr: row["Value"] for attr, row in df_var.groupby(level=0)}
            for var, df_var in meta_table.loc["attribute"].groupby(level=0)
        }
