# For caching objects in files so that handling requests is much quicker
import hashlib
import os


def stable_hash_str(key: str) -> str:
    """
    A hash function that is consistent across restarts. That is of course important for file names for a cache.
    :param key: string to be hashed.
    :return: a 16 character hash string
    """
    str_bytes = bytes(key, "UTF-8")
    m = hashlib.md5(str_bytes)
    return m.hexdigest()[:16].upper()


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
    # using "/tmp/imagerCache" even though that is not necessarily portable.
    directory = '/tmp/imagerCache/'
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
    print(f'Writing cache file={full_filename}')
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
    exists =  os.path.isfile(get_full_filename(filename, suffix, subdir))

    if not exists:
        print(f'File {filename}{suffix} does not exist in cache so will need to create the data')

    return exists


def read_from_cache(filename, suffix='', subdir=''):
    """
    Reads and returns data from file.
    Note: if reading json from cache and need to convert it to a Python object then use:
      return json.loads(json_data, object_hook=lambda d: SimpleNamespace(**d))
    :param filename: if URL should use str(hash(url))
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    :return: the str sdata stored in the file
    """
    full_filename = get_full_filename(filename, suffix, subdir)
    print(f'Reading cache file={full_filename}')
    file = open(full_filename, 'rb')
    data = file.read()
    file.close()
    return data
