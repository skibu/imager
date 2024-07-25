# For caching objects in files so that handling requests is much quicker
import hashlib
import os


def stable_hash(key: str) -> int:
    """
    A hash function that is consistent across restarts. That is of course important for file names for a cache.
    :param key: string to be hashed. abs(hash) is returned so that don't get a peculiar '-' at the beginning.
    :return: the hash
    """
    str_bytes = bytes(key, "UTF-8")
    m = hashlib.md5(str_bytes)
    return abs(int(m.hexdigest(), base=16))


def proper_filename(filename):
    """
    Converts the filename parameter to a proper filename by replacing spaces with '_' and removing apostrophes
    :param filename:
    :return: the modified filename
    """
    return filename.replace(" ", "_").replace("'", "")


def get_filename(name, suffix='', subdir=''):
    """
    Returns the filename for the cached file. Will have suffix appended.
    :param name: of the object being stored. Can be a string or a hash of  URL
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
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


def write_to_cache(data, name, suffix='', subdir=''):
    """
    Writes data to a file so that it is cached
    :param data: data to be cached. Can be string or bytes. If string then is converted to bytes.
    :param name: if URL should use str(cache.stable_hash(url))
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    """
    # If data is a string then convert it to bytes
    if isinstance(data, str):
        data = bytes(data, 'utf-8')

    filename = get_filename(name, suffix, subdir)
    file = open(filename, 'wb')
    file.write(data)
    file.close()


def file_exists(name, suffix='', subdir=''):
    """
    Returns true if file exists
    :param name: if URL should use str(hash(url))
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    :return: true if file exists
    """
    exists =  os.path.isfile(get_filename(name, suffix, subdir))

    if not exists:
        print(f'File {name}{suffix} does not exist in cache so will need to create the data')

    return exists


def read_from_cache(name, suffix='', subdir=''):
    """
    Reads and returns data from file.
    Note: if reading json from cache and need to convert it to a Python object then use:
      return json.loads(json_data, object_hook=lambda d: SimpleNamespace(**d))
    :param name: if URL should use str(hash(url))
    :param suffix: blank if specified in name. Otherwise .wav, .png, or .json, etc
    :param subdir: subdirectory. Useful if want to add species
    :return: the data stored in the file
    """
    filename = get_filename(name, suffix, subdir)
    file = open(filename, 'rb')
    data = file.read()
    file.close()
    return data