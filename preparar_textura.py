from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from PIL import Image

dem_path = Path("data/lola_dem.tif")
photo_path = Path("data/lroc_south_pole.tif")
output = Path("static/data/lroc_texture.png")

N = 2048

with rasterio.open(dem_path) as dem, \
     rasterio.open(photo_path) as photo:

    print("DEM CRS:", dem.crs)
    print("LROC CRS:", photo.crs)

    if dem.crs is None or photo.crs is None:
        raise RuntimeError(
            "Faltan coordenadas geográficas."
        )

    target_transform = dem.transform * \
        rasterio.Affine.scale(
            dem.width / N,
            dem.height / N
        )

    destination = np.full(
        (N, N), np.nan, dtype=np.float32
    )

    reproject(
        source=rasterio.band(photo, 1),
        destination=destination,
        src_transform=photo.transform,
        src_crs=photo.crs,
        src_nodata=photo.nodata,
        dst_transform=target_transform,
        dst_crs=dem.crs,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear
    )

valid = np.isfinite(destination)

if not valid.any():
    raise RuntimeError(
        "No hay superposición entre LOLA y LROC."
    )

low, high = np.percentile(
    destination[valid], [2, 98]
)

if high <= low:
    raise RuntimeError(
        "La imagen no tiene contraste suficiente."
    )

gray = np.clip(
    (destination-low)/(high-low)*255,
    0, 255
).astype(np.uint8)

# Transparencia para zonas sin datos.
alpha = np.where(valid, 255, 0).astype(np.uint8)

rgba = np.stack(
    [gray, gray, gray, alpha],
    axis=-1
)

Image.fromarray(rgba, "RGBA").save(output)

print("TEXTURA LROC CREADA CORRECTAMENTE")
print("Archivo:", output)
print("Dimensiones:", N, "x", N)
print("Cobertura válida:", round(valid.mean()*100, 2), "%")
