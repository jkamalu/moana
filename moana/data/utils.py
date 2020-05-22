import os
import math

import yaml


def root():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


def WGS84():
    spatial_reference = SpatialReference(4326) # wkid code for wgs84
    return spatial_reference


def _capitalize(x):
    return x[0].upper() + x[1:]


def load_config(filename):
    with open("config.yml", "rt") as file:
        config = yaml.load(file.read(), Loader=yaml.Loader)
    return config


def path_to_shoreline(island, source="nccos", year="2007"):
    shapefile = f"{_capitalize(island)}{os.extsep}shp"
    return os.path.join(root(), source, year, "Shorelines", "Shorelines", shapefile)


def path_to_habitat(island, source="nccos", year="2007"):
    if island == "niihau" or island == "kaula":
        island = "niihau_kaula"
    shapefile = f"{island}{os.extsep}shp"
    return os.path.join(root(), source, year, "Habitat_GIS_Data", shapefile)


def path_to_mosaic(island, source="nccos", year="2007"):
    ikonos = f"{_capitalize(island)}_IKONOS"
    dirname = os.path.join(root(), source, year, ikonos)
    paths = []
    for fname in os.listdir(dirname):
        fname_lower = fname.lower()
        if fname_lower.startswith(island) and fname_lower.endswith(f"{os.extsep}tif"):
            paths.append(os.path.join(dirname, fname))
    return paths
    
    shapefile = f"{_capitalize(island)}{os.extsep}shp"
    return os.path.join(root(), source, year, ikonos, shapefile)


def path_to_images(source="nccos", year="2007"):
    images = os.path.join(root(), source, year, "masks")
    if not os.path.exists(o,ages):
        os.makedirs(images)
    return images

    
def path_to_masks(source="nccos", year="2007"):
    masks = os.path.join(root(), source, year, "masks")
    if not os.path.exists(masks):
        os.makedirs(masks)
    return masks


def path_to_temp(subfolder, source="nccos", year="2007"):
    temp = os.path.join(root(), source, year, "temp")
    if not os.path.exists(temp):
        os.makedirs(temp)
    return temp
