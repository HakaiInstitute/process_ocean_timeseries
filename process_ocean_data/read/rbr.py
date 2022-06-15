import pandas as pd
import re


def rtext(file_path, encoding="UTF-8", errors="ignore"):
    """
    Read RBR R-Text format.
    :param errors: default ignore
    :param encoding: default UTF-8
    :param file_path: path to file to read
    :return: metadata dictionary dataframe
    """
    # MON File Header end
    header_end = "NumberOfSamples"

    with open(file_path, encoding=encoding, errors=errors) as fid:
        line = ""
        section = "header_info"
        metadata = {section: {}}

        while not line.startswith(header_end):
            # Read line by line
            line = fid.readline()

            if re.match(r"\s*.*(=).*", line):
                key, item = re.split(r"\s*[:=]\s*", line, 1)

                # If line has key[index].subkey format
                if re.match(r".*\[\d+\]\..*", key):
                    items = re.search(r"(.*)\[(\d+)\]\.(.*)", key)
                    key = items[1]
                    index = items[2]
                    subkey = items[3].strip()

                    if key not in metadata:
                        metadata[key] = {}
                    if index not in metadata[key]:
                        metadata[key][index] = {}

                    metadata[key][index][subkey] = item.strip()

                else:
                    metadata[key] = item.strip()
            else:
                print(f"Ignored: {line}")
        # Read NumberOFSamples line
        metadata["NumberOfSamples"] = int(line.rsplit("=")[1])

        # Read data
        df = pd.read_csv(fid, sep="\s\s+", engine='python')

        # Make sure that line count is good
        if len(df) != metadata["NumberOfSamples"]:
            raise RuntimeError("Data length do not match expected Number of Samples")

        return df, metadata
