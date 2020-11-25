## Takes CHECKPOINT objects and converts them into Palo Objects as set config

import re
import pandas as pd
import numpy as np

FILENAME = "./preconverted/checkpoint_objects.csv"
TCP_OBJECTS = "./preconverted/tcp_objects.csv"
UDP_OBJECTS = "./preconverted/udp_objects.csv"

#REGEX CURRENTLY NOT USED.  HERE IN CASE REQUIRED LATER.
IPV4_REGEX = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'

class Objects():
    def __init__(self, FILENAME):
        self.subnet_masks = {
                '255.255.255.255': '/32',
                '255.255.255.254': '/31',
                '255.255.255.252': '/30',
                '255.255.255.248': '/29',
                '255.255.255.240': '/28',
                '255.255.255.224': '/27',
                '255.255.255.192': '/26',
                '255.255.255.128': '/25',
                '255.255.255.0': '/24',
                '255.255.254.0': '/23',
                '255.255.252.0': '/22',
                '255.255.248.0': '/21',
                '255.255.240.0': '/20',
                '255.255.224.0': '/19',
                '255.255.192.0': '/18',
                '255.255.128.0': '/17',
                '255.255.0.0': '/16',
                '255.254.0.0': '/15',
                '255.252.0.0': '/14',
                '255.248.0.0': '/13',
                '255.240.0.0': '/12',
                '255.224.0.0': '/11',
                '255.192.0.0': '/10',
                '255.128.0.0': '/9',
                '255.0.0.0': '/8',
            }
        self.df = pd.read_csv(FILENAME)
        self.udp_df = pd.read_csv(UDP_OBJECTS)
        self.tcp_df = pd.read_csv(TCP_OBJECTS)

class NetworkObjects(Objects):
    def __init__(self):
        super().__init__(FILENAME=FILENAME)
        self.host_objects = self.get_host_objects()
        self.network_objects = self.get_network_objects()
        self.tcp_objects = self.get_tcp_objects()
        self.udp_objects = self.get_udp_objects()
    
    def get_host_objects(self):
        network_df = self.filter_nan(self.df, 'IPv4', False)
        host_df = self.filter_nan(network_df, 'Mask', True)
        return host_df[['Name','IPv4']]

    def get_network_objects(self):
        network_df = self.filter_nan(self.df, 'IPv4', False)
        filtered_network_df = self.filter_nan(network_df, 'Mask', False)
        return filtered_network_df[['Name', 'IPv4', 'Mask']]

    def get_tcp_objects(self):
        tcp_df = self.filter_nan(self.tcp_df, 'Port', False)
        return tcp_df[['Name', 'Port']]

    def get_udp_objects(self):
        udp_df = self.filter_nan(self.udp_df, 'Port', False)
        return udp_df[['Name', 'Port']]

    def replace_whitespace(self, text):
        '''
        First strips any white space from the beginning and end of the string then replaces
        any spaces with _ 
        
        Used to format object names correctly.

        Takes one argument
        text: string
        '''
        return text.strip().replace(" ", "_")

    def filter_nan(self, data_frame, column, want_nan):
        '''Filters Pandas Data Frame on a specific column depending on whether the value is NaN.

        Returns a list of boolean values based upon whether you want only NaN or everything but NaN.
        The boolean list is used to filter the pandas dataframe.

        Takes three args

        data_frame: pandas.df
        column: string
        want_nan: boolean
        '''
        data = data_frame
        has_value = []
        for value in data_frame[column]:
            if value == '' or pd.isnull(value) or value == 'N/A':
                #IF Blank/NaN and you don't want NaN then append false.  If value then append true
                if want_nan:
                    has_value.append(True)
                else:
                    has_value.append(False)
            else:
                #If there is a value and you want Blank/NaN then append True to filter out rows with value.
                if want_nan:
                    has_value.append(False)
                else:
                    has_value.append(True)
        return data[has_value]

    def convert_cidr(self, mask):
        return self.subnet_masks[mask]

    def convert_host_objects(self):
        CONVERTED_FILENAME = "./converted/palo_host_objects.txt"
        with open(CONVERTED_FILENAME, 'w') as f:
            f.write('-----------------------Converted Host Objects ---------------------------\n\n')
        with open('./review/host_object_errors.txt', 'w') as f:
            f.write('-----------------------HOST OBJECT ERRORS -----------------------------\n\n')

        for index, row in self.host_objects.iterrows():
            name = row['Name']
            address = row['IPv4']
            mask = '/32'

            #Needed to filter data ranges.  Objects placed into seperate file for review.
            if len(address) > 20:
                with open('./review/host_object_errors.txt', 'a') as f:
                    f.write(f'{index}: {name} {address}\n\n')
                continue

            with open(CONVERTED_FILENAME, 'a') as f:
                f.write(f'set address {name} ip-netmask {address}{mask}\n')

    def convert_network_objects(self):
        CONVERTED_FILENAME = "./converted/palo_network_objects.txt"
        with open(CONVERTED_FILENAME, 'w') as f:
            f.write('-----------------------Converted Network Objects ---------------------------\n\n')
        with open('./review/network_object_errors.txt', 'w') as f:
            f.write('-----------------------NETWORK OBJECT ERRORS -----------------------------\n\n')

        for index, row in self.network_objects.iterrows():
            name = self.replace_whitespace(row['Name'])
            address = row['IPv4']
            cidr = self.convert_cidr(row['Mask'])

            #Needed to filter data ranges.  Objects placed into seperate file for review.
            if len(address) > 20:
                with open('./review/host_object_errors.txt', 'a') as f:
                    f.write(f'{index}: {name} {address}\n\n')
                continue

            with open(CONVERTED_FILENAME, 'a') as f:
                f.write(f'set address {name} ip-netmask {address}{cidr}\n')

    def convert_service_objects(self, protocol):
        '''
        For this function to work a CSV with a name and port column must live in ./preconverted/
        named {protocol}_objects.csv

        You pass which protocol you need converted.  From the checkpoint I exported only the specific 
        protocol as exporting them as a mass list did not include protocol information.

        This function takes one argument.  And uses the instanced df inhereted from Objects class.
        protocol: string
        '''
        CONVERTED_FILENAME = f'./converted/palo_{protocol}_objects.txt'
        with open(CONVERTED_FILENAME, 'w') as f:
            f.write(f'-----------------------Converted {protocol} Objects ---------------------------\n\n')
        with open('./review/tcp_object_errors.txt', 'w') as f:
            f.write(f'-----------------------NETWORK {protocol} ERRORS -----------------------------\n\n')

        if protocol == 'tcp':
            for index, row in self.tcp_objects.iterrows():
                name = self.replace_whitespace(row['Name'])
                port = row['Port']
                
                with open(CONVERTED_FILENAME, 'a') as f:
                    f.write(f'set service {name} protocol {protocol} port {port}\n')

        if protocol == 'udp':
            for index, row in self.udp_objects.iterrows():
                name = self.replace_whitespace(row['Name'])
                port = row['Port']
                
                with open(CONVERTED_FILENAME, 'a') as f:
                    f.write(f'set service {name} protocol {protocol} port {port}\n')


## Begin Execution Of Main Script
if __name__ == '__main__':
    net_objs = NetworkObjects()
    net_objs.convert_host_objects()
    net_objs.convert_network_objects()
    net_objs.convert_service_objects('tcp')
    net_objs.convert_service_objects('udp')