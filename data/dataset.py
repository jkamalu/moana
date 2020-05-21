import os
import shutil

from tqdm.notebook import tqdm

from arcpy import (
    Array,
    Polygon,
    Buffer_analysis,
    EliminatePolygonPart_management,
    GeneratePointsAlongLines_management,
    FeatureEnvelopeToPolygon_management,
    Clip_management
)
from arcpy.da import UpdateCursor, SearchCursor, TableToNumPyArray

from utils import path_to_shoreline, path_to_features, path_to_mosaic


def _trim_shoreline(islands):
    """
    Trim the shoreline of micro-islands. This makes 
    permanent changes to the Shapefile.
    """
    for island in islands:
        path = path_to_shoreline(island)
        pair = max(TableToNumPyArray(path, ["OID@", "SHAPE@AREA"]), key=lambda p: p[1])
        with UpdateCursor(path, ["OID@", "SHAPE@"]) as cursor:
            for row in cursor:
                if row[0] != pair[0]:
                    cursor.deleteRow()
                else:
                    row_new = Array()
                    for part in row[1]:
                        part_new = Array()
                        for point in part:
                            if point is None:
                                break
                            part_new.add(point)
                        row_new.add(part_new)
                    row[1] = Polygon(row_new)
                    cursor.updateRow(row)
                    
                    
def _buffer_shoreline(islands, size):
    """
    Pad the shoreline with a buffer that is half the
    desired width of the image data.
    """
    for island in islands:
        in_features = path_to_shoreline(island)
        out_features = path_to_features("temp1", island)
        shutil.rmtree(out_features, ignore_errors=True)
        os.makedirs(os.path.dirname(out_features), exist_ok=True)
        Buffer_analysis(
            in_features, 
            out_features, 
            buffer_distance_or_field="{} METERS".format(size // 2), 
            dissolve_option="ALL"
        )
        
        
def _filter_shoreline(islands):
    """
    Remove the fully esconced inner buffer polygon, 
    leaving the outer buffer polygon.
    """
    for island in islands:
        in_features = path_to_features("temp1", island, ext="shp")
        out_features = path_to_features("temp2", island)
        shutil.rmtree(out_features, ignore_errors=True)
        os.makedirs(os.path.dirname(out_features), exist_ok=True)
        EliminatePolygonPart_management(
            in_features, 
            out_features, 
            condition="PERCENT",
            part_area_percent=99, 
            part_option="ANY"
        )
        

def _pointilate_shoreline(islands, size, step):
    """
    Generate points along the shoreline at a fixed
    interval.
    """
    for island in islands:
        in_features = path_to_features("temp2", island, ext="shp")
        out_features = path_to_features("temp3", island)
        shutil.rmtree(out_features, ignore_errors=True)
        os.makedirs(os.path.dirname(out_features), exist_ok=True)        
        GeneratePointsAlongLines_management(
            in_features, 
            out_features,
            Point_Placement="DISTANCE", 
            Distance="{} METERS".format(step), 
        )

        
def _buffer_shoreline_points(islands, size):
    """
    Pad the points along the shoreline with a buffer 
    that is half the desired width of the image data.
    
    Note: Almost identical to above buffer analysis.
    """
    for island in islands:
        in_features = path_to_features("temp3", island, ext="shp")
        out_features = path_to_features("temp4", island)
        shutil.rmtree(out_features, ignore_errors=True)
        os.makedirs(os.path.dirname(out_features), exist_ok=True)
        Buffer_analysis(
            in_features, 
            out_features,
            buffer_distance_or_field="{} METERS".format(size // 2)
        )
        

def _envelop_shoreline_points(islands):
    """
    Envelop point buffers (circular polygons) in rectangular 
    polygons.
    """
    for island in islands:
        in_features = path_to_features("temp4", island, ext="shp")
        out_features = path_to_features("rects", island)
        shutil.rmtree(out_features, ignore_errors=True)
        os.makedirs(os.path.dirname(out_features), exist_ok=True)
        FeatureEnvelopeToPolygon_management(
            in_features,
            out_features
        )


def create_shoreline_rectangles(islands, config):
    size = config["pix_res"] * config["data_extraction"]["pix_dim"]
    step = int(size * (1 - config["data_extraction"]["overlap"]))
    _trim_shoreline(islands)
    _buffer_shoreline(islands, size)
    _filter_shoreline(islands)
    _pointilate_shoreline(islands, size, step)
    _buffer_shoreline_points(islands, size)
    _envelop_shoreline_points(islands)
    
    
def create_raster_rectangles(islands, ext="png"):
    images = path_to_features("images")
    for island in islands:
        in_raster = path_to_mosaic(island)
        if len(in_raster) > 1:
            print(f"Please merge {island} mosaics before extracting raster rectangles. Skipping...")
            continue
        path_to_rects = path_to_features("rects", island, ext="shp")
        if not os.path.exists(path_to_rects):
            print(f"Please create {island} shoreline rectangles before extracting raster rectangles. Skipping...")
            continue           
        with SearchCursor(path_to_rects, ["OID@", "SHAPE@"]) as cursor:
            rectangles = [(oid, " ".join(str(rect.extent).split()[:4])) for oid, rect in cursor]
        for oid, extent in tqdm(rectangles):
            out_raster = path_to_features("images", f"{island}-{oid}", ext=ext)
            Clip_management(
                in_raster[0],
                extent,
                out_raster
            )
        for name in os.listdir(images):
            if not name.endswith(ext):
                os.remove(os.path.join(images, name))
