import pandas as pd
import re
import logging
import xarray as xr
import xmltodict
import json
import os

logger = logging.getLogger(__name__)
# TODO load reference json file
reference_vocabulary_path = os.path.join(os.path.dirname(__file__),'seabird_variable_attributes.json')
with open(reference_vocabulary_path) as f:
    seabird_variable_attributes = json.load(f)

def convert_to_netcdf_var_name(var_name):
    return var_name.replace('/','Per')

def add_seabird_vocabulary(variable_attributes):
    for var in variable_attributes.keys():
        if var in seabird_variable_attributes:
            variable_attributes[var].update(seabird_variable_attributes[var])
    return variable_attributes

def cnv(file_path, output='xarray'):
    with open(file_path) as f:
        header = parse_seabird_file_header(f)
        header['variables'] = add_seabird_vocabulary(header['variables'])
        df = pd.read_csv(f,delimiter='\s+',names=header['variables'].keys())

    header = generate_seabird_cf_history(header)

    if output == 'dataframe':
        return df, header
    return convert_sbe_dataframe_to_dataset(df,header)

def btl(file_path,output='xarray'):
    with open(file_path) as f:
        header = parse_seabird_file_header(f)
        header['variables'] = add_seabird_vocabulary(header['variables'])
        # TODO parse column header with fix width
        # TODO parse data with fixed width method and separate statistical data
        df = pd.read_fwf(f,widths=[12,14]+ [10]*int(header['nquan']), names=header['variables'].keys())
    # TODO Split statistical data info separate dateframes

    # TODO Regroup dataframes by mathing nearest index prior
    if output == 'dataframe':
        return df, header
    return convert_sbe_dataframe_to_dataset(df,header)
    

def convert_sbe_dataframe_to_dataset(df,header):
    # Convert column names to netcdf compatible format
    df.columns = [convert_to_netcdf_var_name(var) for var in df.columns]
    header['variables'] = {convert_to_netcdf_var_name(var): attrs for var, attrs in header['variables'].items()}
    ds = df.to_xarray()
    variable_attributes = header.pop('variables')
    for var,attrs in variable_attributes.items():
        ds[var].attrs = attrs 
    ds.attrs = header
    return ds


def parse_seabird_file_header(f):
    def unknown_line():
        logger.warning(f'Unknown line format: {line}')
    def standardize_attribute(attribute):
        return attribute.strip().replace(' ','_').lower()
    def read_comments(line):
        if re.match('\*\* .*(\:|\=).*',line):
            r = re.match('\*\* (?P<key>.*)(\:|\=)(?P<value>.*)',line)
            header[r['key'].strip()] = r['value'].strip() 
        else:
            header['comments'] += [line[2:]]

    def read_asterisk_line(line):
        if " = " in line:
             attr, value = line[2:].split('=',1)
             header[standardize_attribute(attr)] = value.strip()
        elif line.startswith('* Sea-Bird'):
            header['instrument_type'] += " " + re.search('\* Sea-Bird (.*) Data File\:',line)[1].strip()
        elif "Software version" in line:
            header['software_version'] = re.search('\* Software version (.*)',line)[1]
        else:
            unknown_line()

    def read_number_line(line):
        if line.startswith('# name'):
            attrs = re.search('\# name (?P<id>\d+) = (?P<sbe_variable>[^\s]+)\: (?P<long_name>.*)( \[(?P<units>.*)\](?P<comments>.*))*',line).groupdict()
            header['variables'][int(attrs['id'])] = attrs
        elif line.startswith('# span'):
            span = re.search('\# span (?P<id>\d+) = (?P<span>.*)',line)
            values = [float(value) if re.search('.|e',value) else int(value) for value in span['span'].split(',')]
            header['variables'][int(span['id'])].update({
                "value_min": values[0],
                "value_max": values[1]
            })
        elif " = " in line:
            attr, value = line[2:].split('=',1)
            header[standardize_attribute(attr)] = value.strip()
        else:
            unknown_line()
    line = ""
    header = {}
    header['variables'] = {}
    header['instrument_type'] = ""
    header['comments'] = []
    read_next_line = True
    while "*END*"  not in line:

        if read_next_line:
            line = f.readline()
        else:
            read_next_line = True

        # Ignore empty lines or last header line
        if re.match('^\*\s*$',line) or '*END*' in line:
            continue

        if re.match('(\*|\#)\s*\<',line):
            # Load XML header 
            # Retriveve the whole block of XML header
            xml_section = ""
            first_character = line[0]
            while re.match(f'\{first_character}\s*\<',line) or re.match(f'^\{first_character}\s*$',line) or line.startswith('** ') or line.startswith('* cast') or re.search('\>\s*$',line):
                if '**' in line:
                    read_comments(line)
                xml_section += line[1:]
                line = f.readline()
            read_next_line = False
            # Add section_name
            if first_character=='*':
                section_name ='data_xml'
            elif first_character=='#':
                section_name = 'instrument_xml'
            xml_dictionary = xmltodict.parse(f"<temp>{xml_section}</temp>")['temp']
            if section_name in header:
                header[section_name].update(xml_dictionary)
            else: 
                header[section_name] = xml_dictionary
            
            read_next_line = False
        elif line.startswith('** '):
            read_comments(line)
        elif line.startswith('* '):
            read_asterisk_line(line)            
        elif line.startswith('# '):
            read_number_line(line)
        else:
            unknown_line()
    # Remap variables to seabird variables
    variables = {attrs['sbe_variable']: attrs for key,attrs in header['variables'].items()}
    header['variables'] = variables
    return header
            
def generate_seabird_cf_history(attrs, drop_processing_attrs=False):
    sbe_processing_steps = ('datcnv',)
    history = []
    for step in sbe_processing_steps:
        step_attrs = {key.replace(step+'_',''): value for key,value in attrs.items()if key.startswith(step)}
        date_line = step_attrs.pop('date')
        date_str, extra = date_line.split(',',1)
        iso_date_str = pd.to_datetime(date_str).isoformat()
        if extra:
            extra = re.search('^\s(?P<software_version>[\d\.]+)\s*(?P<date_extra>.*)',extra)
            step_attrs.update(extra.groupdict()) 
        history += [f"{iso_date_str} - {step_attrs}"]
    # Sort history by date
    attrs['history'] = '\n'.join(sorted(history))

    # Drop processing attributes
    if drop_processing_attrs:
        drop_keys = [key for key in attrs.keys() if key.startswith(sbe_processing_steps)]
        for key in drop_keys:
            attrs.pop(key)
    
    return attrs
    
# TODO add console input
test_file_path = "/Users/jessybarrette/repo/process_ocean_timeseries/process_ocean_data/read/test/seabird/MI18MHDR.btl"
output = btl(test_file_path)
output