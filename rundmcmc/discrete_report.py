import matplotlib.pyplot as plt
import matplotlib.patches as ptch
import geopandas as gp
import os
from collections import Counter

BLUE = '#0000FF'
YELLOW = '#FFFF00'
RED = '#FF0000'

data_folder = 'testData'
df = gp.read_file(os.path.join(data_folder, "mo_dists.geojson"))
discrete_perimeter = {}

def discrete_perim(df):
    df_district = df.dissolve(by = 'CD', as_index = False)
    for district_index in range(len(df_district)):
        tmp_district = df_district.iloc[district_index]
        district_boundary_units = df[df.geometry.intersects(tmp_district.geometry.boundary)]
        discrete_perimeter.update({tmp_district['CD']:len(district_boundary_units)})
    return(discrete_perimeter)

def discrete_area(df):
    return dict(Counter(df['CD']))
discrete_area(df)
