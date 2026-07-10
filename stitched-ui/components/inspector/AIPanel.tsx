export default function AIPanel() {
  return (
    <div style={{ padding: "16px" }}>
      <div style={{ background: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>AI Assistance</h3>
        <p style={{ color: "#64748b", lineHeight: 1.5 }}>
          Later this panel will run Roboflow predictions, show suggested boxes, and let you accept or reject AI annotations.
        </p>
      </div>
    </div>
  );
}
