#! /usr/bin/env python
from io import BytesIO
# Python's bundled WSGI server
from wsgiref import util
from wsgiref import simple_server

from urllib.parse import urlparse
from urllib.parse import parse_qs

import queryGoogle
from getJson import get_species_list_json, get_audio_data_json
from audio import get_wav_file


# NOTE: if you get an SSL Certificate error on OSX (Macs) then you need to install
# the SSL certificates manually by calling the appropriate Python script. It is at
# /Applications/Python\ 3.12/Install\ Certificates.command

# NOTE: had to install Pillow image library using "pip install pillow"
# NOTE: had to install webscraper "pip install html-table-parser-python3"


def wav_response(wav_data, start_response):
    """
    Creates a http response for a wav audio file
    :param wav_data: IOBytes
    :param start_response:
    :return:
    """
    if wav_data is None:
        return error_response("Could not load image", start_response)

    # Return object as a PNG (though should already be a PNG)
    wav_data.seek(0)
    content_length = wav_data.getbuffer().nbytes

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'audio/wav'),
        ('Content-Length', str(content_length))
    ]
    start_response(status, response_headers)

    return wav_data


def json_response(msg, start_response):
    # If no msg then return error
    if len(msg) == 0:
        return error_response('No data for that query', start_response)

    response_body = bytes(msg, 'utf-8')
    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/json'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)

    return [response_body]


def error_response(msg, start_response):
    response_body = bytes(msg, 'utf-8')
    status = '404 Not Found'
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)

    return [response_body]


def image_response(image, start_response):
    """
    Returns an http response for a png image
    """

    # Return object as a PNG (though should already be a PNG)
    img_bytes = BytesIO()
    image.save(img_bytes, 'PNG')
    img_bytes.seek(0)
    content_length = img_bytes.getbuffer().nbytes

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'image/png'),
        ('Content-Length', str(content_length))
    ]
    start_response(status, response_headers)

    return img_bytes


def handle_request(environ, start_response):
    """ Handles each request """

    uri = util.request_uri(environ, include_query=True)
    parsed_url = urlparse(uri)

    # Determine the query string to use for the Google API.
    # Found that get more appropriate pics if also specify "black and white" and "bird flying"
    parsed_qs = parse_qs(parsed_url.query, keep_blank_values=True)
    match parsed_url.path:
        case '/getImage':
            image = queryGoogle.get_image(parsed_qs)
            return image_response(image, start_response)
        case '/speciesList':
            return json_response(get_species_list_json(), start_response)
        case '/audioData':
            return json_response(get_audio_data_json(parsed_qs), start_response)
        case '/wavFile':
            return wav_response(get_wav_file(parsed_qs), start_response)
        case _:
            return error_response('No such command ' + parsed_url.path, start_response)


# If run as main, then start the webserver
if __name__ == "__main__":
    # Instantiate the server
    httpd = simple_server.make_server(
        # 'localhost',  # The host name
        '192.168.0.85',  # If want other device on local network to access then need to use local IP, not localhost
        8080,  # A port number where to wait for the request
        handle_request  # The application object name, in this case a function
    )

    # Respond to requests until process is killed
    httpd.serve_forever()
