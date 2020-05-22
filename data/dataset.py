import os
import shutil

from tqdm.notebook import tqdm

from arcpy import (
    env,
    Array,
    Polygon,
    Buffer_analysis,
    EliminatePolygonPart_management,
    GeneratePointsAlongLines_management,
    FeatureEnvelopeToPolygon_management,
    Clip_management,
    FeatureToRaster_conversion
)
from arcpy.da import UpdateCursor, SearchCursor, TableToNumPyArray

from utils import (
    path_to_shoreline, 
    path_to_mosaic, 
    path_to_habitat, 
    path_to_images,
    path_to_masks,
    path_to_temp
)


def create_shoreline_rectangles(islands, config):
    
    size = config["pix_res"] * config["data_extraction"]["pix_dim"]
    step = int(size * (1 - config["data_extraction"]["overlap"]))
    
    # remove "islands" along shoreline
    _trim_shoreline(islands)
    
    # buffer shoreline 
    _buffer_shoreline(islands, size)
    
    # remove interior polygons
    _filter_shoreline(islands)
    
    # generate points along shoreline
    _pointilate_shoreline(islands, size, step)
    
    # buffer shoreline points
    _buffer_shoreline_points(islands, size)
    
    # convert circular buffer to square
    _envelop_shoreline_points(islands)
    
    
def create_image_rectangles(islands):
    
    for island in islands:
        
        # get path to image mosaic
        in_raster = path_to_mosaic(island)
        if len(in_raster) > 1:
            print(f"Please merge {island} mosaics. Skipping...")
            continue
        
        # get rectangle extents
        path_to_rects = os.path.join(path_to_temp(), "rects5", f"{island}.shp")
        with SearchCursor(path_to_rects, ["OID@", "SHAPE@"]) as cursor:
            rectangles = []
            for oid, rect in cursor:
                extent = " ".join(str(rect.extent).split()[:4])
                rectangles.append((oid, extent))
        
        # clip image mosaic to rectangles and save
        for oid, extent in tqdm(rectangles):
            path_to_raster = os.path.join(path_to_images(), f"{island}-{oid}.png")
            Clip_management(
                in_raster[0],
                extent,
                path_to_raster
            )
        
        # delete all metadata
        _path_to_images = path_to_images()
        for name in os.listdir(_path_to_images):
            if not name.endswith("png"):
                os.remove(os.path.join(_path_to_images, name))
                
                
def create_mask_rectangles(islands):
    
    for island in islands:
        
        # get path to mask raster
        in_raster = os.path.join(path_to_temp(), "habitats", f"{island}.tif")
        
        # get rectangle extents
        path_to_rects = os.path.join(path_to_temp(), "rects5", f"{island}.shp")
        with SearchCursor(path_to_rects, ["OID@", "SHAPE@"]) as cursor:
            rectangles = []
            for oid, rect in cursor:
                extent = " ".join(str(rect.extent).split()[:4])
                rectangles.append((oid, extent))
        
        # clip mask raster to rectangles and save
        for oid, extent in tqdm(rectangles):
            path_to_raster = os.path.join(path_to_masks(), f"{island}-{oid}.png")
            Clip_management(
                in_raster,
                extent,
                path_to_raster
            )
            
        # delete all metadata
        _path_to_masks = path_to_masks()
        for name in os.listdir(_path_to_masks):
            if not name.endswith("png"):
                os.remove(os.path.join(_path_to_masks, name))


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
        out_features = os.path.join(path_to_temp(), "rects1", island) 
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
        in_features = os.path.join(path_to_temp(), "rects1", f"{island}.shp") 
        out_features = os.path.join(path_to_temp(), "rects2", island) 
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
        in_features = os.path.join(path_to_temp(), "rects2", f"{island}.shp") 
        out_features = os.path.join(path_to_temp(), "rects3", island) 
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
        in_features = os.path.join(path_to_temp(), "rects3", f"{island}.shp") 
        out_features = os.path.join(path_to_temp(), "rects4", island) 
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
        in_features = os.path.join(path_to_temp(), "rects4", f"{island}.shp") 
        out_features = os.path.join(path_to_temp(), "rects5", island) 
        shutil.rmtree(out_features, ignore_errors=True)
        os.makedirs(os.path.dirname(out_features), exist_ok=True)
        FeatureEnvelopeToPolygon_management(
            in_features,
            out_features
        )

        
def _rasterize_habitat(islands):
    for island in islands:
        snap_raster = path_to_mosaic(island)
        if len(snap_raster) > 1:
            print(f"Please merge {island} mosaics. Skipping...")
            continue
        # use the cell size of the mosaic for conversion to raster
        env.snapRaster = snap_raster[0]
        in_features = path_to_habitat(island)
        out_raster = os.path.join(path_to_temp(), "habitats", f"{island}.tif")
        FeatureToRaster_conversion(
            in_features, 
            "M_STRUCT", 
            out_raster, 
            "#"
        )
