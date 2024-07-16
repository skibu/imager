from PIL import Image, ImageOps, ImageEnhance
from PIL.Image import Quantize


def process_image_for_norns(img: Image) -> Image:
    """
    Process the image so it can be used on a Norne. Th is included:
      - cropping the image so that important center part emphasized
      - convert to gray scale
      - transform to proper size (128x64)
      - change colors so they are compatible with norne (4 bits of grayscale)
      - If a black on white image, invert colors so it looks better on Norns
      - return it as a png
    :param img:
    :return:
    """
    img.show() # FIXME
    img_h = img.histogram() # FIXME

    grayscale_img = grayscale(img)
    grayscale_img.show('grayscale') # FIXME
    grayscale_img_h = grayscale_img.histogram() # FIXME

    inverted_image = invert_image_if_white_background(grayscale_img)
    inverted_image.show('possibly inverted')
    inverted_image_h = inverted_image.histogram() # FIXME

    cropped_img = crop(inverted_image)
    cropped_img.show('cropped') # FIXME
    cropped_img_h = cropped_img.histogram() # FIXME

    shrunk_img = shrink_to_norns_size(cropped_img)
    shrunk_img.show('shrunk to Norms size') # FIXME
    shrunk_img_h = shrunk_img.histogram() # FIXME

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
    It is more efficient to process a grey scale image. Therefore should convert image to grayscale first,
    and also invert color if it had a white background.
    :param img:
    :return: cropped image
    """
    horiz_fraction = 0.15
    vert_fraction = 0.15

    # First crop out white border.
    non_whitespace_box = (left, upper, right, lower) = img.getbbox()
    (width, height) = img.size
    if left != 0 or upper != 0 or right != width or lower != height:
        # Crop out white image
        img = img.crop(non_whitespace_box)

        # Since already cropping out whitespace don't need to crop as much more
        horiz_fraction = 0.05
        vert_fraction = 0.05

    # Now crop margins a bit to emphasize important part of picture
    (orig_width, orig_height) = img.size
    box = (left, upper, right, lower) = (
        orig_width * horiz_fraction, orig_height * vert_fraction, orig_width * (1 - horiz_fraction), orig_height * (1 - vert_fraction))

    return img.crop(box)


def grayscale(img: Image) -> Image:
    """
    Convert image to grayscale and then reduces it to 16 gray levels, which is what Norns needs
    :param img:
    :return: image converted to 16 color grayscale
    """
    # Convert to grayscale
    grayscale_img = img.convert('L');
    grayscale_img.show('grayscale temp') # FIXME
    grayscale_img_h = grayscale_img.histogram() # FIXME

    # Increase contrast of image so that it looks better on Norns display with only 16 gray scales.
    # Importantly, this also for some reason causes a palette with evenly spaced levels to be used,
    # which is what the Norns needs.
    contrast = ImageEnhance.Contrast(grayscale_img)
    contrasted_image = contrast.enhance(1.5)
    contrasty_image_h = contrasted_image.histogram()
    contrasted_image.show('contrasted')

    # Reduce to just 16 colors. Use MAXCOVERAGE so that gray scales used are even.
    # Note that calling quantize() converts images from a 'L' type without a palette to an
    # 'P' type with a palette, and the palette can be in any order for the colors.
    sixteen_color_img = contrasted_image.quantize(16, method=Quantize.MAXCOVERAGE)
    sixteen_color_img.show('16 color') #FIXME
    sixteen_color_img_h = sixteen_color_img.histogram() #FIXME

    return sixteen_color_img