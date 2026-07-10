import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";
import JSZip from "jszip";
import sharp from "sharp";

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

type SampleMetadata = {
  image?: {
    width?: number;
    height?: number;
    source_image?: string;
  };
};

type Tile = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type ClippedBox = {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
};

function resolvePublicPath(publicDir: string, requestPath: string) {
  const targetPath = path.resolve(publicDir, `.${requestPath}`);
  const relativePath = path.relative(publicDir, targetPath);

  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    return null;
  }

  return targetPath;
}

function resolveSamplePath(sampleDir: string, fileName: string) {
  const targetPath = path.resolve(sampleDir, fileName);
  const relativePath = path.relative(sampleDir, targetPath);

  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    return null;
  }

  return targetPath;
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

function intersectBoxWithTile(box: AnnotationBox, tile: Tile): ClippedBox | null {
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

function yoloLine(box: ClippedBox, classIndex: number, tile: Tile) {
  const xCenter = (box.x + box.width / 2) / tile.width;
  const yCenter = (box.y + box.height / 2) / tile.height;
  const width = box.width / tile.width;
  const height = box.height / tile.height;

  return [
    String(classIndex),
    xCenter.toFixed(6),
    yCenter.toFixed(6),
    width.toFixed(6),
    height.toFixed(6),
  ].join(" ");
}

function cleanName(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "") || "dataset";
}

async function readJsonFile<T>(filePath: string): Promise<T> {
  const text = await readFile(filePath, "utf-8");
  return JSON.parse(text.replace(/^\uFEFF/, "")) as T;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const annotationsPath = String(body.annotationsPath || "");
    const tileSize = Number(body.tileSize || 640);
    const overlap = Number(body.overlap || 64);
    const minBoxSize = Number(body.minBoxSize || 5);
    const skipEmptyTiles = Boolean(body.skipEmptyTiles ?? true);
    const validPercent = Number(body.validPercent ?? 20);

    if (!annotationsPath.startsWith("/samples/") || !annotationsPath.endsWith("annotations.json")) {
      return NextResponse.json({ error: "Invalid annotationsPath." }, { status: 400 });
    }

    if (!Number.isFinite(tileSize) || tileSize <= 0) {
      return NextResponse.json({ error: "Tile size must be positive." }, { status: 400 });
    }

    if (!Number.isFinite(overlap) || overlap < 0 || overlap >= tileSize) {
      return NextResponse.json({ error: "Overlap must be non-negative and smaller than tile size." }, { status: 400 });
    }

    if (!Number.isFinite(validPercent) || validPercent < 0 || validPercent > 80) {
      return NextResponse.json({ error: "Validation percent must be between 0 and 80." }, { status: 400 });
    }

    const publicDir = path.resolve(process.cwd(), "public");
    const annotationFilePath = resolvePublicPath(publicDir, annotationsPath);

    if (!annotationFilePath) {
      return NextResponse.json({ error: "Invalid annotationsPath." }, { status: 400 });
    }

    const sampleDir = path.dirname(annotationFilePath);
    const sampleId = path.basename(sampleDir);
    const metadataPath = path.join(sampleDir, "metadata.json");

    const annotations = await readJsonFile<AnnotationFile>(annotationFilePath);
    const metadata = await readJsonFile<SampleMetadata>(metadataPath);

    const imageWidth = Number(metadata?.image?.width);
    const imageHeight = Number(metadata?.image?.height);
    const sourceImage = String(metadata?.image?.source_image || "source.tif");
    const sourceImagePath = resolveSamplePath(sampleDir, sourceImage);

    if (!sourceImagePath) {
      return NextResponse.json({ error: "Invalid source image path." }, { status: 400 });
    }

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

    if (boxes.length === 0) {
      return NextResponse.json({ error: "No annotation boxes found for this sample." }, { status: 400 });
    }

    const classNames: string[] = [];
    const classIndexByName = new Map<string, number>();

    for (const box of boxes) {
      const label = box.label || "graphene";
      if (!classIndexByName.has(label)) {
        classIndexByName.set(label, classNames.length);
        classNames.push(label);
      }
    }

    const stride = tileSize - overlap;
    const tiles = buildTiles(imageWidth, imageHeight, tileSize, stride);
    const exportItems: Array<{ tile: Tile; boxes: ClippedBox[] }> = [];

    for (const tile of tiles) {
      const clippedBoxes = boxes
        .map((box) => intersectBoxWithTile(box, tile))
        .filter((box) => box && box.width >= minBoxSize && box.height >= minBoxSize) as ClippedBox[];

      if (clippedBoxes.length === 0 && skipEmptyTiles) {
        continue;
      }

      exportItems.push({ tile, boxes: clippedBoxes });
    }

    if (exportItems.length === 0) {
      return NextResponse.json({ error: "No tiles passed the export filters." }, { status: 400 });
    }

    const zip = new JSZip();
    const validEvery = validPercent > 0 ? Math.max(1, Math.round(100 / validPercent)) : 0;
    let trainCount = 0;
    let validCount = 0;

    for (let index = 0; index < exportItems.length; index += 1) {
      const item = exportItems[index];
      const split = validEvery > 0 && index % validEvery === 0 ? "valid" : "train";
      const baseName = `${cleanName(sampleId)}_${String(index + 1).padStart(5, "0")}_x${item.tile.x}_y${item.tile.y}`;

      if (split === "valid") {
        validCount += 1;
      } else {
        trainCount += 1;
      }

      const imageBuffer = await sharp(sourceImagePath, { limitInputPixels: false })
        .extract({
          left: item.tile.x,
          top: item.tile.y,
          width: item.tile.width,
          height: item.tile.height,
        })
        .png()
        .toBuffer();

      const labelLines = item.boxes.map((box) => {
        const classIndex = classIndexByName.get(box.label || "graphene") ?? 0;
        return yoloLine(box, classIndex, item.tile);
      });

      zip.file(`images/${split}/${baseName}.png`, imageBuffer);
      zip.file(`labels/${split}/${baseName}.txt`, `${labelLines.join("\n")}\n`);
    }

    zip.file(
      "data.yaml",
      [
        "path: .",
        "train: images/train",
        "val: images/valid",
        `nc: ${classNames.length}`,
        `names: [${classNames.map((name) => JSON.stringify(name)).join(", ")}]`,
        "",
      ].join("\n")
    );

    zip.file(
      "README.txt",
      [
        `Sample: ${sampleId}`,
        `Source image: ${sourceImage}`,
        `Tile size: ${tileSize}`,
        `Overlap: ${overlap}`,
        `Manual boxes: ${boxes.length}`,
        `Exported tiles: ${exportItems.length}`,
        `Train tiles: ${trainCount}`,
        `Validation tiles: ${validCount}`,
        "",
        "Import this zip into Roboflow as a YOLO dataset.",
        "",
      ].join("\n")
    );

    const zipBuffer = await zip.generateAsync({
      type: "nodebuffer",
      compression: "DEFLATE",
      compressionOptions: { level: 6 },
    });

    return new NextResponse(new Uint8Array(zipBuffer), {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${cleanName(sampleId)}-yolo-export.zip"`,
      },
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
