import os
import sys

from utils import root

def download_nccos(y2003, y2007):

    dirname = os.path.join(root(), "nccos")
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    url = "https://www.nodc.noaa.gov/cgi-bin/OAS/prd/download/1329.1.1.tar.gz"
    out_zip = os.path.join(dirname, os.path.basename(url))
    out = os.path.join(dirname, "NOSbenthic")

    if not os.path.exists(out_zip) and not os.path.exists(out):
        os.system(f"curl {url} --output {out_zip}")
        os.system(f"tar -xvzf {out_zip}")
        os.system(f"mv {out_zip} {out}")

    if y2003:
        download_nccos2003()
    if y2007:
        download_nccos2007()


def download_nccos2007():
    dirname = os.path.join(root(), "nccos", "2007")
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    baseurl = "https://cdn.coastalscience.noaa.gov/datasets/e97/2007"
    tailurls = [
        # labels
        "aap/AccuracyAssessment.zip",
        "gvp/GroundValidation.zip",
        "shapes_benthic/Habitat_GIS_Data.zip",
        "shapes_shoreline/Shorelines.zip",
        # misc.
        "other/MHI_digital_elevation_model_hillshade_GIS_data.zip",
        # islands
        "mosaics/Hawaii_IKONOS.zip",
        "mosaics/Oahu_IKONOS.zip",
        "mosaics/Maui_IKONOS.zip",
        "mosaics/Kauai_IKONOS.zip",
        "mosaics/Lanai_IKONOS.zip",
        "mosaics/Molokai_IKONOS.zip",
        "mosaics/Niihau_IKONOS.zip",
        "mosaics/Kahoolawe_IKONOS.zip",
        "mosaics/Kaula_IKONOS.zip",
        "mosaics/MHI_satellite_image_mosaic_files-land.zip"
    ]

    for tailurl in tailurls:

        basename = os.path.dirname(tailurl)

        url = os.path.join(baseurl, tailurl)
        out = os.path.join(dirname, os.path.basename(tailurl))

        if not os.path.exists(out) and not os.path.exists(os.path.splitext(out)[0]):
            os.system(f"curl {url} --output {out}")
            os.system(f"unzip {out} -d {os.path.splitext(out)[0]}")


def download_nccos2003():
    pass

def download_soest():
    pass

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--nccos2003', action="store_true", default=False)
    parser.add_argument('--nccos2007', action="store_true", default=False)
    parser.add_argument('--soest', action="store_true", default=False)

    args = parser.parse_args()

    if args.nccos2003 or args.nccos2007:
        download_nccos(y2007=args.nccos2007, y2003=args.nccos2003)
    if args.soest:
        download_soest()
