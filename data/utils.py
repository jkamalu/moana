import os
import math

import pyaml

from arcpy import Array, Polygon, Polyline, SpatialReference
from arcpy.da import UpdateCursor

def ROOT():
    return os.path.dirname(os.path.abspath(__file__))

def WKID():
    return 4326 # wkid code for wgs84

def load_config(filename):
    with open("config.yml", "rt") as file:
        config = pyaml.yaml.unsafe_load(file.read())
    return config

def path_to_shoreline(island, source="nccos", year="2007"):
    shapefile = f"{_capitalize(island)}{os.extsep}shp"
    return os.path.join(ROOT(), source, year, "Shorelines", "Shorelines", shapefile)


def path_to_habitat(island, source="nccos", year="2007"):
    if island == "niihau" or island == "kaula":
        island = "niihau_kaula"
    shapefile = f"{island}{os.extsep}shp"
    return os.path.join(ROOT(), source, year, "Habitat_GIS_Data", shapefile)


def path_to_mosaic(island, source="nccos", year="2007"):
    ikonos = f"{_capitalize(island)}_IKONOS"
    dirname = os.path.join(ROOT(), source, year, ikonos)
    paths = []
    for fname in os.listdir(dirname):
        fname_lower = fname.lower()
        if fname_lower.startswith(island) and fname_lower.startswith(f"{os.extsep}shp"):
            paths.append(os.path.join(dirname, fname))
    return paths
    
    shapefile = f"{_capitalize(island)}{os.extsep}shp"
    return os.path.join(ROOT(), source, year, ikonos, shapefile)


def project_to_wkid(geometry):
    """
    Project an ArcPy Geometry to wkid (longitude, latitude)
    """
    wkid = 4326 # wkid code for wgs84
    spatial_reference = SpatialReference(wkid)
    return geometry.projectAs(spatial_reference)


def remove_inner_polygons(path_to_shapefile, feature_id):
    """
    Update the shapefile feature, keep only the exterior
    vertices.
    
    Note: Makes permanent edits to the shapefile. Raw 
    shorelines need this preprocessing.
    """
    updateCursor = UpdateCursor(path_to_shapefile, ["SHAPE@"], where_clause=f"FID = {feature_id}")
    updateRow = next(updateCursor)
    arr_old = updateRow[0]
    arr_new = Array()
    for part_old in arr_old:
        part_new = Array()
        for point in part_old:
            if point is None:
                break
            part_new.add(point)
        arr_new.add(part_new)
    poly_new = Polygon(arr_new)
    updateRow[0] = poly_new
    updateCursor.updateRow(updateRow)


def isoscelese_vertex_point(polyline, height):
    """
    Gets the endpoint of the line segment of a specified length
    which bisects (but does not cross) the Polyline. 
    """    
    
    assert polyline.spatialReference.name != "Unknown"
    
    midpoint = polyline.positionAlongLine(0.5, use_percentage=True)
    
    dY = polyline.firstPoint.Y - polyline.lastPoint.Y
    dX = polyline.firstPoint.X - polyline.lastPoint.X
    
    angle = math.atan2(dY, dX) * 180 / math.pi # convert to degrees
    
    vertex = midpoint.pointFromAngleAndDistance(angle + 90, height, method="PLANAR")
    
    return vertex
    
    
    