# For caching objects in files so that handling requests is much quicker
import hashlib
import os
import logging

logger = logging.getLogger()


def stable_hash_str(key: str) -> str:
    """
    A hash function that is consistent across restarts. That is of course important for file names for a cache.
    :param key: string to be hashed.
    :return: a 12 character hex hash string
    """
    str_bytes = bytes(key, "UTF-8")
    m = hashlib.md5(str_bytes)
    return m.hexdigest()[:12].upper()


def file_identifier(url: str) -> str:
    """
    Returns the identifying part of the file name to be used to cache data associated with a URL.
    Key thing is that if the URL is for a special cornell.edu asset/catalog item then should
    use the catalog identifier, something like ML928372. This way can much more easily lookup the
    original data. But if not a cornell catalog item, use a hash.
    :param url: The object being cached was read from
    :return: the identifying part of the file name to be used to cache data for a url
    """
    if url.find('cornell.edu') != -1 and url.find('/asset/') != -1:
        # Special cornell URL so use the catalog number
        after_asset = url[url.find('/asset/')+7:]
        return 'ML' + after_asset[0:after_asset.find('/')]
    else:
        return stable_hash_str(url)


def proper_filename(filename):
    """
    Converts the filename parameter to a proper filename by replacing spaces with '_' and removing apostrophes
    :param filename:
    :return: the modified filename
    """
    return filename.replace(" ", "_").replace("'", "")


def get_full_filename(name, suffix='', subdir=''):
    """
    Returns the full filename for the cached file. Will have suffix appended.
    :param name: of the object being stored. Can be a string or a hash of  URL
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species. The specified name
    will be processed into a proper file name (e.g. no blanks nor single quotes)
    :return: the full filename of the file in the cache
    """
    # Determine directory where cache stored. Thought might use tempfile.gettempdir() but that directory would
    # change each time the app is run and would therefore not cache info across restarts. Therefore just
    # using "/usr/local/imagerCache" even though that is not necessarily portable.
    directory = '/usr/local/imagerCache/'
    full_directory = directory + proper_filename(subdir) + "/"

    # Make sure the directory exists
    os.makedirs(full_directory, exist_ok=True)

    filename = full_directory + name + suffix
    return filename


def write_to_cache(data, filename, suffix='', subdir=''):
    """
    Writes data to a file so that it is cached
    :param data: data to be cached. Can be string or bytes. If string then is converted to bytes.
    :param filename: if working with a URL should use str(cache.stable_hash(url)) as filename
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    """
    # If data is a string then convert it to bytes
    if isinstance(data, str):
        data = bytes(data, 'utf-8')

    full_filename = get_full_filename(filename, suffix, subdir)
    file = open(full_filename, 'wb')
    file.write(data)
    file.close()


def file_exists(filename, suffix='', subdir=''):
    """
    Returns true if file exists
    :param filename: if URL should use str(hash(url))
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    :return: true if file exists
    """
    exists = os.path.isfile(get_full_filename(filename, suffix, subdir))

    return exists


def read_from_cache(filename, suffix='', subdir=''):
    """
    Reads and returns data from file.
    Note: if reading json from cache and need to convert it to a Python object then use:
      return json.loads(json_data, object_hook=lambda d: SimpleNamespace(**d))
    :param filename: if URL should use str(hash(url))
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    :return: the str data stored in the file
    """
    full_filename = get_full_filename(filename, suffix, subdir)
    file = open(full_filename, 'rb')
    data = file.read()
    file.close()
    return data


def erase_cache():
    """
    Does system call to remove all the server side cache files. This way fresh
    data can be generated and used. Important for if update the
    supplementalSpeciesConfig.json file. Does not erase any of the wav or
    image files, since those do not change and they are much more costly to
    generate.
    """
    logger.info("Erasing cached JSON files from the imager cache")
    dir_name = get_full_filename('')
    os.system(f'rm {dir_name}*Cache.json')
    os.system(f'rm {dir_name}*/*Cache.json')
