import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

type AnnotationBox = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
};

type AnnotationFile = {
  version?: number;
  boxes?: AnnotationBox[];
};

type Tile = {
  x: number;
  y: number;
  width: number;
  height: number;
};

function resolvePublicPath(publicDir: string, requestPath: string) {
  const targetPath = path.resolve(publicDir, `.${requestPath}`);
  const relativePath = path.relative(publicDir, targetPath);

  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    return null;
  }

  return targetPath;
}

function intersectBoxWithTile(box: AnnotationBox, tile: Tile) {
  const x1 = Math.max(box.x, tile.x);
  const y1 = Math.max(box.y, tile.y);
  const x2 = Math.min(box.x + box.width, tile.x + tile.width);
  const y2 = Math.min(box.y + box.height, tile.y + tile.height);

  const width = x2 - x1;
  const height = y2 - y1;

  if (width <= 0 || height <= 0) return null;

  return {
    x: x1 - tile.x,
    y: y1 - tile.y,
    width,
    height,
    label: box.label || "graphene",
  };
}

function buildTiles(imageWidth: number, imageHeight: number, tileSize: number, stride: number): Tile[] {
  const tiles: Tile[] = [];

  for (let y = 0; y < imageHeight; y += stride) {
    for (let x = 0; x < imageWidth; x += stride) {
      tiles.push({
        x,
        y,
        width: Math.min(tileSize, imageWidth - x),
        height: Math.min(tileSize, imageHeight - y),
      });

      if (x + tileSize >= imageWidth) break;
    }

    if (y + tileSize >= imageHeight) break;
  }

  return tiles;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const annotationsPath = String(body.annotationsPath || "");
    const tileSize = Number(body.tileSize || 640);
    const overlap = Number(body.overlap || 64);
    const minBoxSize = Number(body.minBoxSize || 5);
    const skipEmptyTiles = Boolean(body.skipEmptyTiles);

    if (!annotationsPath.startsWith("/samples/") || !annotationsPath.endsWith("annotations.json")) {
      return NextResponse.json({ error: "Invalid annotationsPath." }, { status: 400 });
    }

    if (!Number.isFinite(tileSize) || tileSize <= 0) {
      return NextResponse.json({ error: "Tile size must be positive." }, { status: 400 });
    }

    if (!Number.isFinite(overlap) || overlap < 0 || overlap >= tileSize) {
      return NextResponse.json({ error: "Overlap must be non-negative and smaller than tile size." }, { status: 400 });
    }

    const publicDir = path.resolve(process.cwd(), "public");
    const annotationFilePath = resolvePublicPath(publicDir, annotationsPath);

    if (!annotationFilePath) {
      return NextResponse.json({ error: "Invalid annotationsPath." }, { status: 400 });
    }
    const sampleDir = path.dirname(annotationFilePath);
    const sampleId = path.basename(sampleDir);
    const metadataPath = path.join(sampleDir, "metadata.json");

    const annotations = JSON.parse(await readFile(annotationFilePath, "utf-8")) as AnnotationFile;
    const metadata = JSON.parse(await readFile(metadataPath, "utf-8"));

    const imageWidth = Number(metadata?.image?.width);
    const imageHeight = Number(metadata?.image?.height);
    const sourceImage = String(metadata?.image?.source_image || "source.tif");

    if (!Number.isFinite(imageWidth) || !Number.isFinite(imageHeight) || imageWidth <= 0 || imageHeight <= 0) {
      return NextResponse.json(
        { error: "metadata.json must contain image.width and image.height." },
        { status: 400 }
      );
    }

    const boxes = (annotations.boxes || []).filter((box) => {
      return (
        Number.isFinite(box.x) &&
        Number.isFinite(box.y) &&
        Number.isFinite(box.width) &&
        Number.isFinite(box.height) &&
        box.width > 0 &&
        box.height > 0
      );
    });

    const stride = tileSize - overlap;
    const tiles = buildTiles(imageWidth, imageHeight, tileSize, stride);

    let exportedTiles = 0;
    let annotatedTiles = 0;
    let emptyTiles = 0;
    let exportedBoxInstances = 0;
    const classCounts: Record<string, number> = {};

    for (const tile of tiles) {
      const clippedBoxes = boxes
        .map((box) => intersectBoxWithTile(box, tile))
        .filter((box) => box && box.width >= minBoxSize && box.height >= minBoxSize) as Array<{
          x: number;
          y: number;
          width: number;
          height: number;
          label: string;
        }>;

      if (clippedBoxes.length === 0) {
        if (skipEmptyTiles) {
          emptyTiles += 1;
          continue;
        }
      } else {
        annotatedTiles += 1;
      }

      exportedTiles += 1;
      exportedBoxInstances += clippedBoxes.length;

      for (const box of clippedBoxes) {
        const label = box.label || "graphene";
        classCounts[label] = (classCounts[label] || 0) + 1;
      }
    }

    const estimatedImageMegabytes = Math.round((exportedTiles * tileSize * tileSize * 3) / 1_000_000);

    return NextResponse.json({
      preview: {
        sampleId,
        imageWidth,
        imageHeight,
        sourceImage,
        tileSize,
        overlap,
        stride,
        totalTiles: tiles.length,
        exportedTiles,
        emptyTiles,
        annotatedTiles,
        totalBoxes: boxes.length,
        exportedBoxInstances,
        classCounts,
        estimatedImageMegabytes,
      },
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
