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
count = 20 # Number of images to return per Google Search API query

# 'imgColorType=gray' NOTE: gray might limit pics to silly drawings. Probably better to use photos
# and then grey scale them.

# The caches
_image_info_cache = {}
_processed_images_cache = {}


def load_and_process_image(url, parsed_qs):
    """
    Gets image for the url and processes it. Uses a cache so don't have to process
    same images again.

    :param url: link to image to load
    :param parsed_qs: so can pass extra params to process_image_for_norns()
    :return: the image processed to work on Norns device
    """
    # Get from cache if can
    global _processed_images_cache
    if url in _processed_images_cache:
        print(f'Using processed image from cache for url={url}')
        # For debugging show each image returned
        _processed_images_cache[url].show("returned image")
        return _processed_images_cache[url]

    # Wasn't in cache so get image via the web.
    # Load image and store it into a tmp file. Had to use requests lib and
    # set the headers to look like a browser to get access to certain images
    # where server apparently doesn't want to provide them to a python script.
    print(f'Getting image from url={url}')
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    # Store image into tmp file so that it can be processed
    with tempfile.TemporaryFile() as tmp_file:
        # Store data into file
        tmp_file.write(response.content)

        # Load image from the file into an Image object so that it can be manipulated
        tmp_file.seek(0)
        img = Image.open(tmp_file)

        # Convert image so suitable for Norns special display
        processed_image = process_image_for_norns(img, parsed_qs)

    # For debugging show each image returned
    processed_image.show("returned image")

    # Add to cache
    _processed_images_cache[url] = processed_image

    return processed_image


def scrape_google_for_images(query_str):
    """
    Scrapes the regular google.com search site to get list of urls for images that match
    the query string. The nice thing about this method is that it doesn't need API key and
    is therefore not rate limited.
    :param query_str: what images to search for
    :return: List of URLs of related images
    """
    # Create proper URL to scrape google search. Restricting results to ebird.org
    # and macaulaylibrary.org sos that get good pics. And need to specify more than
    # just single ebird.org to get back from google urls of the images.
    q = quote(f'site:ebird.org OR site:macaulaylibrary.org image {query_str}')
    url = f'https://www.google.com/search?q={q}'

    # Query google search
    print(f'Querying google search using url={url}')
    response = urlopen(url)
    response_as_str = response.read().decode(response.headers.get_content_charset())
    print(f'Response was {len(response_as_str)} characters long')

    # Find all the urls of the images and add them to image_urls
    image_urls = []
    search_str = "imgurl=" # Indicates start of a URL in the search response
    start = response_as_str.find(search_str, 0)
    while start != -1:
        end = response_as_str.find("&", start)
        image_url = response_as_str[start + len(search_str): end]
        image_urls.append(image_url)

        # Find the start of the next image url
        start = response_as_str.find(search_str, end)

    return image_urls


def query_google_images_api(query_str):
    """
    Does google query to determine list of images that can be used. Actually does two queries, each for
    the maximum of 10 images, and then combines the results into a single list.
    Search term specified by 'q' query str param. Note that only get 100 free Google Custom Search API
    calls per day. Once exceed that get an Http error.
    :param query_str:
    :return: list of urls to the original images for the query_str
    """
    q = quote(query_str)
    query_url = f'{api}?key={api_key}&cx={server_context}&q={q}&searchType=image&{color_type}'

    # Get the response of URL and convert response to json object containing just the important 'items' data
    print(f'Querying Google Image API using={query_url}')
    response = urlopen(query_url)
    data_json1 = json.loads(response.read())

    # Get next page of results so that can have total of 20 images to choose from
    response = urlopen(query_url + '&start=11')
    data_json2 = json.loads(response.read())

    combined_json =  data_json1['items'] + data_json2['items']

    image_urls = []
    for item in combined_json:
        image_urls.append(item['link'])

    return image_urls


def get_url_list_for_query(query_str):
    """
    Gets list of URLs for the original images specified by the query params. Uses a cache so that don't have to keep
    hitting search engine so much.
    :param query_str: what images to search for
    :return: the list of urls for the original images
    """

    # Get from cache if can
    global _image_info_cache
    if query_str in _image_info_cache:
        print(f'Getting image list info from cache for query={query_str}')
        return _image_info_cache[query_str]

    # Wasn't in cache so get URLs from search engine.
    # First try scraping the regular Google search site. If that doesn't work
    # then try the Google Search API
    try:
        image_urls = scrape_google_for_images(query_str)
        if len(image_urls) == 0:
            image_urls = query_google_images_api(query_str)

        # Add Google API info for the query_str to cache
        _image_info_cache[query_str] = image_urls
    except HTTPError as err:
        # Will use default url for an image so at least get something
        default_link = 'https://www.allaboutbirds.org/guide/assets/photo/304461551-480px.jpg'
        print(f'Error occurred trying to access Google API to find appropriate images. {err}. '
              f'Using default link {default_link}')
        image_urls = []
        image_urls.append(default_link)
        return image_urls

    return image_urls


def get_image(parsed_qs):
    """
    Does a query to find urls of appropriate images.Then picks a random
    URL and loads and processes the image so the png  can be used on a Norns.

    :param parsed_qs:
    :return: processed image as a PNG made suitable for Norns device
    """
    # Determine the link for the image to use
    query_str = parsed_qs['q'][0]

    # Get list of URLs for the images as specified by the query_str
    image_urls = get_url_list_for_query(query_str)

    # Determine which random result to use.
    random_index = random.randrange(0, len(image_urls))

    link = image_urls[random_index]
    print(f'For query_str="{query_str}" random_index={random_index} so using URL {link}')

    # Get the image and process it. Will use cache
    img = load_and_process_image(link, parsed_qs)

    # Return the processed image
    return img
