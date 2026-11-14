from pathlib import Path

path = Path("static/index.html")
texture = Path("static/data/lroc_texture.png")

if not path.exists():
    raise SystemExit("ERROR: No encuentro static/index.html")

if not texture.exists():
    raise SystemExit("ERROR: No encuentro la textura LROC")

html = path.read_text(encoding="utf-8")

if "const terrainMesh" in html:
    print("El visor ya parece tener cambios anteriores.")
    print("Continuando con comprobaciones.")

original = """terrainMesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      vertexColors:true,
      roughness:1,
      side:THREE.DoubleSide
    })
  );"""

replacement = """const photoTexture = new THREE.TextureLoader().load(
    '/static/data/lroc_texture.png',
    () => {
      console.log('Fotografía NASA LROC cargada');
      status.textContent = 'NASA LOLA + LROC cargados correctamente';
    },
    undefined,
    error => {
      console.error('Error cargando LROC:', error);
      status.textContent = 'LOLA cargado; error en textura LROC';
    }
  );

  photoTexture.colorSpace = THREE.SRGBColorSpace;
  photoTexture.wrapS = THREE.ClampToEdgeWrapping;
  photoTexture.wrapT = THREE.ClampToEdgeWrapping;

  terrainMesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      map: photoTexture,
      roughness: 1,
      metalness: 0,
      side: THREE.DoubleSide
    })
  );"""

if original not in html:
    raise SystemExit(
        "ERROR: No encuentro el bloque del terreno esperado. "
        "No modifiqué el visor."
    )

if "lroc_texture.png" in html:
    raise SystemExit(
        "La textura LROC ya está integrada. "
        "No hace falta repetir este paso."
    )

backup = Path("static/index_antes_lroc.html")
backup.write_text(html, encoding="utf-8")

html = html.replace(original, replacement, 1)
path.write_text(html, encoding="utf-8")

print("====================================")
print("LUNAR WINDOW 3D")
print("FOTOGRAFÍA NASA LROC INTEGRADA")
print("====================================")
print("Copia de seguridad:", backup)
print("Visor actualizado:", path)
