export type SampleCatalogEntry = {
  id: string;
  path: string;
};

export type SampleMetadata = {
  id: string;
  published_at?: string;

  sample?: {
    name?: string;
    material_type?: string;
    objective?: string;
    camera?: string;
    operator?: string;
    notes?: string;
  };

  scan?: {
    grid_size_x?: number;
    grid_size_y?: number;
    tile_overlap?: number;
    scan_order?: string;
    first_tile_index?: number;
  };

  detection?: {
    model_id?: string;
    confidence?: number;
    flake_count?: number | null;
  };

  image?: {
    width?: number | null;
    height?: number | null;
    source_image?: string;
  };
};

export type Sample = SampleCatalogEntry & {
  metadata?: SampleMetadata;
  dzi: string;
  flakes: string;
  annotations: string;
  preview: string;
  metadataPath: string;
};

export type SamplesCatalogFile = {
  version?: number;
  samples: SampleCatalogEntry[];
};

export function normalizeSamplesFile(data: unknown): SampleCatalogEntry[] {
  if (Array.isArray(data)) {
    return data as SampleCatalogEntry[];
  }

  if (
    data &&
    typeof data === "object" &&
    "samples" in data &&
    Array.isArray((data as SamplesCatalogFile).samples)
  ) {
    return (data as SamplesCatalogFile).samples;
  }

  return [];
}

export function buildSampleFromCatalogEntry(entry: SampleCatalogEntry): Sample {
  return {
    ...entry,
    dzi: `${entry.path}/image.dzi`,
    flakes: `${entry.path}/flakes.json`,
    annotations: `${entry.path}/annotations.json`,
    preview: `${entry.path}/preview.png`,
    metadataPath: `${entry.path}/metadata.json`,
  };
}

export function getSampleDisplayName(sample: Sample): string {
  return sample.metadata?.sample?.name || sample.id;
}