import type { ToolMode } from "./viewerTypes";

type ViewerToolbarProps = {
  toolMode: ToolMode;
  onToolModeChange: (mode: ToolMode) => void;
};

const tools: { id: ToolMode; label: string; hint: string }[] = [
  { id: "pointer", label: "Pointer", hint: "Pan and inspect" },
  { id: "box", label: "Box", hint: "Draw bounding boxes" },
  { id: "zoom", label: "Zoom", hint: "Zoom only" },
];

export default function ViewerToolbar({
  toolMode,
  onToolModeChange,
}: ViewerToolbarProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: "8px",
        marginTop: "12px",
      }}
    >
      {tools.map((tool) => (
        <button
          key={tool.id}
          onClick={() => onToolModeChange(tool.id)}
          title={tool.hint}
          style={{
            padding: "9px 10px",
            borderRadius: "6px",
            border: toolMode === tool.id ? "1px solid #2563eb" : "1px solid #cfd6df",
            background: toolMode === tool.id ? "#2563eb" : "#f8fafc",
            color: toolMode === tool.id ? "white" : "#111827",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          {tool.label}
        </button>
      ))}
    </div>
  );
}
