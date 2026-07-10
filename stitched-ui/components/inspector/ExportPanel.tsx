"use client";

import { useState } from "react";

type ExportPreview = {
  sampleId: string;
  imageWidth: number;
  imageHeight: number;
  sourceImage: string;
  tileSize: number;
  overlap: number;
  stride: number;
  totalTiles: number;
  exportedTiles: number;
  emptyTiles: number;
  annotatedTiles: number;
  totalBoxes: number;
  exportedBoxInstances: number;
  classCounts: Record<string, number>;
  estimatedImageMegabytes: number;
};

type ExportPanelProps = {
  boxCount: number;
  annotationsPath: string;
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: 8,
  border: "1px solid #cfd6df",
  borderRadius: 6,
  marginTop: 4,
  boxSizing: "border-box",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontWeight: 700,
  fontSize: 12,
  marginTop: 12,
};

export default function ExportPanel({ boxCount, annotationsPath }: ExportPanelProps) {
  const [tileSize, setTileSize] = useState(640);
  const [overlap, setOverlap] = useState(64);
  const [skipEmptyTiles, setSkipEmptyTiles] = useState(true);
  const [minBoxSize, setMinBoxSize] = useState(5);
  const [validPercent, setValidPercent] = useState(20);
  const [roboflowApiKey, setRoboflowApiKey] = useState("");
  const [roboflowProjectId, setRoboflowProjectId] = useState("");
  const [roboflowBatchName, setRoboflowBatchName] = useState("");
  const [maxTiles, setMaxTiles] = useState(500);
  const [preview, setPreview] = useState<ExportPreview | null>(null);
  const [status, setStatus] = useState("No preview generated yet.");
  const [exporting, setExporting] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function generatePreview() {
    setStatus("Generating preview...");
    setPreview(null);

    const response = await fetch("/api/export-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        annotationsPath,
        tileSize,
        overlap,
        skipEmptyTiles,
        minBoxSize,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      setStatus(data.error || "Preview failed.");
      return;
    }

    setPreview(data.preview);
    setStatus("Preview ready.");
  }

  async function exportZip() {
    setExporting(true);
    setStatus("Building dataset zip...");

    try {
      const response = await fetch("/api/export-yolo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          annotationsPath,
          tileSize,
          overlap,
          skipEmptyTiles,
          minBoxSize,
          validPercent,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        setStatus(data.error || "Export failed.");
        return;
      }

      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match?.[1] || "roboflow-yolo-export.zip";
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      setStatus("Dataset zip downloaded.");
    } finally {
      setExporting(false);
    }
  }

  async function uploadToRoboflow() {
    setUploading(true);
    setStatus("Uploading to Roboflow...");

    try {
      const response = await fetch("/api/upload-roboflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          annotationsPath,
          tileSize,
          overlap,
          skipEmptyTiles,
          minBoxSize,
          validPercent,
          maxTiles,
          apiKey: roboflowApiKey,
          projectId: roboflowProjectId,
          batchName: roboflowBatchName,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setStatus(data.error || "Roboflow upload failed.");
        return;
      }

      setStatus(
        `Uploaded ${data.uploadedImages} images and ${data.uploadedAnnotations} annotations to Roboflow.`
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>YOLO/Roboflow Export</h3>

        <label style={labelStyle}>Tile size</label>
        <input
          type="number"
          min={64}
          step={32}
          value={tileSize}
          onChange={(event) => setTileSize(Number(event.target.value))}
          style={inputStyle}
        />

        <label style={labelStyle}>Overlap</label>
        <input
          type="number"
          min={0}
          step={16}
          value={overlap}
          onChange={(event) => setOverlap(Number(event.target.value))}
          style={inputStyle}
        />

        <label style={labelStyle}>Minimum clipped box size, pixels</label>
        <input
          type="number"
          min={1}
          value={minBoxSize}
          onChange={(event) => setMinBoxSize(Number(event.target.value))}
          style={inputStyle}
        />

        <label style={labelStyle}>Validation split, percent</label>
        <input
          type="number"
          min={0}
          max={80}
          step={5}
          value={validPercent}
          onChange={(event) => setValidPercent(Number(event.target.value))}
          style={inputStyle}
        />

        <label style={labelStyle}>Max tiles to upload</label>
        <input
          type="number"
          min={1}
          max={5000}
          step={25}
          value={maxTiles}
          onChange={(event) => setMaxTiles(Number(event.target.value))}
          style={inputStyle}
        />

        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
          <input
            type="checkbox"
            checked={skipEmptyTiles}
            onChange={(event) => setSkipEmptyTiles(event.target.checked)}
          />
          Skip empty tiles
        </label>

        <div style={{ marginTop: 14, padding: 10, background: "#f8fafc", borderRadius: 8 }}>
          Boxes currently loaded in viewer: <b>{boxCount}</b>
        </div>

        <button
          onClick={generatePreview}
          style={{
            width: "100%",
            marginTop: 14,
            padding: "9px 10px",
            borderRadius: 6,
            border: "1px solid #2563eb",
            background: "#2563eb",
            color: "white",
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          Generate Preview
        </button>

        <button
          onClick={exportZip}
          disabled={exporting || boxCount === 0}
          style={{
            width: "100%",
            marginTop: 10,
            padding: "9px 10px",
            borderRadius: 6,
            border: "1px solid #0f766e",
            background: exporting || boxCount === 0 ? "#94a3b8" : "#0f766e",
            color: "white",
            fontWeight: 700,
            cursor: exporting || boxCount === 0 ? "not-allowed" : "pointer",
          }}
        >
          {exporting ? "Building ZIP..." : "Export YOLO/Roboflow ZIP"}
        </button>

        <div style={{ height: 1, background: "#e5e7eb", margin: "16px 0" }} />

        <label style={labelStyle}>Roboflow project ID</label>
        <input
          type="text"
          value={roboflowProjectId}
          onChange={(event) => setRoboflowProjectId(event.target.value)}
          placeholder="example: grapheneflakes-72y6l-szuyj"
          style={inputStyle}
        />

        <label style={labelStyle}>Roboflow API key</label>
        <input
          type="password"
          value={roboflowApiKey}
          onChange={(event) => setRoboflowApiKey(event.target.value)}
          placeholder="Private API key"
          style={inputStyle}
        />

        <label style={labelStyle}>Batch name</label>
        <input
          type="text"
          value={roboflowBatchName}
          onChange={(event) => setRoboflowBatchName(event.target.value)}
          placeholder="Optional"
          style={inputStyle}
        />

        <button
          onClick={uploadToRoboflow}
          disabled={uploading || boxCount === 0 || !roboflowProjectId}
          style={{
            width: "100%",
            marginTop: 10,
            padding: "9px 10px",
            borderRadius: 6,
            border: "1px solid #7c3aed",
            background: uploading || boxCount === 0 || !roboflowProjectId ? "#94a3b8" : "#7c3aed",
            color: "white",
            fontWeight: 700,
            cursor: uploading || boxCount === 0 || !roboflowProjectId ? "not-allowed" : "pointer",
          }}
        >
          {uploading ? "Uploading..." : "Upload Directly to Roboflow"}
        </button>

        <div style={{ color: "#64748b", fontSize: 12, marginTop: 8 }}>{status}</div>
      </div>

      {preview && (
        <div style={{ marginTop: 16, background: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
          <h3 style={{ marginTop: 0 }}>Preview Results</h3>

          <div style={{ lineHeight: 1.8 }}>
            <b>Sample:</b> {preview.sampleId}<br />
            <b>Source image:</b> {preview.sourceImage}<br />
            <b>Image size:</b> {preview.imageWidth} x {preview.imageHeight}<br />
            <b>Tile size:</b> {preview.tileSize}<br />
            <b>Overlap:</b> {preview.overlap}<br />
            <b>Stride:</b> {preview.stride}<br />
            <b>Total possible tiles:</b> {preview.totalTiles}<br />
            <b>Tiles to export:</b> {preview.exportedTiles}<br />
            <b>Annotated tiles:</b> {preview.annotatedTiles}<br />
            <b>Skipped empty tiles:</b> {preview.emptyTiles}<br />
            <b>Original boxes:</b> {preview.totalBoxes}<br />
            <b>Tile-local box instances:</b> {preview.exportedBoxInstances}<br />
            <b>Estimated image data:</b> {preview.estimatedImageMegabytes} MB
          </div>

          <h4>Class counts</h4>
          {Object.keys(preview.classCounts).length === 0 ? (
            <p style={{ color: "#64748b" }}>No boxes passed the export filters.</p>
          ) : (
            <ul style={{ paddingLeft: 18 }}>
              {Object.entries(preview.classCounts).map(([label, count]) => (
                <li key={label}>{label}: {count}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
