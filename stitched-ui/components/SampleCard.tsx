import type { Sample } from "@/types/sample";
import { getSampleDisplayName } from "@/types/sample";

type SampleCardProps = {
  sample: Sample;
  selected: boolean;
  onClick: () => void;
};

export default function SampleCard({
  sample,
  selected,
  onClick,
}: SampleCardProps) {
  const name = getSampleDisplayName(sample);
  const objective = sample.metadata?.sample?.objective ?? "Unknown objective";
  const material = sample.metadata?.sample?.material_type ?? "Unknown material";
  const flakeCount = sample.metadata?.detection?.flake_count;

  return (
    <button
      onClick={onClick}
      style={{
        display: "block",
        width: "100%",
        marginBottom: "12px",
        padding: "10px",
        textAlign: "left",
        border: selected ? "2px solid #0070f3" : "1px solid #ccc",
        borderRadius: "8px",
        background: selected ? "#e8f2ff" : "white",
        color: "#000",
        cursor: "pointer",
      }}
    >
      {sample.preview && (
        <img
          src={sample.preview}
          alt={name}
          style={{
            width: "100%",
            height: "100px",
            objectFit: "cover",
            borderRadius: "6px",
            marginBottom: "8px",
          }}
        />
      )}

      <strong style={{ color: "#000", fontSize: "16px" }}>{name}</strong>

      <div style={{ fontSize: "12px", color: "#333", marginTop: "4px" }}>
        {material} · {objective}
      </div>

      <div style={{ fontSize: "12px", color: "#555", marginTop: "4px" }}>
        {typeof flakeCount === "number"
          ? `${flakeCount} detected flakes`
          : "Flake count unavailable"}
      </div>
    </button>
  );
}