import os
import math

import yaml

from arcpy import Array, Polygon, Polyline, PointGeometry, SpatialReference
from arcpy.da import UpdateCursor

def ROOT():
    return os.path.dirname(os.path.abspath(__file__))


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
        if fname_lower.startswith(island) and fname_lower.endswith(f"{os.extsep}tif"):
            paths.append(os.path.join(dirname, fname))
    return paths
    
    shapefile = f"{_capitalize(island)}{os.extsep}shp"
    return os.path.join(ROOT(), source, year, ikonos, shapefile)


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


def extract_rectangle_v1(point_A, point_B, height):
    """
    Note: Buggy and shortsighted... Need to rotate raster to extract proper
    """    
    
    assert point_A.spatialReference.name != "Unknown"
    assert point_B.spatialReference.name != "Unknown"
    
    dY = point_B.firstPoint.Y - point_A.firstPoint.Y
    dX = point_B.firstPoint.X - point_A.firstPoint.X
    
    angle = math.atan2(dY, dX) * 180 / math.pi # convert to degrees
    
    point_D = point_A.pointFromAngleAndDistance(angle - 90, height, method="PLANAR")
    point_C = point_B.pointFromAngleAndDistance(angle - 90, height, method="PLANAR")
    
    return point_A, point_B, point_C, point_D


def extract_rectangle_v2(point_A, size):
    """
        
    """    
    
    assert point_A.spatialReference.name != "Unknown"
    

    return point_A, point_B, point_C, point_D
    

def _get_segment_endpoint(segment, point_A, lower, upper, distance, tol):
    """
    Recursive binary search helper function.
    """
    
    position = (upper + lower) / 2
    point_B = segment.positionAlongLine(position)
    
    distance_AB = point_A.distanceTo(point_B)
    
    if abs(distance_AB - distance) < tol:
        return point_B
    elif distance_AB > distance:
        return _get_segment_endpoint(segment, point_A, lower, position, distance, tol)
    else:
        return _get_segment_endpoint(segment, point_A, position, upper, distance, tol)

    
def get_segment_endpoint(polyline, start_measure, distance, perimeter, tol):
    """
    Get the point lying on the polyline at a certain
    Cartesian distance form the point which lies at
    `start_measure` distance along the polyline (within
    a certain tolerance).
    
    Return None when the point lies beyond the end of
    the polyline.
    """
    start_point = polyline.positionAlongLine(start_measure)
    steps = 2 # lowest possible value by triangle inequality
    
    while start_measure + distance * steps < perimeter:
        end_point_estimate = polyline.positionAlongLine(start_measure + distance * steps)
        if start_point.distanceTo(end_point_estimate) >= distance:
            end_measure = start_measure + distance * steps
            break
        steps += 1
        
    try:
        segment = polyline.segmentAlongLine(end_measure - distance, end_measure)
        end_point = _get_segment_endpoint(
            segment, 
            start_point,
            0, 
            distance, 
            distance,
            tol
        )
        return end_point
    except UnboundLocalError:
        return None
