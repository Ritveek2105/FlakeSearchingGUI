import type { InspectorTab } from "../viewer/viewerTypes";

type InspectorTabsProps = {
  activeTab: InspectorTab;
  onTabChange: (tab: InspectorTab) => void;
};

const tabs: { id: InspectorTab; label: string }[] = [
  { id: "annotations", label: "Annotations" },
  { id: "dataset", label: "Dataset" },
  { id: "export", label: "Export" },
  { id: "ai", label: "AI" },
];

export default function InspectorTabs({ activeTab, onTabChange }: InspectorTabsProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "8px",
        padding: "12px 16px",
        background: "#ffffff",
        borderBottom: "1px solid #e5e7eb",
      }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            padding: "8px 10px",
            borderRadius: "6px",
            border: activeTab === tab.id ? "1px solid #2563eb" : "1px solid #cfd6df",
            background: activeTab === tab.id ? "#2563eb" : "#f8fafc",
            color: activeTab === tab.id ? "white" : "#111827",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: "12px",
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
