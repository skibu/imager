from PIL import Image, ImageOps, ImageEnhance
from PIL.Image import Quantize


def process_image_for_norns(img: Image, parsed_qs: dict) -> Image:
    """
    Process the image so it can be used on a Norns. This included:
      - cropping the image so that important center part emphasized
      - convert to gray scale
      - transform to proper size (128x64)
      - change colors so they are compatible with norne (4 bits of grayscale)
      - If a black on white image, invert colors so it looks better on Norns
      - return it as a png
    :type parsed_qs: object
    :param img: the image to process
    :param parsed_qs: query string that was used
    :return:
    """
    debug = parsed_qs.get('debug') is not None

    if debug:
        img.show()
        img_h = img.histogram()

    grayscale_img = grayscale(img, parsed_qs)
    if debug:
        grayscale_img.show('grayscale')
        grayscale_img_h = grayscale_img.histogram()

    inverted_image = invert_image_if_white_background(grayscale_img)
    if debug:
        inverted_image.show('possibly inverted')
        inverted_image_h = inverted_image.histogram()

    cropped_img = crop(inverted_image)
    if debug:
        cropped_img.show('cropped')
        cropped_img_h = cropped_img.histogram()

    shrunk_img = shrink_to_norns_size(cropped_img)
    if debug:
        shrunk_img.show('shrunk to Norms size')
        shrunk_img_h = shrunk_img.histogram()

    return shrunk_img


def shrink_to_norns_size(img: Image) -> Image:
    """
    Reduces image to proper size for the Norns, which is 128x64
    :param img:
    :return: image resized to max of 128x64
    """
    w = img.width
    h = img.height
    fraction = 64/img.height

    return img.resize((int(w * fraction), 64))


def has_white_background(img: Image) -> bool:
    """
    Determines if pixel has white background.
    :param img:
    :return: True if more than 20% of background is white
    """
    pixels_per_color_list = img.histogram()

    # When converting some images to grayscale can get a white value
    # that is not 255. For this situation consider 254 to be white.
    idx = 255
    white_index = None
    while white_index is None:
        white_index = img.palette.colors.get((idx, idx, idx))
        idx -= 1

    num_white_pixels = pixels_per_color_list[white_index]

    total_pixels = img.width * img.height

    # Return True if more than 20% of pixels are white
    return num_white_pixels > 0.2 * total_pixels


def invert_image_if_white_background(img: Image) -> Image:
    """
    Determines if image has white background. If it does then it inverts it so
    that can crop out white border and also so because inverted image will
    display better on a Norns bright white screen.
    :param img: image to be inverted
    :return: inverted image if white background. Otherwise the original image
    """
    if has_white_background(img):
        # Need to invert image since getbbox() crops out black border, not white.
        # But the ImageOps.invert() function doesn't work for 'P' mode images. So convert
        # image back to 'L' mode.
        return ImageOps.invert(img.convert('L'))
    else:
        return img


def crop(img: Image) -> Image:
    """
    Crop the top and bottom of the image so that the subject matter is more prominent in the tiny Norns display.
    It is more efficient to process a grey scale image. Therefore, should convert image to grayscale first,
    and also invert color if it had a white background.
    :param img:
    :return: cropped image
    """
    horiz_fraction = 0.0 # currently not cropping horizontally so image will be as wide as possible
    vert_fraction = 0.08

    # First crop out white border.
    non_whitespace_box = (left, upper, right, lower) = img.getbbox()
    (width, height) = img.size
    if left != 0 or upper != 0 or right != width or lower != height:
        # Crop out white image
        img = img.crop(non_whitespace_box)

        # Since already cropping out whitespace don't need to crop as much more
        horiz_fraction = 0.0
        vert_fraction = 0.04

    # Now crop margins a bit to emphasize important part of picture
    (orig_width, orig_height) = img.size

    left = orig_width * horiz_fraction
    upper = orig_height * vert_fraction
    right = orig_width * (1 - horiz_fraction)
    lower = orig_height * (1 - vert_fraction)

    # Make sure image not too wide. The Norns screen is 128x64.
    # Therefore if new width is more than twice the new height then
    # need to reduce the width proportionally.
    new_height = lower - upper
    new_width = right - left
    width_to_height_ratio = new_width / new_height
    if width_to_height_ratio > 2.0:
        horizontal_adjustment = new_width - (new_width * 2.0 / width_to_height_ratio)
        left += horizontal_adjustment / 2
        right -= horizontal_adjustment / 2

    box = (left, upper, right, lower)
    return img.crop(box)


def grayscale(img: Image, parsed_qs: dict) -> Image:
    """
    Convert image to grayscale and then reduces it to 16 gray levels, which is what Norns needs
    :type parsed_qs: object
    :param img: the image to process
    :param parsed_qs: query string that was used
    :return: image converted to 16 color grayscale
    """
    debug = parsed_qs.get('debug') is not None

    # Convert to grayscale
    grayscale_img = img.convert('L')
    if debug:
        grayscale_img.show('grayscale temp')
        grayscale_img_h = grayscale_img.histogram()

    # Increase contrast of image so that it looks better on Norns display with only 16 gray scales.
    # Importantly, this also for some reason causes a palette with evenly spaced levels to be used,
    # which is what the Norns needs.
    contrast = ImageEnhance.Contrast(grayscale_img)
    contrasted_image = contrast.enhance(1.5)
    if debug:
        contrasted_image.show('contrasted')
        contrasty_image_h = contrasted_image.histogram()

    # Reduce to just 16 colors. Use MAXCOVERAGE so that gray scales used are even.
    # Note that calling quantize() converts images from a 'L' type without a palette to an
    # 'P' type with a palette, and the palette can be in any order for the colors.
    sixteen_color_img = contrasted_image.quantize(16, method=Quantize.MAXCOVERAGE)
    if debug:
        sixteen_color_img.show('16 color')
        sixteen_color_img_h = sixteen_color_img.histogram()

    return sixteen_color_img
