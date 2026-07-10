"use client";

import { useEffect, useState } from "react";
import ChipViewer from "./viewer/ChipViewer";
import SampleCard from "./SampleCard";
import {
  buildSampleFromCatalogEntry,
  getSampleDisplayName,
  normalizeSamplesFile,
  type Sample,
} from "@/types/sample";

async function loadSampleMetadata(sample: Sample): Promise<Sample> {
  try {
    const response = await fetch(sample.metadataPath);

    if (!response.ok) {
      console.warn(`Could not load metadata: ${sample.metadataPath}`);
      return sample;
    }

    const metadata = await response.json();

    return {
      ...sample,
      metadata,
    };
  } catch (error) {
    console.warn(`Failed to load metadata for ${sample.id}:`, error);
    return sample;
  }
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  return String(value);
}

export default function SampleBrowser() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [samplePanelOpen, setSamplePanelOpen] = useState(true);
  const [deleteStatus, setDeleteStatus] = useState("");

  const selectedSample =
    samples.find((sample) => sample.id === selectedSampleId) ?? null;

  async function refreshSamples(preferredSampleId?: string | null) {
    setLoading(true);

    try {
      const response = await fetch(`/samples.json?cacheBust=${Date.now()}`);

      if (!response.ok) {
        throw new Error("Could not load samples.json");
      }

      const catalogData = await response.json();
      const catalogEntries = normalizeSamplesFile(catalogData);
      const baseSamples = catalogEntries.map(buildSampleFromCatalogEntry);

      const samplesWithMetadata = await Promise.all(
        baseSamples.map(loadSampleMetadata)
      );

      setSamples(samplesWithMetadata);

      if (samplesWithMetadata.length === 0) {
        setSelectedSampleId(null);
        return;
      }

      const preferredStillExists =
        preferredSampleId &&
        samplesWithMetadata.some((sample) => sample.id === preferredSampleId);

      if (preferredStillExists) {
        setSelectedSampleId(preferredSampleId);
      } else {
        setSelectedSampleId(samplesWithMetadata[0].id);
      }
    } catch (error) {
      console.error("Failed to load samples:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    queueMicrotask(() => {
      void refreshSamples();
    });
  }, []);

  async function deleteSelectedSample() {
    if (!selectedSample) return;

    const confirmed = window.confirm(
      `Delete sample "${selectedSample.id}"?\n\nThis will remove the sample folder and remove it from samples.json.`
    );

    if (!confirmed) return;

    setDeleteStatus("Deleting...");

    try {
      const response = await fetch("/api/delete-sample", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sampleId: selectedSample.id,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.error ?? "Delete failed.");
      }

      setDeleteStatus(`Deleted ${selectedSample.id}.`);

      const remainingSamples = samples.filter(
        (sample) => sample.id !== selectedSample.id
      );

      const nextSampleId = remainingSamples.length > 0 ? remainingSamples[0].id : null;

      await refreshSamples(nextSampleId);
    } catch (error) {
      console.error(error);
      setDeleteStatus("Delete failed.");
      window.alert(String(error));
    }
  }

  if (loading) {
    return <div style={{ padding: 20, color: "#000" }}>Loading samples...</div>;
  }

  if (!selectedSample) {
    return (
      <div
        style={{
          padding: 20,
          color: "#000",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <h2>No samples found.</h2>
        <p>
          Publish a sample from the desktop pipeline GUI, then refresh this page.
        </p>
      </div>
    );
  }

  const selectedName = getSampleDisplayName(selectedSample);

  return (
    <div
      style={{
        display: "flex",
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        fontFamily: "Arial, sans-serif",
        color: "#000",
      }}
    >
      {!samplePanelOpen && (
        <button
          onClick={() => setSamplePanelOpen(true)}
          style={{
            width: "42px",
            border: "0",
            borderRight: "1px solid #ddd",
            background: "#ffffff",
            color: "#111827",
            cursor: "pointer",
            fontWeight: 700,
            writingMode: "vertical-rl",
            textOrientation: "mixed",
            boxShadow: "4px 0 12px rgba(0,0,0,0.06)",
            zIndex: 20,
          }}
          title="Open sample browser"
        >
          Samples ▶
        </button>
      )}

      {samplePanelOpen && (
        <aside
          style={{
            width: "340px",
            borderRight: "1px solid #ddd",
            overflowY: "auto",
            background: "#f8fafc",
            color: "#000",
            boxShadow: "4px 0 12px rgba(0,0,0,0.05)",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderBottom: "1px solid #e5e7eb",
              background: "#ffffff",
              display: "flex",
              justifyContent: "space-between",
              gap: "12px",
              alignItems: "flex-start",
            }}
          >
            <div>
              <h2 style={{ margin: 0, color: "#000" }}>Graphene Samples</h2>
              <p style={{ margin: "6px 0 0", color: "#6b7280", fontSize: 13 }}>
                Select a published sample.
              </p>
            </div>

            <button
              onClick={() => setSamplePanelOpen(false)}
              style={{
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                background: "#f8fafc",
                cursor: "pointer",
                padding: "4px 8px",
                fontWeight: 700,
              }}
              title="Collapse sample browser"
            >
              ◀
            </button>
          </div>

          <div style={{ padding: "16px" }}>
            {samples.map((sample) => (
              <SampleCard
                key={sample.id}
                sample={sample}
                selected={selectedSample.id === sample.id}
                onClick={() => setSelectedSampleId(sample.id)}
              />
            ))}

            <div
              style={{
                marginTop: "18px",
                background: "#ffffff",
                border: "1px solid #e5e7eb",
                borderRadius: "10px",
                padding: "14px",
              }}
            >
              <h3 style={{ marginTop: 0, color: "#000" }}>Sample Actions</h3>

              <button
                onClick={deleteSelectedSample}
                style={{
                  width: "100%",
                  padding: "9px 10px",
                  borderRadius: "6px",
                  border: "1px solid #fecdd3",
                  background: "#fff1f2",
                  color: "#be123c",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Delete Selected Sample
              </button>

              <div
                style={{
                  marginTop: "8px",
                  color: "#6b7280",
                  fontSize: "12px",
                  lineHeight: 1.4,
                }}
              >
                {deleteStatus || "Deletes the selected sample from the website."}
              </div>
            </div>

            <hr style={{ margin: "20px 0" }} />

            <h3 style={{ color: "#000" }}>Sample Details</h3>

            <div style={{ fontSize: "14px", lineHeight: 1.6, color: "#000" }}>
              <div>
                <strong>ID:</strong> {selectedSample.id}
              </div>

              <div>
                <strong>Name:</strong>{" "}
                {formatValue(selectedSample.metadata?.sample?.name)}
              </div>

              <div>
                <strong>Material:</strong>{" "}
                {formatValue(selectedSample.metadata?.sample?.material_type)}
              </div>

              <div>
                <strong>Objective:</strong>{" "}
                {formatValue(selectedSample.metadata?.sample?.objective)}
              </div>

              <div>
                <strong>Camera:</strong>{" "}
                {formatValue(selectedSample.metadata?.sample?.camera)}
              </div>

              <div>
                <strong>Operator:</strong>{" "}
                {formatValue(selectedSample.metadata?.sample?.operator)}
              </div>

              <hr style={{ margin: "12px 0" }} />

              <div>
                <strong>Grid:</strong>{" "}
                {selectedSample.metadata?.scan?.grid_size_x &&
                selectedSample.metadata?.scan?.grid_size_y
                  ? `${selectedSample.metadata.scan.grid_size_x} × ${selectedSample.metadata.scan.grid_size_y}`
                  : "N/A"}
              </div>

              <div>
                <strong>Overlap:</strong>{" "}
                {formatValue(selectedSample.metadata?.scan?.tile_overlap)}
              </div>

              <div>
                <strong>Scan Order:</strong>{" "}
                {formatValue(selectedSample.metadata?.scan?.scan_order)}
              </div>

              <div>
                <strong>First Tile:</strong>{" "}
                {formatValue(selectedSample.metadata?.scan?.first_tile_index)}
              </div>

              <hr style={{ margin: "12px 0" }} />

              <div>
                <strong>AI Model:</strong>{" "}
                {formatValue(selectedSample.metadata?.detection?.model_id)}
              </div>

              <div>
                <strong>Confidence:</strong>{" "}
                {formatValue(selectedSample.metadata?.detection?.confidence)}
              </div>

              <div>
                <strong>Flake Count:</strong>{" "}
                {formatValue(selectedSample.metadata?.detection?.flake_count)}
              </div>

              <hr style={{ margin: "12px 0" }} />

              <div>
                <strong>Image Size:</strong>{" "}
                {selectedSample.metadata?.image?.width &&
                selectedSample.metadata?.image?.height
                  ? `${selectedSample.metadata.image.width} × ${selectedSample.metadata.image.height}`
                  : "N/A"}
              </div>

              <div>
                <strong>Published:</strong>{" "}
                {formatValue(selectedSample.metadata?.published_at)}
              </div>

              {selectedSample.metadata?.sample?.notes && (
                <>
                  <hr style={{ margin: "12px 0" }} />
                  <div>
                    <strong>Notes:</strong>{" "}
                    {selectedSample.metadata.sample.notes}
                  </div>
                </>
              )}
            </div>
          </div>
        </aside>
      )}

      <main style={{ flex: 1, position: "relative", minWidth: 0 }}>
        <div
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            zIndex: 10,
            background: "rgba(255,255,255,0.9)",
            color: "#000",
            padding: "8px 12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
          }}
        >
          <strong>{selectedName}</strong>
        </div>

        <ChipViewer
          dziPath={selectedSample.dzi}
          flakesPath={selectedSample.flakes}
          annotationsPath={selectedSample.annotations}
        />
      </main>
    </div>
  );
}
