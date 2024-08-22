import gzip
import logging
import traceback
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from urllib.parse import parse_qs
from urllib.parse import urlparse
from PIL import Image
import cache
from audio import get_wav_file
from ebird import ebird
from imageProcessor import load_and_process_image

logger = logging.getLogger()


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        parsed_qs = parse_qs(parsed_url.query, keep_blank_values=True)

        try:
            logger.info(f'{self.client_address[0]}: Handling request {self.path}')
            match parsed_url.path:
                case '/allSpeciesList':
                    # Returns in json a list of all species
                    json = ebird.get_species_list_json()
                    return self._json_response(json)
                case '/groupsList':
                    # Returns in json a list of all species
                    json = ebird.get_group_list_json()
                    return self._json_response(json)
                case '/speciesForGroup':
                    json = ebird.get_species_for_group_json(parsed_qs['g'][0])
                    return self._json_response(json)
                case '/dataForSpecies':
                    # Returns in json a list of image urls for the species. The client app can
                    # then determine which one to use
                    species_info = ebird.get_species_info(parsed_qs['s'][0])
                    return self._json_response(species_info)
                case '/pngFile':
                    # Returns png file for the specified URL. Query string should specify 'url' and 's' for species.
                    image = load_and_process_image(self)
                    return self._image_response(image)
                case '/wavFile':
                    # Loads wav file for specified and species, specified in query string by 'url' and 's'
                    wav_file_data = get_wav_file(self)
                    return self._wav_response(wav_file_data)
                case '/eraseCache':
                    # Gets rid of all the *Cache.json files so that new data will be used
                    cache.erase_cache()
                    return self._json_response('Cache cleared')
                case _:
                    # In case unknown command specified
                    msg = 'No such command ' + self.path
                    logger.error(msg)
                    return self._error_response(msg)
        except Exception as e:
            msg = 'Exception for request ' + self.path + '\n' + traceback.format_exc()
            logger.error(msg)
            return self._error_response(msg)

    def _json_response(self, msg: str):
        # If no msg then return error
        # if len(msg) == 0:
        # return error_response('No data for that query', start_response)

        # If the msg is a string then convert to bytes
        response_body = bytes(msg, 'utf-8') if isinstance(msg, str) else msg

        # Setup headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()

        # Add the body
        self.wfile.write(response_body)

    def _image_response(self, image: Image):
        """
        Returns an http response for a png image.
        :param image: Image object representing the PNG image
        """
        self.send_response(200)
        self.send_header('Content-Type', 'image/png')

        # Return object as a PNG (though should already be a PNG)
        img_bytes_io = BytesIO()
        image.save(img_bytes_io, 'PNG')
        img_bytes_io.seek(0)
        img_bytes = img_bytes_io.read()

        # Finish up the response headers
        content_length = len(img_bytes)
        self.send_header('Content-Length', str(content_length))
        self.end_headers()

        # Write out the body
        self.wfile.write(img_bytes)

    def _wav_response(self, compressed_wav_data):
        """
        Creates a http response for a wav audio file. Can return either compressed
        or uncompressed data, depending on the request Content-Encoding header.
        :param compressed_wav_data: bytes containing the data, in compressed format, to be returned
        :return: IOBytes containing the data bytes for the full reply
        """
        if compressed_wav_data is None:
            return self._error_response("Could not load image")

        # Start the response
        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav')

        # If gzip compression is accepted then send back already compressed wav data
        http_accept_encoding = self.headers.get('Accept-Encoding')
        if http_accept_encoding is not None and 'gzip' in http_accept_encoding:
            # Using compression
            self.send_header('Content-Encoding', 'gzip')
            response_body = compressed_wav_data
        else:
            # Request not accepting compressed data so need to uncompress the compressed wav data
            # and use it as return_data
            uncompressed_bytes = gzip.decompress(compressed_wav_data)
            response_body = uncompressed_bytes

        # Finish up the response headers
        content_length = len(response_body)
        self.send_header('Content-Length', str(content_length))
        self.end_headers()

        # Write out the body
        self.wfile.write(response_body)

    def _error_response(self, msg):
        """
        For sending back error message response
        """
        response_body = bytes(msg, 'utf-8')

        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)
