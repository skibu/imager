import json
import os
import random
import requests
import tempfile

from imageProcessor import process_image_for_norns

from urllib.request import urlopen
from urllib.parse import quote
from urllib.error import HTTPError

from PIL import Image

api = 'https://www.googleapis.com/customsearch/v1'
api_key = 'AI''zaSyB9_wTwJ-''GOLIgD-EoT''9qxOm''-osRT__h0A'
server_context = '57fae5c295baa4bca'
color_type = ''
count = 20 # Number of images to return per query

# 'imgColorType=gray' NOTE: gray might limit pics to silly drawings. Probably better to use photos
# and then grey scale them.

# The caches
_image_info_cache = {}
_processed_images_cache = {}


def query_google_images(query_str):
    """
    Does google query to determine list of images that can be used. Actually does two queries, each for
    the maximum of 10 images, and then combines the results into a single list.
    Search term specified by 'q' query str param. Note that only get 100 free Google Custom Search API
    calls per day. Once exceed that get an Http error.
    :param query_str:
    :return: the important 'items" data from the Google API image call
    """
    q = quote(query_str)
    url = f'{api}?key={api_key}&cx={server_context}&q={q}&searchType=image&{color_type}'

    # Get the response of URL and convert response to json object containing just the important 'items' data
    response = urlopen(url)
    data_json1 = json.loads(response.read())

    # Get next page of results so that can have total of 20 images to choose from
    response = urlopen(url + '&start=11')
    data_json2 = json.loads(response.read())

    return data_json1['items'] + data_json2['items']


def get_image_info(query_str):
    """
    Gets JSON data for the query params. Uses a cache so that don't have to keep hitting Google
    API so much.
    :param query_str:
    :return: json object containing info about images from Google API
    """

    # Get from cache if can
    global _image_info_cache
    if query_str in _image_info_cache:
        print(f'Getting Google search data info from cache for query={query_str}')
        return _image_info_cache[query_str]

    # Wasn't in cache so get data using Google API
    items_data = query_google_images(query_str)

    # Add Google API info for the query_str to cache
    _image_info_cache[query_str] = items_data

    return items_data


def load_image(url):
    """
    Gets image for the url. Uses a cache.

    :param url:
    :return: the specified image
    """
    # Get from cache if can
    global _processed_images_cache
    if url in _processed_images_cache:
        print(f'Using processed image from cache for url={url}')
        return _processed_images_cache[url]

    # Wasn't in cache so get image via the web.
    # Load image and store it into a tmp file. Had to use requests lib and
    # set the headers to look like a browser to get access to certain images
    # where server apparently doesn't want to provide them to a python script.
    print(f'Getting image from url={url}')
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    print(f'Storing image into tmp file so that it can be processed')
    with tempfile.TemporaryFile() as tmp_file:
        # Store data into file
        tmp_file.write(response.content)

        # Load image from the file into an Image object so that it can be manipulated
        tmp_file.seek(0)
        img = Image.open(tmp_file)

        # Convert image so suitable for Norns special display
        processed_image = process_image_for_norns(img)

    # Add to cache
    _processed_images_cache[url] = processed_image

    return processed_image


def get_image(parsed_qs):
    """
    Does a query to Google API to find appropriate links to images. Then loads in a random image.
    If 'debug' query str parameter set then will bypass google API and just use a hardcoded image.
    This is nice for debugging since only get something like 100 free Google API calls per day.

    :param parsed_qs:
    :return: processed image as a PNG made suitable for Norns device
    """

    # Default link for if in debugging mode or there is error with Google API call
    link = 'https://www.shutterstock.com/image-illustration/sandpiper-bird-flight-silhouette-illustration-260nw-476726563.jpg'
    link = 'https://www.allaboutbirds.org/guide/assets/photo/70589231-480px.jpg'
    link = 'https://www.allaboutbirds.org/guide/assets/og/75258011-1200px.jpg'
    link = 'https://www.allaboutbirds.org/guide/assets/photo/304461551-480px.jpg'

    # Determine the link for the image to use
    not_debug = parsed_qs.get('debug') is None
    if not_debug:
        query_str = parsed_qs['q'][0]

        try:
            items_data = get_image_info(query_str)

            # Determine which random result to use.
            random_index = random.randrange(0, len(items_data))
            #random_index = 4 # For debugging specific image
            result = items_data[random_index]
            print(f'random_index: {random_index}')

            # The following is the pertinent data from the Google search
            link = result['link']
            h = result['image']['height']
            w = result['image']['width']
            size = result['image']['byteSize']
            print(f'retrieving {w}x{h} {size} bytes. Image: {link}')
        except HTTPError as err:
            # Will use  default url for an image so at least get something
            print(f'Error occurred trying to access Google API to find appropriate images. {err}. '
                  f'Using default link {link}')

    # Get the image and process it. Will use cache
    img = load_image(link)

    # Return the processed image
    return img
