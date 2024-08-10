import gzip
import io
from io import BytesIO
import requests

from pydub import AudioSegment, silence
from pydub.effects import normalize

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
    :param parsed_qs: query string info. The important parameter is 'url' for link to an mp3. Might work with other
    formats!?! Also provides species name 's' which is used in caching
    :return: IOBytes that contains the wav data. The data is always gzipped to reduce the size of the large files.
    """

    # Constants
    max_clip_voice_msec = 14000  # For when voice intro ends and actual bird sounds start

    # Get from cache if can
    species = parsed_qs['s'][0]
    url = parsed_qs['url'][0]
    cache_file_name = 'audio_' + cache.file_identifier(url)
    cache_suffix = '.wav.gz'
    if cache.file_exists(cache_file_name, cache_suffix, species):
        return io.BytesIO(cache.read_from_cache(cache_file_name, cache_suffix, species))

    # Determine max length of clip to be returned
    max_clip_msec_param = parsed_qs.get('max_msec')
    if max_clip_msec_param is None or len(max_clip_msec_param) == 0:
        max_clip_msec = 30000  # Default value
    else:
        max_clip_msec = max_clip_msec_param[0]

    # Get the mp3 data
    mp3 = requests.get(url)

    # Process the sound. Just use first ~44 seconds so that processing doesn't get bogged down on really long clips
    sound = AudioSegment.from_mp3(BytesIO(mp3.content))[:max_clip_voice_msec + max_clip_msec]

    # Try to get rid of any voice introduction to the clip. The voice intros appear to be consistently
    # separated by half second or so of silence. Found that had to reduce the silence_thresh to -70.0 even
    # though the db of a non-silent clip was just -38. But at least it works. And found that it is really
    # important to set seek_step to 20 since that makes the function run 20x, though then the boundaries are
    # of course not determined as accurately. And found that needed small min_silence_len=50 so that would
    # work for ML106633 wav file.
    silent_portions = silence.detect_silence(sound, min_silence_len=50, silence_thresh=-70.0, seek_step=20)

    end_of_last_voice_silence = None
    special_end_found = None
    for silent_portion in silent_portions:
        start, stop = silent_portion

        # Look for last silence within the time that can have voice intro (max_clip_voice_msec).
        # Example is https://cdn.download.ams.birds.cornell.edu/api/v2/asset/62320/mp3&s=American+Golden%2DPlover
        if stop < max_clip_voice_msec:
            print(f'Trimming audio to get rid of voice intro, silence_stop={stop}')
            end_of_last_voice_silence = stop

        # Look for first silence past max_clip_voice_msec, which probably indicates a second voice.
        # Example is  https://cdn.download.ams.birds.cornell.edu/api/v2/asset/29385/mp3&s=Short-billed_Dowitcher
        if start > max_clip_voice_msec:
            print(f'Additional voice section found so trimming it off from the audio')
            special_end_found = start
            break

    # Trim the sound to get rid of voice parts
    non_voice_start = 0 if end_of_last_voice_silence is None else end_of_last_voice_silence
    non_voice_end = special_end_found # Works because then using sound[start:None]
    sound = sound[non_voice_start : non_voice_end]

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
    compressed_bytes = gzip.compress(buffer_bytes)
    cache.write_to_cache(compressed_bytes, cache_file_name, cache_suffix, species)

    print(f'Stored audio in file {cache.get_full_filename(cache_file_name, cache_suffix, species)} for url {url}')

    return io.BytesIO(compressed_bytes)
