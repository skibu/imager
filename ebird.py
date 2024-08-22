import collections
import json
import json.decoder
from typing import Any
import logging
import requests
from bs4 import BeautifulSoup

import cache
from queryGoogle import query_google_images_api

# Note: need this hack because BeautifulSoup doesn't work with Python 3.10+
# Discussion at
# https://stackoverflow.com/questions/69515086/error-attributeerror-collections-has-no-attribute-callable-using-beautifu
collections.Callable = collections.abc.Callable

logger = logging.getLogger(__name__)


class EBird:
    def __init__(self):
        """
        Loads in the key data at startup so that requests are fast
        """
        self.__get_groups_dictionary()

    def __get_species_code(self, species_name):
        """
        Looks up and returns the species ebird code needed for scraping ebird site. An example is
        "ameavo" for the "American Avocet" species. Also called the taxonCode by ebird site.
        :param species_name:
        :return: species code
        """
        # Determine the species code, which is needed for scraping the ebird site
        taxonomy_dict = self.__get_taxonomy_dictionary()
        unified_species_name = self.__unified_name(species_name)
        if unified_species_name not in taxonomy_dict:
            logger.warning(f'Species={species_name} not found in ebird.get_species_info()')
            return None
        species_data = taxonomy_dict[unified_species_name]

        return species_data['speciesCode']

    def __get_audio_data_list_for_species(self, species_name):
        """
        Scrapes ebird site to get info on best audio files for the specified species. Not cached since whoever
        calls this method caches it.
        :param species_name: Which species want info for
        :return: list of objects containing image info for species
        """
        logger.info(f'Determining audio data, including, urls for species={species_name}...')

        # Determine the species code, which is needed for scraping the ebird site
        species_code = self.__get_species_code(species_name)

        url = (f'https://media.ebird.org/catalog?taxonCode={species_code}'
               f'&mediaType=audio&sort=rating_rank_desc&view=list')

        # Make request to the website
        logger.info(f'Getting audio info for species={species_name} from url={url}')
        req = requests.get(url)

        # Parse the returned html
        soup = BeautifulSoup(req.text, 'html.parser')

        audio_info_list = []

        # Get the results list
        ol = soup.find('ol', class_="ResultsList")
        li_elements = ol.find_all('li')
        for li in li_elements:
            header = li.find('div', class_='ResultsList-header')
            # Get the URL of the mp3 file. It is the first immediate child of header that is a <a>
            first_a = header.find('a', recursive=False)
            catalog_number = first_a.text.replace('"', '').replace('ML', '')

            audio_url = f'https://cdn.download.ams.birds.cornell.edu/api/v2/asset/{catalog_number}/mp3'

            tag_span = header.find('span', class_='ResultsList-label')
            tag_label_text = tag_span.text if tag_span is not None else None
            tag_content_text = tag_span.find_next_sibling('span').text if tag_span is not None else None

            meta_element = li.find('div', class_='ResultsList-meta')
            user_date_loc_element = meta_element.find('div', class_='userDateLoc')

            # Usually author name is in a <a> element but sometimes it is in a <span>
            author_element = user_date_loc_element.find(['a','span'])
            author = author_element.text

            # Usually date is in a <time> element but sometimes it is in a span (if it is unknown for example0
            date_element = author_element.find_next(['time','span'])
            date = date_element.text

            # Since sometimes author is also in an span need to use date_element.find_next() to
            # dependably get the location span
            loc_element = date_element.find_next('span')
            loc = loc_element.text

            audio_info_list.append({'author': author,
                                    'date': date,
                                    'loc': loc,
                                    'audio_url': audio_url,
                                    'tagLabel': tag_label_text,
                                    'tagContent': tag_content_text})

            # Just use 10 best. If used more then would rarely have cache hits. And they
            # are supposedly listed in order of ratings. Better to just use the 10 best.
            if len(audio_info_list) >= 10:
                break

        return audio_info_list

    def __get_image_data_list_for_species(self, species_name):
        """
        Scrapes ebird site to get info on best images for the specified species. Not cached since whoever
        calls this method caches it.
        :param species_name: Which species want info for
        :return: list of objects containing image info for species
        """
        logger.info(f'Determining image data, including urls, for species={species_name}...')

        # Determine the species code, which is needed for scraping the ebird site
        species_code = self.__get_species_code(species_name)

        url = (f'https://media.ebird.org/catalog?taxonCode={species_code}'
               f'&mediaType=photo&sort=rating_rank_desc&view=list')

        # Make request to the website
        logger.info(f'Getting image info for species={species_name} from url={url}')
        req = requests.get(url)

        # Parse the returned html
        soup = BeautifulSoup(req.text, 'html.parser')

        image_info_list = []

        # Get the results list
        ol = soup.find('ol', class_="ResultsList")
        li_elements = ol.find_all('li')
        for li in li_elements:
            media = li.find('div', class_='ResultsList-media')
            image = media.find('img')
            image_url = image.attrs['src']

            meta_element = li.find('div', class_='ResultsList-meta')
            user_date_loc_element = meta_element.find('div', class_='userDateLoc')

            # Usually author name is in a <a> element but sometimes it is in a <span>
            author_element = user_date_loc_element.find(['a', 'span'])
            author = author_element.text

            # Usually date is in a <time> element but sometimes it is in a span (if it is unknown for example0
            date_element = author_element.find_next(['time','span'])
            date = date_element.text

            # Since sometimes author is also in an span need to use date_element.find_next() to
            # dependably get the location span
            loc_element = date_element.find_next('span')
            loc = loc_element.text

            # Get the tags like 'Behavior'
            tags_div = li.find('div', class_='ResultsList-tags')
            tags_list = tags_div.find_all('div')
            found_tags = []
            for div in tags_list:
                label = div.find('span', class_='ResultsList-label')
                content = label.find_next('span')
                found_tags.append({'label': label.text, 'content': content.text})

            image_info_list.append({'author': author,
                                    'date': date,
                                    'loc': loc,
                                    'image_url': image_url,
                                    'tags': found_tags})

            # Just use 10 best. If used more then would rarely have cache hits. And they
            # are supposedly listed in order of ratings. Better to just use the 10 best.
            if len(image_info_list) >= 10:
                break

        return image_info_list

    def __unified_name(self, species_name):
        """
        Turns out ebird is not 100% consistent with their species names. Found at least one case,
        "Black-crowned Night-Heron" where the second dash isn't always there. Also found a problem
        with "Western/Eastern Cattle Egret". Therefore need to do lookups with a unified name.
        :rtype: str
        :param species_name:
        :return: Modified species name that is easier to match
        """
        return (species_name.replace('-', ' ')
                .replace('Western/Eastern ', '')
                .replace('Western Flycatcher (Cordilleran)', 'Cordilleran Flycatcher')
                .lower())

    def __get_track_data(self):
        """
        Loads in audio "track" data from Macaulay Library (Ithaca) and puts it into
        an array. This is a useful way of determining the most relevant bird species
        to include. A species will likely have multiple audio tracks. Data in the list
        is not sorted in any way. Might not actually use the audio tracks from this list
        because can get a greater selection by perusing the ebird web page for a species,
        but it is definitely useful for determining list of species to use.
        :return: Array of data describing each audio track available
        """
        # The webpage where the data is listed
        url = 'https://www.macaulaylibrary.org/guide-to-bird-sounds/track-list/'

        # Make request to the website
        logger.info(f'Getting species data from url={url}')
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

    def __get_species_tracks_dictionary(self):
        """
        Data dictionary is keyed on species name and value is list of audio tracks for the species.
        Raw data & track info is from https://www.macaulaylibrary.org/guide-to-bird-sounds/track-list/
        Not cached since the calling methods cache it. But I'm not confident this is truly the best
        thing to do.
        :return: the data dictionary
        """
        # Add each species data to the species dictionary
        logger.info("Creating species dictionary...")
        species_dict = dict()
        for species_data in self.__get_track_data():
            list_for_species = species_dict.get(species_data['species'])
            if list_for_species is None:
                list_for_species = []
                species_dict[species_data['species']] = list_for_species
            list_for_species.append(species_data)

        return species_dict

    __taxonomy_dictionary_cache = None

    def __get_taxonomy_dictionary(self):
        """
        Gets as a dictionary the taxonomy of all bird species (~30k!) from the ebird site. Includes ebird
        taxonomy name, which is needed for looking up best images and audio clips on ebird. Caches
        the dictionary so don't need to keep hitting the ebird site.
        :return: taxonomy of all bird species. A dictionary keyed by unified species name and containing basic
        info about the species. unified_species_name = self.__unified_name(species_name)
        """
        # Try getting from memory cache first
        if self.__taxonomy_dictionary_cache is not None:
            logger.info(f'Using taxonomy dictionary from memory cache')
            return self.__taxonomy_dictionary_cache

        # Try getting from file cache
        cache_file_name = "allEbirdSpeciesTaxonomyDictionaryCache.json"
        if cache.file_exists(cache_file_name):
            logger.info(f'Using taxonomy dictionary from file cache')
            json_data = cache.read_from_cache(cache_file_name)
            return json.loads(json_data)

        # Load in the full taxonomy from ebird site
        logger.info(f'Generating taxonomy dictionary because was not cached')
        url = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json "
        headers = {'x-ebirdapitoken': 'jfekjedvescr'}
        response = requests.get(url, headers=headers)
        full_taxonomy = json.loads(response.content)

        taxonomy_dict: dict[Any, dict[str, Any]] = {}
        for full_species in full_taxonomy:
            # If species missing any important data then skip it
            if ('comName' not in full_species or
                    'speciesCode' not in full_species or
                    'sciName' not in full_species or
                    'familyComName' not in full_species):
                continue

            species_name = full_species['comName']
            unified_species_name = self.__unified_name(species_name)

            species = {
                "speciesName": species_name,
                "speciesCode": full_species['speciesCode'],
                "sciName": full_species['sciName'],
                "groupName": full_species['familyComName']}
            taxonomy_dict[unified_species_name] = species

        # Write the full_taxonomy json to cache file in nice format by dumping object into json string
        cache.write_to_cache(json.dumps(taxonomy_dict, indent=4), cache_file_name)

        # Store in memory cache
        self.__taxonomy_dictionary_cache = taxonomy_dict

        return taxonomy_dict

    __supplemental_species_config_cache = None

    def __supplemental_species_config(self):
        """
        Reads in supplemental species config file supplementalSpeciesConfig.json
        :return: data for the supplemental species
        """
        if self.__supplemental_species_config_cache is not None:
            logger.info(f'Using cached supplemental species config info')
            return self.__supplemental_species_config_cache

        # Read in supplemental data and convert JSON to a python object
        logger.info(f'Generating supplemental species config info')
        supplemental_file_name = 'data/supplementalSpeciesConfig.json'
        try:
            with open(supplemental_file_name, 'rb') as file:
                json_data = file.read()
                try:
                    supplemental_species = json.loads(json_data)
                except json.decoder.JSONDecodeError as err:
                    logger.error(f'Error parsing supplementalSpeciesConfig.json {err}')
                    return {}
        except FileNotFoundError:
            logger.warning(f'The supplemental file {supplemental_file_name} does not exist')
            return {}

        # Convert to a dictionary so can look up data by species_name easily
        supplemental_species_dict = {}
        for species in supplemental_species:
            supplemental_species_dict[species['speciesName']] = species

        # Cache result
        __supplemental_species_config_cache = supplemental_species_dict

        return supplemental_species_dict

    def __add_species_to_group(self, species_name, group_name, groups):
        if group_name not in groups:
            species_list_for_group = [species_name]
            groups[group_name] = species_list_for_group
        else:
            species_list_for_group = groups[group_name]
            species_list_for_group.append(species_name)

    __groups_dictionary_cache = None

    def __get_groups_dictionary(self):
        """
        Provides the group list for the species specified in the species_list. Each group is a list of
        species names within that group.
        :return: dictionary of all groups. Keyed by group name and containing values of list of all
        species names for that group
        """
        # Return memory cached value if exists
        if self.__groups_dictionary_cache is not None:
            logger.info(f'Using memory cached groups dictionary')
            return self.__groups_dictionary_cache

        # Use file cache if it exists
        cache_file_name = 'groupsCache.json'
        if cache.file_exists(cache_file_name):
            logger.info(f'Using file cached groups dictionary')
            json_data = cache.read_from_cache(cache_file_name)
            return json.loads(json_data)

        logger.info("Generating the groups dictionary...")

        # The return value. groups is a dictionary keyed on group name and containing list of species names
        groups = {}

        # So that can limit which species are listed
        species_name_list = self.__get_species_name_list()
        taxonomy = self.__get_taxonomy_dictionary()

        # For each species name from __get_species_name_list...
        for species_name in species_name_list:
            # Get the species info from the taxonomy data
            uni_name = self.__unified_name(species_name)
            if uni_name not in taxonomy:
                # If can't find this species, even using unified name, in the taxonomy, then skip it
                logger.warning(f'Could not find species "{species_name}" in taxonomy so skipping it.')
                continue
            species = taxonomy[uni_name]

            # Add the group name to the groups dictionary
            group_name = species['groupName']
            self.__add_species_to_group(species_name, group_name, groups)

        # Read in and add the supplemental data to the groups object
        supplemental_species = self.__supplemental_species_config()
        for species in supplemental_species.values():
            self.__add_species_to_group(species['speciesName'], species['groupName'], groups)

        # Write groups to cache
        cache.write_to_cache(json.dumps(groups, indent=4), cache_file_name)

        # Store in memory cache
        self.__groups_dictionary_cache = groups

        return groups

    def __get_sorted_species_list(self):
        """
        Returns list of all species in alphabetical order. For each species there is a list of the
        track audio calls, but those particular track calls might not be used. Caches the data.
        :return: list of all data, ordered alphabetically by species
        """
        # Try getting from cache first
        cache_file_name = "speciesTracksListCache.json"
        if cache.file_exists(cache_file_name):
            logger.info(f'Using file cached species list {cache_file_name}')
            json_data = cache.read_from_cache(cache_file_name)
            return json.loads(json_data)

        logger.info("Generating speciesTrackList...")
        species_dictionary = self.__get_species_tracks_dictionary()
        keys_list = list(species_dictionary.keys())
        keys_list.sort()

        all_species_list = []
        for species in keys_list:
            all_species_list.append(species_dictionary.get(species))

        # Write to cache
        json_data = json.dumps(all_species_list, indent=4)
        cache.write_to_cache(json_data, cache_file_name)

        return all_species_list

    def __get_species_name_list(self):
        """
        Returns list of species names in alphabetical order
        :return: list of species names
        """
        all_data_list = self.__get_sorted_species_list()
        species_list = []
        for species in all_data_list:
            # Each a_species is a list of calls
            a_call_for_species = species[0]
            species_list.append(a_call_for_species['species'])

        return sorted(species_list)

    # Memory cache for get_species_list_json()
    __species_names_list_cache = None

    def get_species_list_json(self):
        """
        Returns JSON string of list of species names in alphabetical order.
        :return: species list as JSON string
        """
        # If in memory cache return it
        if self.__species_names_list_cache is not None:
            return self.__species_names_list_cache

        # Try getting from file cache first
        cache_file_name = "speciesNamesListCache.json"
        if cache.file_exists(cache_file_name):
            logger.info(f'Getting species names list from file cache {cache_file_name}')
            return cache.read_from_cache(cache_file_name)

        logger.info('Generating species name list json...')

        # Get the list of species names
        species_list = self.__get_species_name_list()

        # Convert to JSON
        json_data = json.dumps(species_list, indent=4)

        # Write to cache
        cache.write_to_cache(json_data, cache_file_name)

        # Write to memory cache
        __species_names_list_cache = json_data

        # Return the results in JSON
        return json_data

    __group_names_list_cache = None

    def get_group_list_json(self):
        """
        Returns JSON str of list of group names alphabetized
        :return: JSON str of group names
        """
        # If in memory cache return it
        if self.__group_names_list_cache is not None:
            logger.info(f'Getting the group name list from memory cache')
            return self.__group_names_list_cache

        # Try getting from cache first
        cache_file_name = "groupNamesListCache.json"
        if cache.file_exists(cache_file_name):
            logger.info(f'Getting the group name list from file cache {cache_file_name}')
            return cache.read_from_cache(cache_file_name)

        logger.info('Determining group list json...')

        # Get the group info
        groups_dict = self.__get_groups_dictionary()

        # Put group names into an array
        group_names = []
        for group_name in groups_dict:
            group_names.append(group_name)

        # Convert sorted group names to a json str
        json_data = json.dumps(sorted(group_names), indent=4)

        # Write to cache
        cache.write_to_cache(json_data, cache_file_name)

        # Write to memory cache
        __group_names_list_cache = json_data

        # Return the results in JSON
        return json_data

    def get_species_info(self, species_name):
        """
        Returns info for the specified species, including list of image info, list of audio info, and some other
        data.
        :param species_name:
        :return: json str containing info for species
        """
        # Return info from cache if available
        cache_file_name = 'speciesDataCache.json'
        if cache.file_exists(cache_file_name, subdir=species_name):
            logger.info(f'Using file cached data for species={species_name} file={cache_file_name}')
            return cache.read_from_cache(cache_file_name, subdir=species_name)

        logger.info(f'Generating data for species={species_name}...')

        # First, see if info for this species is in the supplemental file. This
        # way the supplemental file can override what is automatically determined
        # using ebird data.
        supplemental_species_dict = self.__supplemental_species_config()
        if species_name in supplemental_species_dict:
            # Use supplemental info
            supplemental_species = supplemental_species_dict.get(species_name)
            image_search_query = supplemental_species['imageSearchQuery']
            image_list = query_google_images_api(image_search_query)
            species_data = {
                "speciesName": supplemental_species['speciesName'],
                "groupName": supplemental_species['groupName'],
                "imageDataList": image_list,
                "audioDataList": supplemental_species['mp3s']}
        else:
            # Get all the ebird info for the species
            taxonomy_dict = self.__get_taxonomy_dictionary()
            unified_species_name = self.__unified_name(species_name)
            if unified_species_name not in taxonomy_dict:
                logger.warning(f'Species={species_name} not found in ebird.get_species_info()')
                return None
            species_data = taxonomy_dict[unified_species_name]

            # Add info for images and audio
            image_data_list = self.__get_image_data_list_for_species(species_name)
            species_data['imageDataList'] = image_data_list

            audio_data_list = self.__get_audio_data_list_for_species(species_name)
            species_data['audioDataList'] = audio_data_list

        # Convert the species data into json
        json_data = json.dumps(species_data, indent=4)

        # Write to cache
        cache.write_to_cache(json_data, cache_file_name, subdir=species_name)

        return json_data

    def get_species_for_group_json(self, group_name):
        """
        Returns json consisting of list of species for the specified group
        :param group_name:
        :return: list of species for group
        """
        groups_dict = self.__get_groups_dictionary()

        if group_name not in groups_dict:
            return f'Error: group {group_name} does not exist'

        species_list = groups_dict[group_name]
        json_data = json.dumps(species_list, indent=4)
        return json_data


# Global instantiation
ebird = EBird()
