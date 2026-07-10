"use client";

import { useEffect, useRef, useState } from "react";
import WorkspaceInspector from "../inspector/WorkspaceInspector";
import type { AnnotationBox, AnnotationFile, Flake, ToolMode } from "./viewerTypes";

type ChipViewerProps = {
  dziPath: string;
  flakesPath: string;
  annotationsPath: string;
};

type OpenSeadragonPoint = {
  x: number;
  y: number;
};

type OpenSeadragonViewport = {
  pointFromPixel(point: OpenSeadragonPoint): OpenSeadragonPoint;
  viewportToImageCoordinates(point: OpenSeadragonPoint): OpenSeadragonPoint;
  imageToViewportCoordinates(x: number, y: number): OpenSeadragonPoint;
  pixelFromPoint(point: OpenSeadragonPoint, current?: boolean): OpenSeadragonPoint;
  zoomBy(factor: number, refPoint?: OpenSeadragonPoint): void;
  applyConstraints(): void;
};

type OpenSeadragonViewer = {
  viewport: OpenSeadragonViewport;
  clearOverlays(): void;
  addOverlay(options: { element: HTMLElement; location: OpenSeadragonPoint }): void;
  addHandler(name: string, handler: () => void): void;
  destroy(): void;
};

type OpenSeadragonFactory = {
  (options: {
    element: HTMLElement;
    prefixUrl: string;
    tileSources: string;
    showNavigator: boolean;
    gestureSettingsMouse: {
      clickToZoom: boolean;
      dblClickToZoom: boolean;
      scrollToZoom: boolean;
      dragToPan: boolean;
    };
  }): OpenSeadragonViewer;
  Point: new (x: number, y: number) => OpenSeadragonPoint;
};

function getFlakeX(flake: Flake): number | null {
  if (typeof flake.x === "number") return flake.x;
  if (flake.centroid) return flake.centroid.x;
  if (flake.bbox && typeof flake.bbox.x === "number") return flake.bbox.x;
  return null;
}

function getFlakeY(flake: Flake): number | null {
  if (typeof flake.y === "number") return flake.y;
  if (flake.centroid) return flake.centroid.y;
  if (flake.bbox && typeof flake.bbox.y === "number") return flake.bbox.y;
  return null;
}

function makeBoxId() {
  return `box_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function normalizeBox(start: { x: number; y: number }, end: { x: number; y: number }) {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);

  return { x, y, width, height };
}

export default function ChipViewer({ dziPath, flakesPath, annotationsPath }: ChipViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const viewerInstanceRef = useRef<OpenSeadragonViewer | null>(null);
  const pointConstructorRef = useRef<OpenSeadragonFactory["Point"] | null>(null);
  const overlaySvgRef = useRef<SVGSVGElement | null>(null);

  const boxesRef = useRef<AnnotationBox[]>([]);
  const isDrawingRef = useRef(false);
  const drawStartRef = useRef<{ x: number; y: number } | null>(null);
  const draftBoxRef = useRef<AnnotationBox | null>(null);

  const [flakes, setFlakes] = useState<Flake[]>([]);
  const [boxes, setBoxes] = useState<AnnotationBox[]>([]);
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null);
  const [toolMode, setToolMode] = useState<ToolMode>("pointer");
  const [saveStatus, setSaveStatus] = useState("");
  const [inspectorOpen, setInspectorOpen] = useState(true);

  const selectedBox = boxes.find((box) => String(box.id) === String(selectedBoxId)) ?? null;

  function updateBoxes(nextBoxes: AnnotationBox[]) {
    boxesRef.current = nextBoxes;
    setBoxes(nextBoxes);
    redrawBoxes(nextBoxes);
  }

  function imagePointFromPointer(event: React.PointerEvent<SVGSVGElement>) {
    const viewer = viewerInstanceRef.current;
    const svg = overlaySvgRef.current;
    if (!viewer || !svg) return null;

    const rect = svg.getBoundingClientRect();
    const Point = pointConstructorRef.current;
    if (!Point) return null;

    const pixelPoint = new Point(
      event.clientX - rect.left,
      event.clientY - rect.top
    );

    const viewportPoint = viewer.viewport.pointFromPixel(pixelPoint);
    const imagePoint = viewer.viewport.viewportToImageCoordinates(viewportPoint);

    return { x: imagePoint.x, y: imagePoint.y };
  }

  function boxToScreenRect(box: AnnotationBox) {
    const viewer = viewerInstanceRef.current;
    if (!viewer) return null;

    const topLeftViewport = viewer.viewport.imageToViewportCoordinates(box.x, box.y);
    const bottomRightViewport = viewer.viewport.imageToViewportCoordinates(
      box.x + box.width,
      box.y + box.height
    );

    const topLeftPixel = viewer.viewport.pixelFromPoint(topLeftViewport, true);
    const bottomRightPixel = viewer.viewport.pixelFromPoint(bottomRightViewport, true);

    return {
      x: topLeftPixel.x,
      y: topLeftPixel.y,
      width: bottomRightPixel.x - topLeftPixel.x,
      height: bottomRightPixel.y - topLeftPixel.y,
    };
  }

  function redrawBoxes(nextBoxes = boxesRef.current) {
    const svg = overlaySvgRef.current;
    if (!svg) return;

    while (svg.firstChild) svg.removeChild(svg.firstChild);

    nextBoxes.forEach((box) => {
      const rect = boxToScreenRect(box);
      if (!rect) return;

      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      const boxRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");

      boxRect.setAttribute("x", String(rect.x));
      boxRect.setAttribute("y", String(rect.y));
      boxRect.setAttribute("width", String(rect.width));
      boxRect.setAttribute("height", String(rect.height));
      boxRect.setAttribute("fill", box.id === selectedBoxId ? "rgba(37,99,235,0.16)" : "rgba(239,68,68,0.10)");
      boxRect.setAttribute("stroke", box.id === selectedBoxId ? "#2563eb" : "#ef4444");
      boxRect.setAttribute("stroke-width", box.id === selectedBoxId ? "3" : "2");
      boxRect.style.cursor = "pointer";

      boxRect.addEventListener("pointerdown", (event) => {
        event.stopPropagation();
        setSelectedBoxId(box.id);
        setInspectorOpen(true);
      });

      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", String(rect.x));
      label.setAttribute("y", String(Math.max(14, rect.y - 5)));
      label.setAttribute("font-size", "13");
      label.setAttribute("font-weight", "700");
      label.setAttribute("fill", box.id === selectedBoxId ? "#2563eb" : "#ef4444");
      label.textContent = box.label || "flake";

      group.appendChild(boxRect);
      group.appendChild(label);
      svg.appendChild(group);
    });
  }

  function redrawFlakeMarkers(viewer: OpenSeadragonViewer, nextFlakes: Flake[]) {
    viewer.clearOverlays();

    nextFlakes.forEach((flake) => {
      const x = getFlakeX(flake);
      const y = getFlakeY(flake);
      if (x === null || y === null) return;

      const marker = document.createElement("div");
      marker.innerText = String(flake.id);
      marker.style.background = "rgba(34,197,94,0.9)";
      marker.style.border = "1px solid #111827";
      marker.style.borderRadius = "999px";
      marker.style.padding = "3px 7px";
      marker.style.fontSize = "11px";
      marker.style.fontWeight = "700";
      marker.style.color = "white";
      marker.style.whiteSpace = "nowrap";
      marker.style.pointerEvents = "none";

      viewer.addOverlay({
        element: marker,
        location: viewer.viewport.imageToViewportCoordinates(x, y),
      });
    });
  }

  function getViewportPointFromMouseEvent(
    event: React.MouseEvent<SVGSVGElement> | React.WheelEvent<SVGSVGElement>
  ) {
    const viewer = viewerInstanceRef.current;
    const svg = overlaySvgRef.current;
    if (!viewer || !svg) return null;

    const rect = svg.getBoundingClientRect();
    const Point = pointConstructorRef.current;
    if (!Point) return null;

    const pixelPoint = new Point(
      event.clientX - rect.left,
      event.clientY - rect.top
    );

    return viewer.viewport.pointFromPixel(pixelPoint);
  }

  function handleOverlayWheel(event: React.WheelEvent<SVGSVGElement>) {
    const viewer = viewerInstanceRef.current;
    if (!viewer) return;

    event.preventDefault();
    event.stopPropagation();

    const viewportPoint = getViewportPointFromMouseEvent(event);
    if (!viewportPoint) return;

    const zoomFactor = event.deltaY < 0 ? 1.2 : 1 / 1.2;

    viewer.viewport.zoomBy(zoomFactor, viewportPoint);
    viewer.viewport.applyConstraints();
    redrawBoxes();
  }

  function handleOverlayDoubleClick(event: React.MouseEvent<SVGSVGElement>) {
    const viewer = viewerInstanceRef.current;
    if (!viewer) return;

    event.preventDefault();
    event.stopPropagation();

    const viewportPoint = getViewportPointFromMouseEvent(event);
    if (!viewportPoint) return;

    viewer.viewport.zoomBy(2, viewportPoint);
    viewer.viewport.applyConstraints();
    redrawBoxes();
  }

  function handlePointerDown(event: React.PointerEvent<SVGSVGElement>) {
    if (toolMode !== "box") return;
    if (event.detail > 1) return;
    if (event.button !== 0) return;

    const imagePoint = imagePointFromPointer(event);
    if (!imagePoint) return;

    event.preventDefault();
    event.stopPropagation();

    isDrawingRef.current = true;
    drawStartRef.current = imagePoint;

    const now = new Date().toISOString();

    draftBoxRef.current = {
      id: makeBoxId(),
      x: imagePoint.x,
      y: imagePoint.y,
      width: 0,
      height: 0,
      label: "graphene",
      source: "manual",
      confidence: 1,
      notes: "",
      created: now,
      modified: now,
    };
  }

  function handlePointerMove(event: React.PointerEvent<SVGSVGElement>) {
    if (!isDrawingRef.current || !drawStartRef.current || !draftBoxRef.current) return;

    const imagePoint = imagePointFromPointer(event);
    if (!imagePoint) return;

    const normalized = normalizeBox(drawStartRef.current, imagePoint);
    draftBoxRef.current = {
      ...draftBoxRef.current,
      ...normalized,
      modified: new Date().toISOString(),
    };

    redrawBoxes([...boxesRef.current, draftBoxRef.current]);
  }

  function handlePointerUp(event: React.PointerEvent<SVGSVGElement>) {
    if (!isDrawingRef.current || !draftBoxRef.current) return;

    event.preventDefault();
    event.stopPropagation();

    const finalBox = draftBoxRef.current;
    isDrawingRef.current = false;
    drawStartRef.current = null;
    draftBoxRef.current = null;

    if (finalBox.width < 5 || finalBox.height < 5) {
      redrawBoxes(boxesRef.current);
      return;
    }

    const nextBoxes = [...boxesRef.current, finalBox];
    updateBoxes(nextBoxes);
    setSelectedBoxId(finalBox.id);
    setInspectorOpen(true);
  }

  function updateSelectedBoxField(field: keyof AnnotationBox, value: string) {
    if (!selectedBoxId) return;

    const nextBoxes = boxes.map((box) =>
      box.id === selectedBoxId
        ? { ...box, [field]: value, modified: new Date().toISOString() }
        : box
    );

    updateBoxes(nextBoxes);
  }

  function deleteSelectedBox() {
    if (!selectedBoxId) return;

    const nextBoxes = boxes.filter((box) => box.id !== selectedBoxId);
    updateBoxes(nextBoxes);
    setSelectedBoxId(null);
  }

  async function saveAnnotations() {
    setSaveStatus("Saving...");

    const payload: AnnotationFile = { version: 1, boxes };

    const response = await fetch("/api/save-annotations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ annotationsPath, data: payload }),
    });

    setSaveStatus(response.ok ? "Saved." : "Save failed.");
  }

  useEffect(() => {
    let viewer: OpenSeadragonViewer | null = null;
    let cancelled = false;

    async function init() {
      if (!viewerRef.current) return;

      const OpenSeadragon = (await import("openseadragon")).default as unknown as OpenSeadragonFactory;
      pointConstructorRef.current = OpenSeadragon.Point;

      if (cancelled) return;

      viewer = OpenSeadragon({
        element: viewerRef.current,
        prefixUrl: "https://openseadragon.github.io/openseadragon/images/",
        tileSources: dziPath,
        showNavigator: true,
        gestureSettingsMouse: {
          clickToZoom: false,
          dblClickToZoom: true,
          scrollToZoom: true,
          dragToPan: true,
        },
      });

      viewerInstanceRef.current = viewer;

      viewer.addHandler("open", async () => {
        if (!viewer) return;

        const flakeResponse = await fetch(flakesPath);
        const flakeData = flakeResponse.ok ? await flakeResponse.json() : { flakes: [] };

        const loadedFlakes: Flake[] = flakeData.flakes || [];
        setFlakes(loadedFlakes);
        redrawFlakeMarkers(viewer, loadedFlakes);

        const annotationResponse = await fetch(annotationsPath);
        const annotationData: AnnotationFile = annotationResponse.ok
          ? await annotationResponse.json()
          : { version: 1, boxes: [] };

        updateBoxes(annotationData.boxes || []);
      });

      viewer.addHandler("animation", () => redrawBoxes());
      viewer.addHandler("zoom", () => redrawBoxes());
      viewer.addHandler("pan", () => redrawBoxes());
      viewer.addHandler("resize", () => redrawBoxes());
    }

    init();

    return () => {
      cancelled = true;
      if (viewer) viewer.destroy();
    };
  }, [dziPath, flakesPath, annotationsPath]);

  return (
    <div style={{ width: "100%", height: "90vh", display: "flex" }}>
      <div style={{ position: "relative", flex: 1, height: "100%" }}>
        <div ref={viewerRef} style={{ width: "100%", height: "100%" }} />

        <svg
          ref={overlaySvgRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onWheel={handleOverlayWheel}
          onDoubleClick={handleOverlayDoubleClick}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            pointerEvents: toolMode === "box" ? "auto" : "none",
            touchAction: "none",
            zIndex: 10,
          }}
        />
      </div>

      <button
        onClick={() => setInspectorOpen((open) => !open)}
        style={{
          position: "absolute",
          top: "12px",
          right: inspectorOpen ? "370px" : "12px",
          zIndex: 30,
          padding: "8px 10px",
          borderRadius: "6px",
          border: "1px solid #cfd6df",
          background: "white",
          cursor: "pointer",
          fontWeight: 700,
        }}
      >
        {inspectorOpen ? "Hide Workspace" : "Show Workspace"}
      </button>

      {inspectorOpen && (
        <WorkspaceInspector
          toolMode={toolMode}
          onToolModeChange={setToolMode}
          boxes={boxes}
          flakes={flakes}
          selectedBox={selectedBox}
          saveStatus={saveStatus}
          dziPath={dziPath}
          annotationsPath={annotationsPath}
          onUpdateSelectedBoxField={updateSelectedBoxField}
          onDeleteSelectedBox={deleteSelectedBox}
          onSaveAnnotations={saveAnnotations}
        />
      )}
    </div>
  );
}
