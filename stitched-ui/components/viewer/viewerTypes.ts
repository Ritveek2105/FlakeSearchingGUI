export type Flake = {
  id: string | number;
  x?: number;
  y?: number;
  centroid?: { x: number; y: number };
  bbox?: { x?: number; y?: number };
  label?: string;
  material?: string;
  source?: string;
};

export type AnnotationBox = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  source: "manual" | "ai";
  confidence?: number;
  notes?: string;
  created?: string;
  modified?: string;
};

export type AnnotationFile = {
  version: number;
  boxes: AnnotationBox[];
};

export type ToolMode = "pointer" | "box" | "zoom";
export type InspectorTab = "annotations" | "dataset" | "export" | "ai";
