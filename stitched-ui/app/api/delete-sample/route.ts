import { NextRequest, NextResponse } from "next/server";
import { rm, readFile, writeFile } from "fs/promises";
import path from "path";

type SamplesCatalog = {
  version?: number;
  samples?: Array<{
    id: string;
    path: string;
  }>;
};

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const sampleId = body.sampleId;

    if (!sampleId || typeof sampleId !== "string") {
      return NextResponse.json(
        { error: "Missing sampleId." },
        { status: 400 }
      );
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(sampleId)) {
      return NextResponse.json(
        { error: "Invalid sampleId." },
        { status: 400 }
      );
    }

    const publicDir = path.join(process.cwd(), "public");
    const samplesDir = path.join(publicDir, "samples");
    const sampleDir = path.join(samplesDir, sampleId);
    const catalogPath = path.join(publicDir, "samples.json");

    await rm(sampleDir, {
      recursive: true,
      force: true,
    });

    let catalog: SamplesCatalog = {
      version: 1,
      samples: [],
    };

    try {
      const raw = await readFile(catalogPath, "utf-8");
      const parsed = JSON.parse(raw);

      if (Array.isArray(parsed)) {
        catalog = {
          version: 1,
          samples: parsed,
        };
      } else {
        catalog = parsed;
      }
    } catch {
      catalog = {
        version: 1,
        samples: [],
      };
    }

    catalog.samples = (catalog.samples ?? []).filter(
      (sample) => sample.id !== sampleId
    );

    await writeFile(catalogPath, JSON.stringify(catalog, null, 2), "utf-8");

    return NextResponse.json({
      ok: true,
      deleted: sampleId,
    });
  } catch (error) {
    return NextResponse.json(
      { error: String(error) },
      { status: 500 }
    );
  }
}