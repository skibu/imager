import io
from io import BytesIO
import requests

from pydub import AudioSegment, silence
from pydub.effects import normalize
from pydub.playback import play # Just for if want to play audio

import cache

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

# Cache of processed audio data, keyed by url
_audio_cache = {}


def get_wav_file(parsed_qs):
    """
    Gets the mp3 file for the URL specified in the query string and returns wav version of it, since that is what
    Norns requires.
    :param parsed_qs: query string info. The important parameter is 'url' for link to an mp3. Might work with other formats!?!
    Also provides species name 's' which is used in caching
    :return: bytes that contains the wav data
    """

    # Constants
    max_clip_start_msec = 10000 # For when voice intro ends and actual bird sounds start

    # Get from cache if can
    species = parsed_qs['s'][0]
    url = parsed_qs['url'][0]
    cache_file_name = 'audio_' + str(cache.stable_hash(url))
    cache_suffix = '.wav'
    if cache.file_exists(cache_file_name, cache_suffix, species):
        return io.BytesIO(cache.read_from_cache(cache_file_name, cache_suffix, species))

    # Determine max length of clip to be returned
    max_clip_msec_param = parsed_qs.get('max_msec')
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

    # Add tags, make sure bitrate is 48k, and convert to wav data
    buffer = io.BytesIO()
    sound.export(buffer, format="wav", tags=tags, bitrate='48k')

    # Store audio in cache
    buffer.seek(0)
    buffer_bytes = buffer.read()
    cache.write_to_cache(buffer_bytes, cache_file_name, cache_suffix, species)

    return buffer
