import type { AnnotationBox, Flake } from "../viewer/viewerTypes";

type AnnotationPanelProps = {
  boxes: AnnotationBox[];
  flakes: Flake[];
  selectedBox: AnnotationBox | null;
  saveStatus: string;
  onUpdateSelectedBoxField: (field: keyof AnnotationBox, value: string) => void;
  onDeleteSelectedBox: () => void;
  onSaveAnnotations: () => void;
};

const buttonStyle: React.CSSProperties = {
  width: "100%",
  padding: "9px 10px",
  borderRadius: "6px",
  border: "1px solid #cfd6df",
  background: "#f8fafc",
  cursor: "pointer",
  fontWeight: 600,
  marginBottom: "8px",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  marginTop: "4px",
  marginBottom: "12px",
  border: "1px solid #cfd6df",
  borderRadius: "6px",
  fontSize: "13px",
  boxSizing: "border-box",
};

const labelStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: "12px",
  color: "#374151",
};

export default function AnnotationPanel({
  boxes,
  flakes,
  selectedBox,
  saveStatus,
  onUpdateSelectedBoxField,
  onDeleteSelectedBox,
  onSaveAnnotations,
}: AnnotationPanelProps) {
  return (
    <div style={{ padding: "16px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "10px",
          marginBottom: "16px",
        }}
      >
        <div style={{ background: "white", padding: "10px" }}>
          <div style={{ color: "#6b7280" }}>Boxes</div>
          <div style={{ fontWeight: 700, fontSize: "20px" }}>{boxes.length}</div>
        </div>
        <div style={{ background: "white", padding: "10px" }}>
          <div style={{ color: "#6b7280" }}>Flake markers</div>
          <div style={{ fontWeight: 700, fontSize: "20px" }}>{flakes.length}</div>
        </div>
      </div>

      {selectedBox ? (
        <div
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: "10px",
            padding: "14px",
          }}
        >
          <label style={labelStyle}>Label</label>
          <input
            value={selectedBox.label}
            onChange={(e) => onUpdateSelectedBoxField("label", e.target.value)}
            style={inputStyle}
          />

          <label style={labelStyle}>Notes</label>
          <textarea
            value={selectedBox.notes ?? ""}
            onChange={(e) => onUpdateSelectedBoxField("notes", e.target.value)}
            style={{
              ...inputStyle,
              height: "90px",
              resize: "vertical",
              fontFamily: "inherit",
            }}
          />

          <div
            style={{
              background: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              padding: "10px",
              marginBottom: "12px",
              lineHeight: 1.6,
            }}
          >
            <b>Box coordinates</b>
            <br />X: {Math.round(selectedBox.x)}
            <br />Y: {Math.round(selectedBox.y)}
            <br />W: {Math.round(selectedBox.width)}
            <br />H: {Math.round(selectedBox.height)}
          </div>

          <button
            onClick={onDeleteSelectedBox}
            style={{
              ...buttonStyle,
              background: "#fff1f2",
              borderColor: "#fecdd3",
              color: "#be123c",
            }}
          >
            Delete Selected Box
          </button>
        </div>
      ) : (
        <div
          style={{
            background: "#ffffff",
            border: "1px dashed #cbd5e1",
            borderRadius: "10px",
            padding: "16px",
            color: "#64748b",
            lineHeight: 1.5,
          }}
        >
          No box selected.
          <br />Draw a box or click an existing box.
        </div>
      )}

      <div
        style={{
          marginTop: "16px",
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: "10px",
          padding: "14px",
        }}
      >
        <button
          onClick={onSaveAnnotations}
          style={{
            ...buttonStyle,
            background: "#2563eb",
            borderColor: "#2563eb",
            color: "white",
            marginBottom: "6px",
          }}
        >
          Save Annotations
        </button>

        <div style={{ color: "#6b7280", fontSize: "12px" }}>
          {saveStatus || "No recent save."}
        </div>
      </div>
    </div>
  );
}
