
import json

import queryGoogle

import cache
from ebird import ebird


def get_all_species_audio_data_json():
    """
    DEPRECATED
    Returns all audio track data in json format
    :return: all data in json format
    """
    return json.dumps(ebird.__get_sorted_species_list(), indent=4)


def get_audio_data_json(qs):
    """
    DEPRECATED
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
    data_for_species = ebird.__get_species_tracks_dictionary()[species]

    json_data = json.dumps(data_for_species, indent=4)

    # Write to cache
    cache.write_to_cache(json_data, cache_file_name, cache_suffix, species)

    return json_data


def get_image_urls_for_search_json(parsed_qs):
    """
    DEPRECATED
    Does a Google query to find urls of appropriate images. Uses cache.

    :param parsed_qs: the query string info from the request. The 'q' param
    specifies the Google search to be done, like "image brown pelican flying"
    :return: list of urls of images for the query
    """
    # Determine the link for the image to use
    query_str = parsed_qs['q'][0]
    species = parsed_qs['s'][0]

    cache_file_name = 'imageUrlsForQuery_' + cache.stable_hash_str(query_str)
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
