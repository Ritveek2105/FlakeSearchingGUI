# Stitched UI

Next.js viewer for published graphene sample Deep Zoom images, flake JSON, and manual annotation files produced by `graphene_pipeline`.

## Requirements

- Node.js 20 or newer
- npm
- Optional: `graphene_pipeline` if you want to publish new samples into `public/samples`

## Install From A Download

For a simple local launch on Windows, double-click:

```text
start-viewer.bat
```

The launcher installs dependencies if `node_modules/` is missing, opens the browser, and starts the development server.

Manual install:

```powershell
npm install
```

## Run Locally

```powershell
npm run dev
```

Open http://localhost:3000.

## Production Build

```powershell
npm run lint
npm run build
npm run start
```

## Data Layout

Published samples are expected under:

```text
public/
  samples.json
  samples/
    graphene_000001/
      image.dzi
      image_files/
      flakes.json
      annotations.json
      metadata.json
      preview.png
      source.tif
```

The pipeline can publish into this folder when `GRAPHENE_WEBSITE_DIR` points to the `stitched-ui` project root.

## Roboflow Export

The sample viewer Export tab can:

- download a YOLO/Roboflow dataset zip from saved manual annotation boxes
- upload generated training tiles and YOLO annotations directly to an existing Roboflow object-detection project

Direct upload requires:

- a Roboflow private API key
- the Roboflow project ID, for example `grapheneflakes-72y6l-szuyj`
- saved manual annotation boxes for the current sample
- `source.tif` in the sample folder

The uploaded training images remain clean; bounding boxes are sent as separate YOLO annotation files.

## Release Notes

Do not ship local dependency/build folders in source downloads:

- `node_modules/`
- `.next/`
- `out/`
- `build/`
- `rf-env/`

Generated microscope/sample data can be large. Include `public/samples/` only when you intentionally want to ship demo data.
