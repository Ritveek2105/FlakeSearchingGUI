import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import path from "path";

function resolvePublicPath(publicDir: string, requestPath: string) {
  const targetPath = path.resolve(publicDir, `.${requestPath}`);
  const relativePath = path.relative(publicDir, targetPath);

  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    return null;
  }

  return targetPath;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const annotationsPath = body.annotationsPath;
    const data = body.data;

    if (!annotationsPath || !data) {
      return NextResponse.json(
        { error: "Missing annotationsPath or data." },
        { status: 400 }
      );
    }

    if (
      !annotationsPath.startsWith("/samples/") ||
      !annotationsPath.endsWith("annotations.json")
    ) {
      return NextResponse.json(
        { error: "Invalid annotationsPath." },
        { status: 400 }
      );
    }

    const publicDir = path.resolve(process.cwd(), "public");
    const targetPath = resolvePublicPath(publicDir, annotationsPath);

    if (!targetPath) {
      return NextResponse.json(
        { error: "Invalid annotationsPath." },
        { status: 400 }
      );
    }

    await mkdir(path.dirname(targetPath), { recursive: true });
    await writeFile(targetPath, JSON.stringify(data, null, 2), "utf-8");

    return NextResponse.json({ ok: true });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
