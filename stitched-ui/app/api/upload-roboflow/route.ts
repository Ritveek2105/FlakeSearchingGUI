import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";
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

type RoboflowUploadResponse = {
  id?: string;
  image?: string | { id?: string };
  success?: boolean;
  [key: string]: unknown;
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

async function readJsonFile<T>(filePath: string): Promise<T> {
  const text = await readFile(filePath, "utf-8");
  return JSON.parse(text.replace(/^\uFEFF/, "")) as T;
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

function extractImageId(response: RoboflowUploadResponse) {
  if (typeof response.id === "string") return response.id;
  if (typeof response.image === "string") return response.image;
  if (response.image && typeof response.image === "object" && typeof response.image.id === "string") {
    return response.image.id;
  }

  return null;
}

async function uploadImageToRoboflow({
  apiKey,
  projectId,
  name,
  split,
  batch,
  imageBuffer,
}: {
  apiKey: string;
  projectId: string;
  name: string;
  split: string;
  batch: string;
  imageBuffer: Buffer;
}) {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("split", split);
  if (batch) formData.append("batch", batch);
  formData.append("file", new Blob([new Uint8Array(imageBuffer)], { type: "image/png" }), name);

  const url = new URL(`https://api.roboflow.com/dataset/${encodeURIComponent(projectId)}/upload`);
  url.searchParams.set("api_key", apiKey);

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  const text = await response.text();
  let data: RoboflowUploadResponse;

  try {
    data = JSON.parse(text) as RoboflowUploadResponse;
  } catch {
    data = { raw: text };
  }

  if (!response.ok) {
    throw new Error(`Image upload failed for ${name}: ${text}`);
  }

  const imageId = extractImageId(data);
  if (!imageId) {
    throw new Error(`Roboflow did not return an image id for ${name}: ${text}`);
  }

  return imageId;
}

async function uploadAnnotationToRoboflow({
  apiKey,
  projectId,
  imageId,
  name,
  annotation,
  labelmap,
}: {
  apiKey: string;
  projectId: string;
  imageId: string;
  name: string;
  annotation: string;
  labelmap: Record<string, string>;
}) {
  const url = new URL(`https://api.roboflow.com/dataset/${encodeURIComponent(projectId)}/annotate/${encodeURIComponent(imageId)}`);
  url.searchParams.set("api_key", apiKey);
  url.searchParams.set("name", name);

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      annotationFile: annotation,
      labelmap,
    }),
  });

  const text = await response.text();

  if (!response.ok) {
    throw new Error(`Annotation upload failed for ${name}: ${text}`);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const apiKey = String(body.apiKey || process.env.ROBOFLOW_API_KEY || "").trim();
    const projectId = String(body.projectId || "").trim();
    const batchName = String(body.batchName || "").trim();
    const annotationsPath = String(body.annotationsPath || "");
    const tileSize = Number(body.tileSize || 640);
    const overlap = Number(body.overlap || 64);
    const minBoxSize = Number(body.minBoxSize || 5);
    const skipEmptyTiles = Boolean(body.skipEmptyTiles ?? true);
    const validPercent = Number(body.validPercent ?? 20);
    const maxTiles = Number(body.maxTiles ?? 500);

    if (!apiKey) {
      return NextResponse.json({ error: "Roboflow API key is required." }, { status: 400 });
    }

    if (!projectId) {
      return NextResponse.json({ error: "Roboflow project ID is required." }, { status: 400 });
    }

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

    if (!Number.isFinite(maxTiles) || maxTiles <= 0 || maxTiles > 5000) {
      return NextResponse.json({ error: "Max tiles must be between 1 and 5000." }, { status: 400 });
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

    const labelmap = Object.fromEntries(classNames.map((name, index) => [String(index), name]));
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
      return NextResponse.json({ error: "No tiles passed the upload filters." }, { status: 400 });
    }

    if (exportItems.length > maxTiles) {
      return NextResponse.json(
        { error: `Upload would include ${exportItems.length} tiles. Increase max tiles or enable Skip empty tiles.` },
        { status: 400 }
      );
    }

    const validEvery = validPercent > 0 ? Math.max(1, Math.round(100 / validPercent)) : 0;
    let uploadedImages = 0;
    let uploadedAnnotations = 0;
    let trainCount = 0;
    let validCount = 0;

    for (let index = 0; index < exportItems.length; index += 1) {
      const item = exportItems[index];
      const split = validEvery > 0 && index % validEvery === 0 ? "valid" : "train";
      const baseName = `${cleanName(sampleId)}_${String(index + 1).padStart(5, "0")}_x${item.tile.x}_y${item.tile.y}`;
      const imageName = `${baseName}.png`;
      const labelName = `${baseName}.txt`;

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

      const annotation = `${item.boxes.map((box) => {
        const classIndex = classIndexByName.get(box.label || "graphene") ?? 0;
        return yoloLine(box, classIndex, item.tile);
      }).join("\n")}\n`;

      const imageId = await uploadImageToRoboflow({
        apiKey,
        projectId,
        name: imageName,
        split,
        batch: batchName || `${sampleId}-manual-export`,
        imageBuffer,
      });
      uploadedImages += 1;

      if (item.boxes.length > 0) {
        await uploadAnnotationToRoboflow({
          apiKey,
          projectId,
          imageId,
          name: labelName,
          annotation,
          labelmap,
        });
        uploadedAnnotations += 1;
      }
    }

    return NextResponse.json({
      ok: true,
      sampleId,
      projectId,
      batchName: batchName || `${sampleId}-manual-export`,
      uploadedImages,
      uploadedAnnotations,
      trainCount,
      validCount,
      classes: classNames,
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
