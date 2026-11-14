from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.enums import Resampling

root = Path(".")
static = root / "static"
data = static / "data"
data.mkdir(parents=True, exist_ok=True)

dem_path = root / "data/lola_dem.tif"
texture_path = data / "lroc_texture.png"

if not dem_path.exists():
    raise SystemExit("ERROR: falta NASA LOLA")

if not texture_path.exists():
    raise SystemExit("ERROR: falta NASA LROC")

N = 257

with rasterio.open(dem_path) as ds:
    arr = ds.read(
        1,
        out_shape=(N, N),
        masked=True,
        resampling=Resampling.bilinear
    )

    values = np.asarray(arr.filled(np.nan), dtype=float)
    valid = np.isfinite(values)

    if not valid.any():
        raise SystemExit("ERROR: LOLA sin elevaciones válidas")

    reference = float(np.nanmedian(values))
    values = np.where(valid, values-reference, 0)

    width_m = ds.bounds.right-ds.bounds.left
    height_m = ds.bounds.top-ds.bounds.bottom

    terrain = {
        "width": N,
        "height": N,
        "extent_x_m": width_m,
        "extent_y_m": height_m,
        "reference_elevation_m": reference,
        "crs": str(ds.crs),
        "elevations_m": values.ravel().round(3).tolist(),
        "valid_mask": valid.astype(int).ravel().tolist()
    }

(data / "lola_terrain.json").write_text(
    json.dumps(terrain),
    encoding="utf-8"
)

html = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LUNAR WINDOW 3D</title>
<style>
body{margin:0;background:#05070b;color:white;font-family:Arial}
#view{position:fixed;inset:0}
#panel{position:fixed;top:18px;left:18px;background:#101723e8;
padding:18px;border:1px solid #344256;border-radius:12px;
width:290px;max-width:calc(100vw - 72px)}
h2{margin:0 0 8px;font-size:19px}
small{color:#aebdd0}
button{background:#25344b;color:white;border:1px solid #526580;
border-radius:7px;padding:9px;margin:8px 4px 8px 0;cursor:pointer}
button:hover{background:#365376}
input{width:100%}
#status{font-size:12px;color:#a8c8e9;line-height:1.5}
#coords{position:fixed;bottom:16px;left:18px;background:#101723df;
padding:10px;border-radius:8px;font-size:12px}
</style>
</head>
<body>
<div id="view"></div>
<div id="panel">
<h2>🌕 LUNAR WINDOW 3D</h2>
<small>NASA LOLA + NASA LROC</small>
<div>
<button id="orbit">Vista orbital</button>
<button id="surface">Superficie</button>
</div>
<label>Exageración vertical: <span id="scaleLabel">3×</span></label>
<input id="scale" type="range" min="1" max="15" step="0.5" value="3">
<p id="status">Cargando datos científicos...</p>
<small>Arrastrar: rotar · Rueda: acercar · Clic derecho: desplazar</small>
</div>
<div id="coords">Esperando terreno...</div>

<script type="module">
import * as THREE from
'https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.module.js';
import {OrbitControls} from
'https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/controls/OrbitControls.js';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x05070b);

const camera = new THREE.PerspectiveCamera(
  60, innerWidth/innerHeight, 0.01, 5000
);

const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth,innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
document.getElementById('view').appendChild(renderer.domElement);

const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.maxDistance = 1500;

scene.add(new THREE.AmbientLight(0xffffff,1.25));

const sun = new THREE.DirectionalLight(0xffffff,1.6);
sun.position.set(-100,200,80);
scene.add(sun);

const status = document.getElementById('status');
const coords = document.getElementById('coords');

let terrainMesh;
let geometry;
let heights;
let terrainData;
let extentX;
let extentY;
let verticalScale = 3;

function elevationAt(x,z){
  if(!terrainData)return 0;
  const n=terrainData.width;
  const col=Math.max(0,Math.min(n-1,
    Math.round((x/extentX+0.5)*(n-1))));
  const row=Math.max(0,Math.min(n-1,
    Math.round((0.5-z/extentY)*(n-1))));
  return heights[row*n+col]/1000*verticalScale;
}

async function loadTerrain(){
  const response=await fetch('/static/data/lola_terrain.json');
  if(!response.ok)throw Error('No se pudo cargar LOLA');
  terrainData=await response.json();

  const n=terrainData.width;
  extentX=terrainData.extent_x_m/1000;
  extentY=terrainData.extent_y_m/1000;
  heights=terrainData.elevations_m;

  geometry=new THREE.PlaneGeometry(
    extentX,extentY,n-1,n-1
  );
  geometry.rotateX(-Math.PI/2);

  const positions=geometry.attributes.position;

  for(let row=0;row<n;row++){
    for(let col=0;col<n;col++){
      const vertex=row*n+col;
      const demRow=n-1-row;
      const height=heights[demRow*n+col];
      positions.setY(vertex,height/1000*verticalScale);
    }
  }

  positions.needsUpdate=true;
  geometry.computeVertexNormals();

  const texture=new THREE.TextureLoader().load(
    '/static/data/lroc_texture.png',
    ()=>status.textContent=
      'NASA LOLA + LROC cargados correctamente',
    undefined,
    ()=>status.textContent=
      'LOLA cargado; error en fotografía LROC'
  );

  texture.colorSpace=THREE.SRGBColorSpace;

  // El DEM se invierte verticalmente al construir
  // la geometría, por eso se ajusta también la textura.
  texture.flipY=false;

  terrainMesh=new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      map:texture,
      side:THREE.DoubleSide,
      roughness:1
    })
  );

  scene.add(terrainMesh);

  camera.position.set(110,130,150);
  controls.target.set(0,0,0);
  controls.update();

  status.textContent='Relieve LOLA cargado. Cargando LROC...';
}

document.getElementById('orbit').onclick=()=>{
  camera.position.set(110,130,150);
  controls.target.set(0,0,0);
  controls.update();
};

document.getElementById('surface').onclick=()=>{
  const x=0,z=0;
  const y=elevationAt(x,z);
  camera.position.set(x,y+0.002,z);
  controls.target.set(x+0.1,y+0.002,z-0.5);
  controls.update();
};

document.getElementById('scale').oninput=e=>{
  verticalScale=Number(e.target.value);
  document.getElementById('scaleLabel').textContent=
    verticalScale+'×';

  if(!geometry||!terrainData)return;

  const n=terrainData.width;
  const positions=geometry.attributes.position;

  for(let row=0;row<n;row++){
    for(let col=0;col<n;col++){
      const vertex=row*n+col;
      const demRow=n-1-row;
      positions.setY(
        vertex,
        heights[demRow*n+col]/1000*verticalScale
      );
    }
  }

  positions.needsUpdate=true;
  geometry.computeVertexNormals();
};

function animate(){
  requestAnimationFrame(animate);
  controls.update();

  if(terrainData){
    const x=controls.target.x;
    const z=controls.target.z;
    coords.textContent=
      'X: '+x.toFixed(2)+' km | Y: '+
      (-z).toFixed(2)+' km | Elevación relativa: '+
      (elevationAt(x,z)/verticalScale*1000).toFixed(1)+' m';
  }

  renderer.render(scene,camera);
}

addEventListener('resize',()=>{
  camera.aspect=innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight);
});

loadTerrain().catch(error=>{
  console.error(error);
  status.textContent='ERROR: '+error.message;
});

animate();
</script>
</body>
</html>'''

(static / "index.html").write_text(html, encoding="utf-8")

server = '''from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LUNAR WINDOW 3D")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")
'''

Path("main.py").write_text(server, encoding="utf-8")

print("===================================")
print("LUNAR WINDOW 3D RECONSTRUIDO")
print("===================================")
print("NASA LOLA: OK")
print("NASA LROC: OK")
print("Terreno:", N, "x", N)
print("Extensión:", round(extentX if False else width_m/1000), "km")
print("Visor: static/index.html")
print("Servidor: main.py")
