from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LUNAR WINDOW 3D")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")


# Servicio de efemérides solares NASA/JPL SPICE.
from datetime import datetime, timezone
from functools import lru_cache
from fastapi import HTTPException
import math
import spiceypy as spice

@lru_cache(maxsize=1)
def cargar_kernels_solares():
    for archivo in [
        "data/kernels/naif0012.tls",
        "data/kernels/de440s.bsp",
        "data/kernels/pck00011.tpc",
    ]:
        spice.furnsh(archivo)
    return True

@app.get("/api/sol")
def posicion_solar(fecha: str = "2026-11-14T22:00:00Z"):
    try:
        dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("La fecha debe incluir zona horaria")
        dt = dt.astimezone(timezone.utc)
        if not (1850 <= dt.year <= 2150):
            raise ValueError("Fecha fuera del rango permitido")

        cargar_kernels_solares()
        et = spice.utc2et(dt.strftime("%Y-%m-%dT%H:%M:%S"))
        vector, _ = spice.spkpos(
            "SUN", et, "IAU_MOON", "LT+S", "MOON"
        )

        distancia = math.sqrt(sum(v*v for v in vector))
        direccion = [float(v/distancia) for v in vector]
        altura_polo_sur = math.degrees(
            math.asin(max(-1.0, min(1.0, -direccion[2])))
        )

        return {
            "fecha_utc": dt.isoformat(),
            "direccion_iau_moon": direccion,
            "distancia_km": distancia,
            "altura_polo_sur_grados": altura_polo_sur,
            "modelo": "NASA/JPL SPICE DE440s + IAU_MOON",
            "horizonte": "Geometrico, sin relieve local"
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# LUNAR_CIELO_SPICE_V1
# Elevación y azimut topocéntricos del Sol y la Tierra.
# Horizonte geométrico: no incluye montañas ni cráteres.
from fastapi import Query

@app.get("/api/cielo")
def cielo_lunar(
    fecha: str = "2026-11-14T22:00:00Z",
    lat: float = Query(-89.0, ge=-90, le=90),
    lon: float = Query(0.0, ge=-180, le=180),
):
    try:
        dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("La fecha debe incluir zona horaria")
        dt = dt.astimezone(timezone.utc)

        cargar_kernels_solares()
        et = spice.utc2et(dt.strftime("%Y-%m-%dT%H:%M:%S"))

        lat_r = math.radians(lat)
        lon_r = math.radians(lon)

        clat, slat = math.cos(lat_r), math.sin(lat_r)
        clon, slon = math.cos(lon_r), math.sin(lon_r)

        up = (clat*clon, clat*slon, slat)
        east = (-slon, clon, 0.0)
        north = (-slat*clon, -slat*slon, clat)

        # Aproximación esférica al radio lunar.
        radio_km = 1737.4
        sitio = [radio_km*v for v in up]

        def dot(a, b):
            return sum(x*y for x, y in zip(a, b))

        resultados = {}

        for nombre in ("SUN", "EARTH"):
            vec, _ = spice.spkpos(
                nombre, et, "IAU_MOON", "LT+S", "MOON"
            )

            local = [vec[i]-sitio[i] for i in range(3)]
            distancia = math.sqrt(dot(local, local))
            direccion = [v/distancia for v in local]

            elevacion = math.degrees(
                math.asin(max(-1, min(1, dot(direccion, up))))
            )

            azimut = math.degrees(
                math.atan2(
                    dot(direccion, east),
                    dot(direccion, north)
                )
            ) % 360

            resultados[nombre.lower()] = {
                "elevacion_grados": round(elevacion, 6),
                "azimut_grados": round(azimut, 6),
                "distancia_km": round(distancia, 3)
            }

        return {
            "fecha_utc": dt.isoformat(),
            "latitud": lat,
            "longitud": lon,
            "sol": resultados["sun"],
            "tierra": resultados["earth"],
            "referencia": "NASA/JPL SPICE DE440s, IAU_MOON",
            "advertencia": (
                "Horizonte geometrico esferico; "
                "no considera relieve ni obstrucciones"
            )
        }

    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
