# Maps.py
import os
import folium
import geopandas as gpd
import rasterio  
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
import numpy as np

class MAPS:
    """
    A class to handle map operations using Folium and GeoPandas.
    
    Attributes:
        map (folium.Map): The Folium map object.
        map_html (str): Path to the saved HTML file of the map.
    
    Methods:
        default_tile_map(dir): Creates a default map with OpenStreetMap tiles.
        add_tile_layer(tile_url, dir): Adds a custom tile layer to the map.
        load_survey_lines(coordinates, dir, color="blue"): Loads survey lines onto the map.
        load_vector_data(file_path, dir): Loads vector data from a file and adds it to the map.
        load_raster_data(file_path, dir): Loads raster data from a file and adds it to the map.
    """

    def __init__(self):
            self.map = None 
            self.map_html = None 

    def default_tile_map(self, dir):
        """
        Creates a default map with OpenStreetMap tiles and saves it as an HTML file.
        Args:
            dir (str): Directory where the map HTML file will be saved.
        Returns:
            tuple: A tuple containing the Folium map object and the path to the saved HTML file.
        Raises:
            Exception: If there is an error while creating the map or saving the HTML file.
        """
        try:
                
            # Create the default map
            center = [0, 0]  # Default center of the map
            zoom = 2  # Default zoom level
            self.map = folium.Map(location=center, zoom_start=zoom, tiles = "OpenStreetMap")
            
            # Define paths for map assets
            print(f"output dir: {dir}")

            # Save the map as an HTML file
            self.map_html = os.path.join(dir, "default_map.html")
            self.map.save(self.map_html)
            return self.map, self.map_html
        except Exception as e:
            raise Exception(f"Error, Failed to load default tile layer: {e}")
    
    
    def add_tile_layer(self, tile_url, dir):
        """
        Adds a custom tile layer to the map and saves it as an HTML file.
        Args:
            tile_url (str): URL of the custom tile layer to be added.
            dir (str): Directory where the map HTML file will be saved.
        Returns:
            tuple: A tuple containing the Folium map object and the path to the saved HTML file.
        Raises:
            Exception: If there is an error while adding the tile layer or saving the HTML file.
        """
        try:
            # Clear the current map and add the new tile layer
            self.map = folium.Map(location=[0, 0], zoom_start=2, tiles=tile_url, attr="Custom Layer")

            # Define paths for map assets
            print(f"output dir: {dir}")

            # Save the map as an HTML file
            self.map_html = os.path.join(dir, "default_map.html")
            self.map.save(self.map_html)
            return self.map, self.map_html
        except Exception as e:
            raise Exception(f"Error, Failed to add the new tile layer: {e}")
    
    def load_survey_lines(self, coordinates, dir, color="red"):
        """
        Loads survey lines onto the map using given coordinates and saves it as an HTML file.
        Args:
            coordinates (list): List of coordinates for the survey lines.
            dir (str): Directory where the map HTML file will be saved.
            color (str): Color of the survey lines. Default is "blue".
        Returns:
            tuple: A tuple containing the Folium map object and the path to the saved HTML file.
        Raises:
            Exception: If there is an error while loading the survey lines or saving the HTML file.
        """
       
        try:
            if not self.map:
                first_latlon = coordinates[0]
                self.map = folium.Map(location=first_latlon, zoom_start=13)
            
            # Add survey lines to the map
            folium.PolyLine(locations=coordinates, color=color, weight=2.5).add_to(self.map)

            # Define paths for map assets
            print(f"output dir: {dir}")

            # Save the map as an HTML file
            self.map_html = os.path.join(dir, "default_map.html")
            self.map.save(self.map_html)
            return self.map, self.map_html
        except Exception as e:
            raise Exception(f"Error, Failed to load survey data: {e}")

    def load_mag_lines(self, coordinates, dir, color="blue"):
        
        try:

            # Determine map center using the first coordinate
            first_latlon = list(coordinates.values())[0][0]
            self.map = folium.Map(location=[first_latlon[1], first_latlon[0]], zoom_start=13)

            # Add each line to the map
            for line, coords in coordinates.items():
                folium.PolyLine(locations=[(lat, lon) for lon, lat in coords],
                                tooltip=f"Line {line}",
                                color=color).add_to(self.map)

            # Fit map bounds to all points
            all_points = [pt for coords in coordinates.values() for pt in coords]
            lats, lons = zip(*[(lat, lon) for lon, lat in all_points])
            self.map.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

            # Define paths for map assets
            print(f"output dir: {dir}")

            # Save the map as an HTML file
            self.map_html = os.path.join(dir, "default_map.html")
            self.map.save(self.map_html)
            return self.map, self.map_html
        
        except Exception as e:
            raise Exception(f"Error, Failed to load magnetic survey data: {e}")

    def load_vector_data(self, file_path, dir):
        """
        Loads vector data from a file and adds it to the map, reprojecting to EPSG:4326.
        Args:
            file_path (str): Path to the vector data file (e.g., GeoJSON, Shapefile).
            dir (str): Directory where the map HTML file will be saved.
        Returns:
            tuple: A tuple containing the Folium map object and the path to the saved HTML file.
        Raises:
            Exception: If there is an error while loading the vector data or saving the HTML file.
        """
        try:
            gdf = gpd.read_file(file_path)
            
            # Check the current CRS
            print(f"Original CRS: {gdf.crs}")
            
            # Reproject to the target CRS
            gdf_transformed = gdf.to_crs("EPSG:4326")
            print(f"Transformed CRS: {gdf_transformed.crs}")

            for _, row in gdf_transformed.iterrows():
                if row.geometry.type == "Point":
                    folium.Marker(location=[row.geometry.y, row.geometry.x]).add_to(self.map)
                elif row.geometry.type in ["LineString", "Polygon"]:
                    folium.GeoJson(data=row.geometry).add_to(self.map)

            # Define paths for map assets
            print(f"output dir: {dir}")

            # Save the map as an HTML file
            self.map_html = os.path.join(dir, "default_map.html")
            self.map.save(self.map_html)
            return self.map, self.map_html
        
        except Exception as e:
            raise Exception(f"Error, Failed to load vector data: {e}")
    
    def load_raster_data(self, file_path, dir):
        """
        Loads raster data from a file and adds it to the map, reprojecting to EPSG:4326.
        Args:
            file_path (str): Path to the raster data file (e.g., GeoTIFF).
            dir (str): Directory where the map HTML file will be saved.
        Returns:
            tuple: A tuple containing the Folium map object and the path to the saved HTML file.
        Raises:
            Exception: If there is an error while loading the raster data or saving the HTML file.
        """
        try:
            # Ensure the output directory exists
            os.makedirs(dir, exist_ok=True)

            # Open the raster file
            with rasterio.open(file_path) as src:
                print(f"{file_path} CRS: {src.crs}")
                print(f"{file_path} Bounds: {src.bounds}")

                # Calculate the transform and metadata for the target CRS (EPSG:4326)
                transform, width, height = calculate_default_transform(
                    src.crs, "EPSG:4326", src.width, src.height, *src.bounds
                )
                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': "EPSG:4326",
                    'transform': transform,
                    'width': width,
                    'height': height
                })

                # Reproject raster
                reprojected_data = np.empty((src.count, height, width), dtype=src.dtypes[0])
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=reprojected_data[i - 1],
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs="EPSG:4326",
                        resampling=Resampling.nearest
                    )

                # Normalize raster data for single-band visualization
                raster_normalized = (reprojected_data[0] - np.min(reprojected_data[0])) / (
                    np.max(reprojected_data[0]) - np.min(reprojected_data[0])
                )
                raster_normalized = (raster_normalized * 255).astype(np.uint8)

                # Calculate bounds
                bounds = array_bounds(kwargs['height'], kwargs['width'], kwargs['transform'])
                min_lon, min_lat, max_lon, max_lat = bounds

                # Initialize the map if not set
                if not hasattr(self, "map") or self.map is None:
                    center_lat = (min_lat + max_lat) / 2
                    center_lon = (min_lon + max_lon) / 2
                    self.map = folium.Map(location=[center_lat, center_lon], zoom_start=12)

                # Add raster as an overlay
                folium.raster_layers.ImageOverlay(
                    image=raster_normalized,
                    bounds=[[max_lat, min_lon], [min_lat, max_lon]],
                    opacity=0.6
                ).add_to(self.map)

                # Add layer control to the map
                folium.LayerControl().add_to(self.map)

                # Save the map
                self.map_html = os.path.join(dir, "default_map.html")
                self.map.save(self.map_html)

                return self.map, self.map_html

        except Exception as e:
            raise Exception(f"Error: Failed to load raster data: {e}")
