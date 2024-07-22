import collections
import json

from bs4 import BeautifulSoup
import requests

# Note: need this hack because BeautifulSoup doesn't work with Python 3.10+
# Discussion at
# https://stackoverflow.com/questions/69515086/error-attributeerror-collections-has-no-attribute-callable-using-beautifu
collections.Callable = collections.abc.Callable


def get_species_data():
    """
    Loads in audio "track" data from Macaulay Library (Ithaca) and puts it into
    an array.
    :return: Array of data describing each audio track available
    """
    # The webpage where the data is listed
    url = 'https://www.macaulaylibrary.org/guide-to-bird-sounds/track-list/'

    # Make request to the website
    print(f'Getting species data from url={url}')
    req = requests.get(url)

    # Parse the returned html
    soup = BeautifulSoup(req.text, 'html.parser')

    # Get the first table
    table = soup.find_all('table')[0]

    # Process each row, after the first header row, for that table
    rows = table.find_all('tr')
    rows_data = []
    for row in rows[1:]:
        row_data = {}

        cells = row.find_all('td')
        row_data['track'] = cells[0].text.strip()

        # For title trim off the end recording number and other cruft
        species = cells[1].text.strip()
        end = species.find(' 0')
        if end == -1:
            end = species.find(' 1')
        if end == -1:
            end = species.find(' 2')
        # Determine species name, and replace the weird apostrophe with a regular one
        row_data['species'] = species[0:end].replace("’", "'")
        row_data['callName'] = species

        row_data['scientificName'] = cells[2].text.strip()
        row_data['recordist'] = cells[3].text.strip()
        row_data['location'] = cells[4].text.strip()
        row_data['date'] = cells[5].text.strip()

        # If no link indicating catalog number then skip this row
        a = cells[6].find('a')
        if a is None:
            continue
        catalog_number = a.text.strip()
        row_data['catalogNumber'] = catalog_number

        # Store link to audio file
        number = catalog_number.lstrip('ML')
        row_data['audioUrl'] = f'https://cdn.download.ams.birds.cornell.edu/api/v2/asset/{number}/mp3'

        # Useful to include copyright info
        row_data['copyright'] = 'Cornell Lab Macaulay Library'

        rows_data.append(row_data)

    return rows_data


# Global cache
_species_dict_cache = None


def get_species_dictionary():
    """
    Data dictionary is keyed on species name and value is list of all the info for the species. Cached.
    :return: the data dictionary
    """
    # If already cached, return it
    global _species_dict_cache
    if _species_dict_cache is not None:
        print("Returning species dictionary from cache")
        return _species_dict_cache

    # Add each species data to the species dictionary
    print("Creating species dictionary...")
    species_dict = dict()
    for species_data in get_species_data():
        list_for_species = species_dict.get(species_data['species'])
        if list_for_species is None:
            list_for_species = []
            species_dict[species_data['species']] = list_for_species
        list_for_species.append(species_data)

    # Save in cache
    _species_dict_cache = species_dict

    return species_dict


# Global caches
_species_list_cache = None


def get_sorted_all_data_list():
    """
    Returns list of all species in alphabetical order. For each species there is a list of the calls. Caches the data.
    :return: list of all data, ordered alphabetically by species
    """
    # If already cached, return it
    global _species_list_cache
    if _species_list_cache is not None:
        print("Returning species list from cache")
        return _species_list_cache

    print("Determining species list...")
    species_dictionary = get_species_dictionary()
    keys_list = list(species_dictionary.keys())
    keys_list.sort()

    all_data_list = []
    for species in keys_list:
        all_data_list.append(species_dictionary.get(species))

    # Put in cache
    _species_list_cache = all_data_list

    return all_data_list


def get_species_list_json():
    """
    Returns JSON version of species list in alphabetical order.
    :return: species list
    """
    all_data_list = get_sorted_all_data_list()
    species_list = []
    for a_species in all_data_list:
        # Each a_species is a list of calls
        a_call_for_species = a_species[0]
        species_list.append(a_call_for_species['species'])

    return json.dumps(species_list, indent=4)


def get_all_data_json():
    """
    Returns all audio track data in json format
    :return: all data in json format
    """
    return json.dumps(get_sorted_all_data_list(), indent=4)


def get_audio_data_json(qs):
    """
    Gets audio data for specified species. If species not specified then returns
    data for all species.
    :param qs: query string info. The parameter is 's' for species
    :return: JSON data for the species specified
    """
    species_param = qs.get('s')

    # If species not specified return data for all species
    if species_param is None or len(species_param) == 0:
        return get_all_data_json()

    species_name = species_param[0]

    # Get object for specified species
    data_for_species = get_species_dictionary()[species_name]

    return json.dumps(data_for_species, indent=4)
