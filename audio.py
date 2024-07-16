import collections
import io
import json
from io import BytesIO

from bs4 import BeautifulSoup
import requests

from pydub import AudioSegment, silence
from pydub.effects import normalize

# Note: To convert from mp3 to wav need to load both pydub and ffmpeg using
# (see https://github.com/jiaaro/pydub?tab=readme-ov-file#installation):
#  "pip install pydub"
# See for ffmpeg https://www.hostinger.com/tutorials/how-to-install-ffmpeg#How_to_Install_FFmpeg_on_macOS
#  "apt-get install ffmpeg"  or on Macos go to https://www.ffmpeg.org/download.html
# Afterwards need to move ffmpeg to a place like audio/bin/ffmpeg and then create a symbolic link to where Path
# is already pointing, like to /usr/local/bin using:
#  "ln -s ~/audio/bin/ffmpeg /usr/local/bin/ffmpeg"
# And then had to load in ffprob in same way!

# To get more advanced AudioSegment features installed:
#  pip install audiosegment
# filter_silence() requires sox, which is huge! If use that function then do:
#   brew install sox

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
        row_data['species'] = species[0:end]
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
        return _species_dict_cache

    # Add the species data to the species dictionary
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
        return _species_list_cache

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


# Cache of processed audio data, keyed by url
_audio_cache = {}


def get_wav_file(qs):
    """
    Gets the mp3 file for the specified species and returns wav version of it, since that is what Norns requires.
    :param qs: query string info. The parameter is 'url' for link to an mp3. Might work with other formats too!?!
    :return: bytes that contains the wav data
    """

    # Constants
    max_clip_start_msec = 10000 # For when voice intro ends and actual bird sounds start

    # If mp3 file not specified then return None
    url_param = qs.get('url')
    if url_param is None or len(url_param) == 0:
        return None
    url = url_param[0]

    global _audio_cache
    if url in _audio_cache:
        print(f'Getting audio data from cache for url={url}')
        return io.BytesIO(_audio_cache[url])

    # Determine max length of clip to be returned
    max_clip_msec_param = qs.get('max_msec')
    if max_clip_msec_param is None or len(max_clip_msec_param) == 0:
        max_clip_msec = 30000 # Default value
    else:
        max_clip_msec = max_clip_msec_param[0]

    # Get the mp3 data
    mp3 = requests.get(url)

    # Process the sound. Just use first ~40 seconds so that processing doesn't get bogged down on really long clips
    sound = AudioSegment.from_mp3(BytesIO(mp3.content))[:max_clip_msec+max_clip_start_msec]

    # Try to get rid of any voice introduction to the clip. The voice intros appear to be consistently
    # separated by half second or so of silence. Found that had to reduce the silence_thresh to -70.0 even
    # though the db of a non-silent clip was just -38. But at least it works. And found that it is really
    # important to set seek_step to 25 since that makes the function run 25x, though then the boundaries are
    # of course not determined as accurately.
    silent_portions = silence.detect_silence(sound, min_silence_len=300, silence_thresh=-70.0, seek_step=25)
    if len(silent_portions) > 0:
        start, stop = silent_portions[0]
        if stop < max_clip_start_msec:
            sound = sound[stop:]

    # Trim sound clip to final length now that have removed any possible intro
    sound = sound[0:max_clip_msec]

    # Normalize sound so loud as possible
    sound = normalize(sound, headroom=1.0)

    # Specify meta data for audio
    tags = f'{{"url": "{url}", "copyright": "Cornell Lab Macaulay Library"}}'

    # Convert to wav data
    buffer = io.BytesIO()
    sound.export(buffer, format="wav", tags=tags)

    # Store audio in cache
    buffer.seek(0)
    buffer_bytes = buffer.read()
    _audio_cache[url] = buffer_bytes

    return buffer
