﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Enphase-API <https://github.com/Matthew1471/Enphase-API>
# Copyright (C) 2023 Matthew1471!
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json     # This script makes heavy use of JSON parsing.
import os.path  # We check whether a file exists and manipulate filepaths.

# All the shared Enphase® functions are in these packages.
from enphase_api.cloud.authentication import Authentication
from enphase_api.local.gateway import Gateway

# Enable this mode to perform no actual requests.
test_only = True

def get_header_section(endpoint, file_depth=0):
    # Heading.
    result = '= ' + endpoint['name'] + '\n'

    # Table of Contents.
    result += ':toc: preamble\n'

    # Reference.
    result += 'Matthew1471 <https://github.com/matthew1471[@Matthew1471]>;\n\n'

    # Document Settings.
    result += '// Document Settings:\n\n'

    # Set the autogenerated seciond IDs to be the GitHub format, so links work across both platforms.
    result += '// Set the ID Prefix and ID Separators to be consistent with GitHub so links work irrespective of rendering platform. (https://docs.asciidoctor.org/asciidoc/latest/sections/id-prefix-and-separator/)\n'
    result += ':idprefix:\n'
    result += ':idseparator: -\n\n'

    # This project uses JSON5 code highlighting by default.
    result += '// Any code blocks will be in JSON5 by default.\n'
    result += ':source-language: json5\n\n'

    # This will convert the admonitions to be icons rather than text (both on GitHub and outside of it).
    result += 'ifndef::env-github[:icons: font]\n\n'

    result += '// Set the admonitions to have icons (Github Emojis) if rendered on GitHub (https://blog.mrhaki.com/2016/06/awesome-asciidoctor-using-admonition.html).\n'
    result += 'ifdef::env-github[]\n'
    result += ':status:\n'
    result += ':caution-caption: :fire:\n'
    result += ':important-caption: :exclamation:\n'
    result += ':note-caption: :paperclip:\n'
    result += ':tip-caption: :bulb:\n'
    result += ':warning-caption: :warning:\n'
    result += 'endif::[]\n\n'

    # The document's metadata.
    result += '// Document Variables:\n'
    result += ':release-version: 1.0\n'
    result += ':url-org: https://github.com/Matthew1471\n'
    result += ':url-repo: {url-org}/Enphase-API\n'
    result += ':url-contributors: {url-repo}/graphs/contributors\n\n'

    # Page Description.
    result += endpoint['description']['long'] + '\n'

    # Heading.
    result += '\n== Introduction\n\n'

    # Introduction.
    result += 'Enphase-API is an unofficial project providing an API wrapper and the documentation for Enphase(R)\'s products and services.\n\n'

    result += 'More details on the project are available from the link:' + ('../' * (file_depth + 1)) + 'README.adoc[project\'s homepage].\n'

    return result

def get_request_section(request_json, auth_required=False, file_depth=0):
    # Heading.
    result = '\n== Request\n\n'

    # Some IQ Gateway API requests now require authorisation.
    if auth_required:
        result += 'As of recent Gateway software versions this request requires a valid `sessionid` cookie obtained by link:' + ('../' * file_depth) + 'Auth/Check_JWT.adoc[Auth/Check_JWT].\n'

    # Sub Heading.
    result += '\n=== Request Querystring\n\n'

    # Table Header.
    result += '[cols="1,1,1,2", options="header"]\n'
    result += '|===\n'
    result += '|Name\n'
    result += '|Type\n'
    result += '|Values\n'
    result += '|Description\n\n'

    # Table Rows.
    for query_item in request_json:
        # Name (and whether it is optional).
        result += '|`' + query_item['name'] + '` ' + ('(Optional)' if 'optional' in query_item and query_item['optional'] else '') + '\n'

        # Type.
        result += '|' + query_item['type'] + '\n'

        # Value (or Type if not known) and a suggested option.
        result += '|' + (query_item['value'] if 'value' in query_item else query_item['type'])
        if query_item['type'] == 'Boolean': result += ' (e.g. `0` or `1`)'
        result += '\n'

        # Description.
        result += '|' + query_item['description'] + '\n\n'

    # End of Table.
    result += '|===\n'

    return result

def get_type_string(json_value):
    if isinstance(json_value, (int, float)):
        return 'Number'
    elif isinstance(json_value, bool):
        return 'Boolean'
    elif isinstance(json_value, str):
        return 'String'
    elif json_value is None:
        return 'Null'
    else:
        return 'Unknown'

def get_schema(json_object, table_name='.', field_map=None):
    # The fields in the current table.
    current_table_fields = {}

    # Store any discovered nested tables in this dictionary.
    child_tables = {}

    # A field_map contains all the table meta-data both static and dynamic.
    if field_map:
        # Does this table already exist in the field map? Get a reference to just this table's field_map outside the loop.
        current_table_field_map = field_map.get(table_name)

    # Take each key and value of the current table.
    for json_key, json_value in json_object.items():

        # Is this itself another object?
        if isinstance(json_value, dict):
            # Get a sensible name for this nested table (that preserves its scope).
            child_table_name = (table_name + '.' if len(table_name) > 0 and table_name != '.' else '') + json_key.capitalize()

            # Add the schema of this nested table to child_tables.
            child_tables[child_table_name] = get_schema(json_object=json_value, table_name=child_table_name, field_map=field_map)

            # Add the type of this key.
            current_table_fields[json_key] = {'type':'Object', 'value':'`' + child_table_name + '`'}

        # Is this a list of values?
        elif isinstance(json_value, list):

            # Are there any values and is the first value an object?
            if len(json_value) > 0 and isinstance(json_value[0], dict):

                # We can override some object names (and merge metadata).
                if current_table_field_map and (value_name := current_table_field_map.get(json_key).get('value_name')):
                    # This name has been overridden.
                    child_table_name = value_name
                else:
                    # Get a sensible default name for this nested table (that preserves its JSON scope).
                    child_table_name = (table_name + '.' if len(table_name) and table_name != '.' else '') + json_key.capitalize()

                # Take each of the items in the list and combine all the keys and their metadata.
                new_list_items = {}
                for list_item in json_value:
                    new_list_items.update(get_schema(json_object=list_item, table_name=child_table_name, field_map=field_map)[child_table_name])

                # If this has been mapped/merged to a duplicate table name then we will need to append the existing dictionary.
                if child_table_name in child_tables:
                    # Get a reference to the existing list items.
                    old_list_items = child_tables[child_table_name]
                else:
                    old_list_items = None

                # Take each of the new list item keys.
                for new_list_item_key, new_list_item_value in new_list_items.items():
                    # Is this new key not present in all of the new items or not present in the old list of item keys (if applicable)?
                    if any(new_list_item_key not in item for item in json_value) or (old_list_items and new_list_item_key not in old_list_items):
                        # Mark this new key as optional.
                        new_list_item_value['optional'] = True

                # If this has been mapped to a duplicate then we will need to append the existing dictionary.
                if old_list_items:
                    # Take all the old list item keys.
                    for old_list_item_key, old_list_item_value in old_list_items.items():
                        # Is this old key not present in all of the new items?
                        if any(old_list_item_key not in item for item in json_value):
                            # Mark this old key as optional.
                            old_list_item_value['optional'] = True

                    # Get the existing dictionary.
                    child_tables[child_table_name].update(new_list_items)
                else:
                    # Add the schema of this list of nested tables to child_tables.
                    child_tables[child_table_name] = new_list_items

                # Add the type of this key.
                current_table_fields[json_key] = {'type':'Array(Object)', 'value':'Array of `' + child_table_name + '`'}

            # This is just an array of standard JSON types.
            else:
                # Add the type of this key.
                current_table_fields[json_key] = {'type':'Array(' + get_type_string(json_value) + ')', 'value': 'Array of ' + get_type_string(json_value)}

        # This is just a standard JSON type.
        else:
            # Add the type of this key.
            current_table_fields[json_key] = {'type':get_type_string(json_value)}

    # Prepend this parent table (all its fields have been explored for nested objects).
    tables = {}
    tables[table_name] = current_table_fields
    tables.update(child_tables)

    return tables

def get_table_and_types_section(table_name, table, type_map):
    # Heading.
    result = '\n=== ' + ('`' + table_name + '` Object' if len(table_name) > 0 and table_name != '.' else 'Root') + '\n\n'

    # Table Header.
    result += '[cols=\"1,1,1,2\", options=\"header\"]\n'
    result += '|===\n'
    result += '|Name\n'
    result += '|Type\n'
    result += '|Values\n'
    result += '|Description\n\n'

    # Any used custom types are collected then output after the table.
    used_custom_types = set()

    # Table Rows.
    for field_name, field_metadata in table.items():
        # Field Name.
        result += '|`' + field_name + '`' + (' (Optional)' if 'optional' in field_metadata and field_metadata['optional'] else '') + '\n'

        # Field Type.
        if isinstance(field_metadata, dict) and 'type' in field_metadata:
            field_type = (field_metadata['type'] if 'type' in field_metadata else 'Unknown')
        else:
            field_type = 'Unknown'
        result += '|' + field_type + '\n'

        # Field Value.
        result += '|'
        if isinstance(field_metadata, dict) and 'value' in field_metadata:
            result += field_metadata['value']
        else:
            # Did the user provide further details about this string field in the field map?
            if field_type == 'String' and (value_name := field_metadata.get('value_name')):
                result += '`' + value_name + '`'

                # Add an example value if available.
                if value_name in type_map and len(type_map[value_name]) > 0:
                    result += ' (e.g. `' + type_map[value_name][0]['value'] + '`)'
            
            else:
                result += field_type

                # Did the user provide further details about this number field in the field map?
                if field_type == 'Number' and field_metadata.get('allow_negative') == False: result += ' (> 0)'

        result += '\n'

        # Field Description. Did the user provide further details about this field in the field map?
        result += '|'

        # Is "Description" one of the things the user has declared.
        if 'description' in field_metadata:
            # Add the description.
            result += field_metadata['description']

            # Is this a string or array that has a custom type?
            if field_type == 'String' and (field_value_name:= field_metadata.get('value_name')):

                # Update the description to mark the type.
                result += ' In the format `' + field_value_name + '`.'

                # Mark that we need to ouput this custom type after this table.
                used_custom_types.add(field_value_name)
        else:
            result += '???'

        result += '\n\n'

    # End of Table.
    result += '|===\n'

    # Output any used custom types.
    if type_map:
        for used_custom_type in used_custom_types:
            # Check the custom_type is defined.
            if custom_type := type_map.get(used_custom_type):
                # Type Heading.
                result += '\n=== `' + used_custom_type + '` Types\n\n'

                # Type Table Header.
                result += '[cols=\"1,1,2\", options=\"header\"]\n'
                result += '|===\n'
                result += '|Value\n'
                result += '|Name\n'
                result += '|Description\n\n'

                # Type Table Rows.
                for current_field in custom_type:                    
                    # Field Value.
                    result += '|`' + current_field['value'] + '`' + ('?' if 'uncertain' in current_field else '') + '\n'

                    # Field Name.
                    result += '|' + current_field['name'] + '\n'

                    # Field Description.
                    result += '|' + current_field['description'] + '\n\n'

                # End of Table.
                result += '|===\n'

    return result

def get_example_section(uri, example_item, json_object):
    # Heading.
    result = '\n\n=== ' + example_item['name'] + '\n\n'

    # Example.
    result += '.GET */' + uri + ('?' + example_item['uri'] if 'uri' in example_item else '') + '* Response\n'
    result += '[source,json5,subs="+quotes"]\n'
    result += '----\n'
    result += str(json_object) + '\n'
    result += '----'

    return result

# Inspired by https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries.
def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            # If a is a dictionary but b is a string then add the string to the dictionary as a description.
            elif isinstance(a[key], dict) and isinstance(b[key], str):
                a[key]['description'] = b[key]
            # If b is a dictionary but a is a string then add the string to the dictionary as a description.
            elif isinstance(b[key], dict) and isinstance(a[key], str):
                b[key]['description'] = a[key]
                a[key] = b[key]
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

def main():

    # Load credentials.
    with open('configuration/credentials_token.json', mode='r', encoding='utf-8') as json_file:
        credentials = json.load(json_file)

    # Do we have a valid JSON Web Token (JWT) to be able to use the service?
    if not test_only and not (credentials.get('token') or Authentication.check_token_valid(credentials['token'], credentials['gatewaySerialNumber'])):
        # It is not valid so clear it.
        raise ValueError('No or expired token.')

    # Did the user override the config or library default hostname to the Gateway?
    if credentials.get('host'):
        # Download and store the certificate from the gateway so all future requests are secure.
        if not os.path.exists('configuration/gateway.cer'): Gateway.trust_gateway(credentials['host'])

        # Get an instance of the Gateway API wrapper object (using the hostname specified in the config).
        gateway = Gateway(credentials['host'])
    else:
        # Download and store the certificate from the gateway so all future requests are secure.
        if not os.path.exists('configuration/gateway.cer'): Gateway.trust_gateway()

        # Get an instance of the Gateway API wrapper object (using the library default hostname).
        gateway = Gateway()

    # Are we able to login to the gateway?
    if test_only or gateway.login(credentials['token']):

        # Load endpoints.
        with open('resources/API_Details.json', mode='r', encoding='utf-8') as json_file:
            endpoint_metadata = json.load(json_file)

        # Only load one endpoint for now (this script is still being developed).
        if test_only:
            endpoint_metadata = [ endpoint_metadata['Production'] ]

        # Take each endpoint in the metadata.
        for endpoint in endpoint_metadata:

            # This script currently exclusively writes "IQ Gateway API" documents.
            endpoint['documentation'] = 'IQ Gateway API/' + endpoint['documentation']

            # Count how many sub-folders this file will be under.
            file_depth = endpoint['documentation'].count('/')

            # Add the documentation header.
            output = get_header_section(endpoint=endpoint, file_depth=file_depth)

            # Get a reference to the current endpoint's request details.
            endpoint_request = endpoint['request']

            # Does the endpoint support any request query strings?
            if 'query' in endpoint_request:
                output += get_request_section(endpoint_request['query'], auth_required=True, file_depth=file_depth-1)

            # Perform a GET request on the resource.
            #json_object = gateway.api_call('/' + endpoint_request['uri'])
            json_object = json.loads('{"production":[{"type":"inverters","activeCount":10,"readingTime":0,"wNow":0,"whLifetime":314441},{"type":"eim","activeCount":1,"measurementType":"production","readingTime":1676757919,"wNow":-0.0,"whLifetime":276144.03,"varhLeadLifetime":0.024,"varhLagLifetime":205023.785,"vahLifetime":458229.78,"rmsCurrent":0.763,"rmsVoltage":239.037,"reactPwr":175.992,"apprntPwr":182.823,"pwrFactor":0.0,"whToday":3694.0,"whLastSevenDays":49814.0,"vahToday":7451.0,"varhLeadToday":2.0,"varhLagToday":3909.0}],"consumption":[{"type":"eim","activeCount":1,"measurementType":"total-consumption","readingTime":1676757919,"wNow":370.516,"whLifetime":781493.591,"varhLeadLifetime":765078.737,"varhLagLifetime":205039.176,"vahLifetime":1254065.428,"rmsCurrent":4.567,"rmsVoltage":239.146,"reactPwr":-938.239,"apprntPwr":1092.2,"pwrFactor":0.34,"whToday":15261.591,"whLastSevenDays":101733.591,"vahToday":21683.428,"varhLeadToday":14879.737,"varhLagToday":3905.176},{"type":"eim","activeCount":1,"measurementType":"net-consumption","readingTime":1676757919,"wNow":370.516,"whLifetime":646231.428,"varhLeadLifetime":765078.713,"varhLagLifetime":15.391,"vahLifetime":1254065.428,"rmsCurrent":3.804,"rmsVoltage":239.255,"reactPwr":-762.247,"apprntPwr":908.029,"pwrFactor":0.41,"whToday":0,"whLastSevenDays":0,"vahToday":0,"varhLeadToday":0,"varhLagToday":0}],"storage":[{"type":"acb","activeCount":0,"readingTime":0,"wNow":0,"whNow":0,"state":"idle"}]}')

            # Get a reference to the current endpoint's response details.
            endpoint_response = endpoint['response']

            # Get the schema recursively (we can override some known types, provide known value criteria and descriptions using the field_map).
            json_schema = get_schema(json_object=json_object, field_map=endpoint_response.get('field_map'))

            # Merge the dictionaries with their nested values.
            endpoint_response['field_map'] = merge(json_schema, endpoint_response['field_map'])

            # Ouput all the response tables.
            output += '\n== Response\n'

            # Add each of the tables from the derived json_schema.
            for table_name, table in endpoint_response['field_map'].items():
                output += get_table_and_types_section(table_name=table_name, table=table, type_map=endpoint_response.get('type_map'))

            # Add the examples.
            output += '\n'
            output += '== Examples'

            count = 1
            for example_item in endpoint_request['examples']:
                # We skip calling the first example as this has already been queried above.
                if not test_only and count > 1:
                    json_object = gateway.api_call('/' + endpoint_request['uri'] + ('?' + example_item['uri'] if 'uri' in example_item else ''))

                # Take the obtained JSON as an example.
                output += get_example_section(uri=endpoint_request['uri'], example_item=example_item, json_object=json_object)

            # Generate a suitable filename to store our documentation in.
            filename = 'output/' + endpoint['documentation']

            # Create any required sub-directories.
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Write the output to the file.
            with open(filename, mode='w', encoding='utf-8') as text_file:
                text_file.write(output)

    else:
        # Let the user know why the program is exiting.
        raise ValueError('Unable to login to the gateway (bad, expired or missing token in credentials.json).')

# Launch the main method if invoked directly.
if __name__ == '__main__':
    main()