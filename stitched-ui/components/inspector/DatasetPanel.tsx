import type { AnnotationBox, Flake } from "../viewer/viewerTypes";

type DatasetPanelProps = {
  boxes: AnnotationBox[];
  flakes: Flake[];
  annotationsPath: string;
  dziPath: string;
};

function countByLabel(boxes: AnnotationBox[]) {
  return boxes.reduce<Record<string, number>>((counts, box) => {
    const label = box.label || "unlabeled";
    counts[label] = (counts[label] ?? 0) + 1;
    return counts;
  }, {});
}

export default function DatasetPanel({ boxes, flakes, annotationsPath, dziPath }: DatasetPanelProps) {
  const labelCounts = countByLabel(boxes);
  const samplePath = annotationsPath.replace(/\/annotations\.json$/, "");

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>Current Sample</h3>
        <div style={{ lineHeight: 1.7 }}>
          <b>Sample path:</b>
          <br />
          <span style={{ color: "#475569" }}>{samplePath}</span>
          <br />
          <b>DZI:</b>
          <br />
          <span style={{ color: "#475569" }}>{dziPath}</span>
        </div>
      </div>

      <div style={{ marginTop: 12, background: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>Annotation Summary</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <div style={{ color: "#6b7280" }}>Manual boxes</div>
            <div style={{ fontWeight: 700, fontSize: 22 }}>{boxes.length}</div>
          </div>
          <div>
            <div style={{ color: "#6b7280" }}>Detected markers</div>
            <div style={{ fontWeight: 700, fontSize: 22 }}>{flakes.length}</div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 12, background: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>Classes</h3>
        {Object.keys(labelCounts).length === 0 ? (
          <p style={{ color: "#64748b" }}>No classes yet.</p>
        ) : (
          Object.entries(labelCounts).map(([label, count]) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f1f5f9" }}>
              <span>{label}</span>
              <b>{count}</b>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
