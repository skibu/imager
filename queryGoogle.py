import json
import random
import logging
from imageProcessor import load_and_process_image_for_url

from urllib.request import urlopen
from urllib.parse import quote
from urllib.error import HTTPError

logger = logging.getLogger()

api = 'https://www.googleapis.com/customsearch/v1'
api_key = 'AI''zaSyB9_wTwJ-''GOLIgD-EoT''9qxOm''-osRT__h0A'
server_context = '57fae5c295baa4bca'
color_type = ''
count = 20 # Number of images to return per Google Search API query


def scrape_google_for_images(query_str):
    """
    DEPRECATED - Doesn't actually work
    Scrapes the regular google.com search site to get list of urls for images that match
    the query string. The nice thing about this method is that it doesn't need API key and
    is therefore not rate limited.
    :param query_str: what images to search for. Can be something like
    "site:ebird.org OR site:macaulaylibrary.org image brown pelican flying"
    :return: List of URLs of related images
    """
    # Create proper URL to scrape google search. Restricting results to ebird.org
    # and macaulaylibrary.org sos that get good pics. And need to specify more than
    # just single ebird.org to get back from google urls of the images.
    q = quote(query_str)
    url = f'https://www.google.com/search?q={q}'

    # Query google search
    logger.info(f'Scraping google search using url={url}')
    response = urlopen(url)
    response_as_str = response.read().decode(response.headers.get_content_charset())
    logger.info(f'Scraping response was {len(response_as_str)} characters long')

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
    logger.info(f'Querying Google Image API using={query_url}')
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


def get_url_list_for_image_search_query(query_str):
    """
    Gets list of URLs for the original images specified by the query params.
    :param query_str: what images to search for
    :return: the list of urls for the original images
    """

    # Wasn't in cache so get URLs from search engine.
    # First try the Google Search API since that provides more results. But if the API call
    # fails, likely due to more than 100 hits in a day, they try scraping the regular Google
    # search site.
    logger.info(f'Searching for images using "{query_str}"')
    try:
        image_urls = query_google_images_api(query_str)
    except HTTPError as err:
        logger.warning(f'Got error using the Google API. Therefore trying scraping Google as backup. {err}')
        image_urls = scrape_google_for_images(query_str)
        if image_urls is None or len(image_urls) == 0:
            # Will use default url for an image so at least get something
            default_link = 'https://www.allaboutbirds.org/guide/assets/photo/304461551-480px.jpg'
            logger.warning(f'Did not successfully find image via scraping Google site. Therefore '
                  f'using default image link {default_link}')
            image_urls = [default_link]

    return image_urls


def get_random_image_for_query(parsed_qs):
    """
    Does a Google query to find urls of appropriate images. Then picks a random
    URL and loads and processes the image so the png  can be used on a Norns.

    :param parsed_qs: the query string info from the request. The 'q' param
    specifies the Google search to be done, like "image brown pelican flying".
    Should also contain 's' param to specify the species.
    :return: processed image as a PNG made suitable for Norns device
    """
    # Determine the link for the image to use
    query_str = parsed_qs['q'][0]

    # Get list of URLs for the images as specified by the query_str
    image_urls = get_url_list_for_image_search_query(query_str)

    # Determine which random result to use.
    random_index = random.randrange(0, len(image_urls))

    url = image_urls[random_index]
    logger.info(f'For query_str="{query_str}" random_index={random_index} so using URL {url}')

    # Get the image and process it. Will use cache
    img = load_and_process_image_for_url(url, parsed_qs)

    # Return the processed image
    return img
