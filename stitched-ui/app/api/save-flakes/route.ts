import { NextRequest, NextResponse } from "next/server";
import { writeFile } from "fs/promises";
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

    const flakesPath = body.flakesPath;
    const data = body.data;

    if (!flakesPath || !data) {
      return NextResponse.json(
        { error: "Missing flakesPath or data." },
        { status: 400 }
      );
    }

    if (!flakesPath.startsWith("/samples/") || !flakesPath.endsWith("flakes.json")) {
      return NextResponse.json(
        { error: "Invalid flakesPath." },
        { status: 400 }
      );
    }

    const publicDir = path.resolve(process.cwd(), "public");
    const targetPath = resolvePublicPath(publicDir, flakesPath);

    if (!targetPath) {
      return NextResponse.json(
        { error: "Invalid flakesPath." },
        { status: 400 }
      );
    }

    await writeFile(targetPath, JSON.stringify(data, null, 2), "utf-8");

    return NextResponse.json({ ok: true });
  } catch (error) {
    return NextResponse.json(
      { error: String(error) },
      { status: 500 }
    );
  }
}
