import collections
import json
from types import SimpleNamespace

import queryGoogle
from bs4 import BeautifulSoup
import requests

import cache

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


def get_species_dictionary():
    """
    Data dictionary is keyed on species name and value is list of all the info for the species.
    Not cached since the calling methods cache it. But I'm not confident this is truly the best
    thing to do.
    :return: the data dictionary
    """
    # Add each species data to the species dictionary
    print("Creating species dictionary...")
    species_dict = dict()
    for species_data in get_species_data():
        list_for_species = species_dict.get(species_data['species'])
        if list_for_species is None:
            list_for_species = []
            species_dict[species_data['species']] = list_for_species
        list_for_species.append(species_data)

    return species_dict


def get_sorted_all_data_list():
    """
    Returns list of all species in alphabetical order. For each species there is a list of the calls. Caches the data.
    :return: list of all data, ordered alphabetically by species
    """
    # Try getting from cache first
    cache_file_name = "speciesAndAudioList.json"
    if cache.file_exists(cache_file_name):
        json_data = cache.read_from_cache(cache_file_name)
        return json.loads(json_data, object_hook=lambda d: SimpleNamespace(**d))

    print("Determining species list...")
    species_dictionary = get_species_dictionary()
    keys_list = list(species_dictionary.keys())
    keys_list.sort()

    all_data_list = []
    for species in keys_list:
        all_data_list.append(species_dictionary.get(species))

    # Write to cache
    json_data = json.dumps(all_data_list, indent=4)
    cache.write_to_cache(json_data, cache_file_name)

    return all_data_list


def get_species_list_json():
    """
    Returns JSON version of species list in alphabetical order.
    :return: species list
    """
    # Try getting from cache first
    cache_file_name = "speciesList.json"
    if cache.file_exists(cache_file_name):
        return cache.read_from_cache(cache_file_name)

    all_data_list = get_sorted_all_data_list()
    species_list = []
    for a_species in all_data_list:
        # Each a_species is a list of calls
        a_call_for_species = a_species[0]
        species_list.append(a_call_for_species['species'])

    # Convert to JSON
    json_data = json.dumps(species_list, indent=4)

    # Write to cache
    cache.write_to_cache(json_data, cache_file_name)

    # Return the results in JSON
    return json_data


def get_all_species_audio_data_json():
    """
    Returns all audio track data in json format
    :return: all data in json format
    """
    return json.dumps(get_sorted_all_data_list(), indent=4)


def get_audio_data_json(qs):
    """
    Gets list of audio data for specified species. If species not specified then returns
    data for all species.
    :param qs: query string info. The parameter is 's' for species
    :return: JSON data for the species specified
    """
    species_param = qs.get('s')

    # If species not specified return data for all species
    if species_param is None or len(species_param) == 0:
        return get_all_species_audio_data_json()
    species = species_param[0]

    # First try getting from cache
    cache_file_name = 'audioUrlsForSpecies'
    cache_suffix = '.json'
    if cache.file_exists(cache_file_name, cache_suffix, species):
        return cache.read_from_cache(cache_file_name, cache_suffix, species)

    # Get object for specified species
    data_for_species = get_species_dictionary()[species]

    json_data = json.dumps(data_for_species, indent=4)

    # Write to cache
    cache.write_to_cache(json_data, cache_file_name, cache_suffix, species)

    return json_data


def get_image_urls_for_search_json(parsed_qs):
    """
    Does a Google query to find urls of appropriate images. Uses cache.

    :param parsed_qs: the query string info from the request. The 'q' param
    specifies the Google search to be done, like "image brown pelican flying"
    :return: list of urls of images for the query
    """
    # Determine the link for the image to use
    query_str = parsed_qs['q'][0]
    species = parsed_qs['s'][0]

    cache_file_name = 'imageUrlsForQuery_' + str(cache.stable_hash(query_str))
    cache_suffix = '.json'
    if cache.file_exists(cache_file_name, cache_suffix, species):
        return cache.read_from_cache(cache_file_name, cache_suffix, species)

    # Get list of URLs for the images as specified by the query_str
    image_urls = queryGoogle.get_url_list_for_image_search_query(query_str)

    json_data = json.dumps(image_urls, indent=4)

    # Write to cache
    cache.write_to_cache(json_data, cache_file_name, cache_suffix, species)

    # Return the results in JSON
    return json_data
