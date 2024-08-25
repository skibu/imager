# Imager
Imager is python based webserver for serving up data to the 
[Taweeet Norns application](https://github.com/skibu/norns). It provides JSON data, 
PNG images, and audio WAV files that drive Taweet. Most of the images and audio are
obtained from [http://ebird.org](http://ebird.org) . Imager processes any color image
into a PNG that can be used in a Norns via scaling, cropping, and modifying the colors. 
And Imager also takes in readily available mp3 files and converts them to WAV files, 
which is the only format of audio file that a Norns can use.

## Address
Currently the main Imager server can be accessed at http://taweeet.mywire.org/ .
And example call is [http://taweeet.mywire.org/allSpeciesList](http://taweeet.mywire.org/allSpeciesList)

## Server Setup
Imager can be run on almost any computer. You need at least Python 3.10. Useful 
instructions for upgrading to a specific version of Python are at 
 [https://itheo.tech/upgrading-to-python-312-on-your-raspberry-pi](https://itheo.tech/upgrading-to-python-312-on-your-raspberry-pi)

You should also make sure that pip has been updated. Can use:
`pip3.12 install —upgrade pip`
or
`python3 -m pip install --upgrade pip`

Copy pip to PATH: 
`sudo cp ~/.local/bin/pip /usr/bin/pip`

You also need the following libraries:
```
sudo apt-get install libjpeg-dev
python3 -m pip install --upgrade Pillow # or: pip install pillow
pip install html-table-parser-python3
pip install requests
pip install pydub
sudo pip install bs4
```

### Running app
First get the application from github:
`git clone https://github.com/skibu/imager.git`

Then run it via either:
`python3 imager/main.py`
or
`imager/main.py`

### Auto startup
Important consideration is to have the application start automatically at bootup. 
If using a Raspberry Pi one can simply modify the /etc/rc.local and add:

```
# Start imager, as user pi instead of root.
# Since /usr/local is owned by root need to first make sure
# that /usr/local/imagerCache is created by user root, and
# then change ownership of the directory to user pi so that
# when imager is run as user pi it can write to the directory.
# Also, when running the app, need to first cd into the imager
# directory so that the supplemental data in the data sub-directory
# can be found.
mkdir -p /usr/local/imagerCache
chown pi /usr/local/imagercache chgrp pi /usr/local/imagerCache
sudo -H -u pi bash -c 'cd /home/pi/imager/; /usr/bin/python3 main.py' &
```
