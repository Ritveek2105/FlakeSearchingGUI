import { useState } from "react";
import ViewerToolbar from "../viewer/ViewerToolbar";
import type { AnnotationBox, Flake, InspectorTab, ToolMode } from "../viewer/viewerTypes";
import InspectorTabs from "./InspectorTabs";
import AnnotationPanel from "./AnnotationPanel";
import DatasetPanel from "./DatasetPanel";
import ExportPanel from "./ExportPanel";
import AIPanel from "./AIPanel";

type WorkspaceInspectorProps = {
  toolMode: ToolMode;
  onToolModeChange: (mode: ToolMode) => void;
  boxes: AnnotationBox[];
  flakes: Flake[];
  selectedBox: AnnotationBox | null;
  saveStatus: string;
  dziPath: string;
  annotationsPath: string;
  onUpdateSelectedBoxField: (field: keyof AnnotationBox, value: string) => void;
  onDeleteSelectedBox: () => void;
  onSaveAnnotations: () => void;
};

export default function WorkspaceInspector({
  toolMode,
  onToolModeChange,
  boxes,
  flakes,
  selectedBox,
  saveStatus,
  dziPath,
  annotationsPath,
  onUpdateSelectedBoxField,
  onDeleteSelectedBox,
  onSaveAnnotations,
}: WorkspaceInspectorProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("annotations");

  return (
    <aside
      style={{
        width: "360px",
        borderLeft: "1px solid #d1d5db",
        background: "#f8fafc",
        color: "#111827",
        fontSize: "13px",
        overflowY: "auto",
      }}
    >
      <div style={{ padding: "16px", background: "#ffffff", borderBottom: "1px solid #e5e7eb" }}>
        <h2 style={{ margin: 0, fontSize: "18px" }}>Annotation Workspace</h2>
        <p style={{ color: "#6b7280", marginBottom: 0 }}>
          Pointer pans. Box draws annotations.
        </p>
        <ViewerToolbar toolMode={toolMode} onToolModeChange={onToolModeChange} />
      </div>

      <InspectorTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === "annotations" && (
        <AnnotationPanel
          boxes={boxes}
          flakes={flakes}
          selectedBox={selectedBox}
          saveStatus={saveStatus}
          onUpdateSelectedBoxField={onUpdateSelectedBoxField}
          onDeleteSelectedBox={onDeleteSelectedBox}
          onSaveAnnotations={onSaveAnnotations}
        />
      )}

      {activeTab === "dataset" && (
        <DatasetPanel
          boxes={boxes}
          flakes={flakes}
          annotationsPath={annotationsPath}
          dziPath={dziPath}
        />
      )}

      {activeTab === "export" && <ExportPanel boxCount={boxes.length} annotationsPath={annotationsPath} />}

      {activeTab === "ai" && <AIPanel />}
    </aside>
  );
}
