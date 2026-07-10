import json
import argparse
from pathlib import Path

import cv2
import numpy as np
import tifffile as tiff


def load_image(path):
    path = Path(path)

    if path.suffix.lower() in [".tif", ".tiff"]:
        img = tiff.imread(str(path))
    else:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Could not read image: {path}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    if img.shape[-1] == 4:
        img = img[:, :, :3]

    if img.dtype != np.uint8:
        img = img.astype(np.float32)
        img -= img.min()
        img /= max(img.max(), 1e-6)
        img = (img * 255).astype(np.uint8)

    return img


def get_object_pixels(channel_img, contour):
    x, y, w, h = cv2.boundingRect(contour)
    roi = channel_img[y:y + h, x:x + w]

    mask = np.zeros((h, w), dtype=np.uint8)
    shifted = contour - np.array([[[x, y]]])
    cv2.drawContours(mask, [shifted], -1, 255, -1)

    return roi[mask > 0]


def compute_features(img, lab, gray, contour):
    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)

    perimeter = cv2.arcLength(contour, True)
    aspect_ratio = max(w / max(h, 1), h / max(w, 1))

    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / max(hull_area, 1)

    bbox_area = w * h
    extent = area / max(bbox_area, 1)

    circularity = 4 * np.pi * area / max(perimeter ** 2, 1e-6)
    perimeter_area_ratio = perimeter / max(area, 1)

    rgb_pixels = get_object_pixels(img, contour)
    lab_pixels = get_object_pixels(lab, contour)

    mean_rgb = np.mean(rgb_pixels, axis=0)
    mean_lab = np.mean(lab_pixels, axis=0)
    std_lab = np.std(lab_pixels, axis=0)

    L, A, B = mean_lab
    R, G, Blue = mean_rgb

    # Purple score: target flakes are magenta/purple compared to pink substrate.
    purple_score = 0

    if A > 135:
        purple_score += 1
    if B < 140:
        purple_score += 1
    if R > G:
        purple_score += 1
    if Blue > G:
        purple_score += 1
    if (A - B) > -5:
        purple_score += 1

    # Edge density, but not overly strict.
    roi_gray = gray[y:y + h, x:x + w]
    edges = cv2.Canny(roi_gray, 35, 100)

    obj_mask = np.zeros((h, w), dtype=np.uint8)
    shifted = contour - np.array([[[x, y]]])
    cv2.drawContours(obj_mask, [shifted], -1, 255, -1)

    edge_density = np.logical_and(edges > 0, obj_mask > 0).sum() / max((obj_mask > 0).sum(), 1)

    # Glue tends to be fragmented/stringy/low-solidity.
    glue_score = 0

    if solidity < 0.55:
        glue_score += 2
    if extent < 0.25:
        glue_score += 1
    if perimeter_area_ratio > 0.18:
        glue_score += 1
    if aspect_ratio > 7:
        glue_score += 1
    if area > 900 and solidity < 0.65:
        glue_score += 1
    if edge_density < 0.008 and area > 500:
        glue_score += 1

    flake_score = purple_score + (2 if solidity > 0.65 else 0) + (1 if extent > 0.25 else 0) - glue_score

    return {
        "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
        "area_px": round(float(area), 2),
        "perimeter": round(float(perimeter), 2),
        "aspect_ratio": round(float(aspect_ratio), 3),
        "solidity": round(float(solidity), 3),
        "extent": round(float(extent), 3),
        "circularity": round(float(circularity), 3),
        "perimeter_area_ratio": round(float(perimeter_area_ratio), 4),
        "edge_density": round(float(edge_density), 4),
        "mean_rgb": [round(float(v), 2) for v in mean_rgb],
        "mean_lab": [round(float(v), 2) for v in mean_lab],
        "std_lab": [round(float(v), 2) for v in std_lab],
        "purple_score": int(purple_score),
        "glue_score": int(glue_score),
        "flake_score": int(flake_score),
    }


def detect_flakes(
    img,
    min_area=40,
    max_area=8000,
    threshold=16,
    blur=301,
    min_flake_score=2,
    min_solidity=0.35,
    max_glue_score=4,
):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    if blur % 2 == 0:
        blur += 1

    bg = cv2.GaussianBlur(lab, (blur, blur), 0)

    diff = lab.astype(np.float32) - bg.astype(np.float32)
    dist = np.sqrt(np.sum(diff ** 2, axis=2))

    # Also emphasize purple/magenta objects.
    L, A, B = cv2.split(lab)
    purple_mask = ((A > 132) & (B < 150)).astype(np.uint8) * 255
    contrast_mask = (dist > threshold).astype(np.uint8) * 255

    mask = cv2.bitwise_or(contrast_mask, purple_mask)

    small_kernel = np.ones((3, 3), np.uint8)
    medium_kernel = np.ones((5, 5), np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, small_kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, medium_kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    flakes = []
    rejected = {
        "too_small": 0,
        "too_large": 0,
        "low_solidity": 0,
        "glue_like": 0,
        "low_flake_score": 0,
    }

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < min_area:
            rejected["too_small"] += 1
            continue

        if area > max_area:
            rejected["too_large"] += 1
            continue

        features = compute_features(img, lab, gray, contour)

        if features["solidity"] < min_solidity:
            rejected["low_solidity"] += 1
            continue

        if features["glue_score"] > max_glue_score:
            rejected["glue_like"] += 1
            continue

        if features["flake_score"] < min_flake_score:
            rejected["low_flake_score"] += 1
            continue

        M = cv2.moments(contour)
        if M["m00"] == 0:
            x = features["bbox"]["x"]
            y = features["bbox"]["y"]
            w = features["bbox"]["width"]
            h = features["bbox"]["height"]
            cx = x + w / 2
            cy = y + h / 2
        else:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]

        perimeter = cv2.arcLength(contour, True)
        epsilon = 0.004 * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        polygon = approx.reshape(-1, 2).tolist()

        flakes.append({
            "id": f"flake_{len(flakes) + 1:05d}",
            "x": round(float(cx), 2),
            "y": round(float(cy), 2),
            "label": "purple_candidate",
            "polygon": polygon,
            **features,
        })

    return flakes, mask, rejected


def save_preview(img, flakes, output_path):
    preview = img.copy()

    for flake in flakes:
        bbox = flake["bbox"]
        x1 = bbox["x"]
        y1 = bbox["y"]
        x2 = x1 + bbox["width"]
        y2 = y1 + bbox["height"]

        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(preview, (int(flake["x"]), int(flake["y"])), 4, (255, 0, 0), -1)

        cv2.putText(
            preview,
            str(flake["flake_score"]),
            (x1, max(0, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    cv2.imwrite(str(output_path), cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--image", required=True)
    parser.add_argument("--out", default="public/flakes.json")
    parser.add_argument("--mask", default="public/flake_mask.png")
    parser.add_argument("--preview", default="public/flake_preview.png")

    parser.add_argument("--min-area", type=float, default=40)
    parser.add_argument("--max-area", type=float, default=8000)
    parser.add_argument("--threshold", type=float, default=16)
    parser.add_argument("--blur", type=int, default=301)

    parser.add_argument("--min-flake-score", type=int, default=2)
    parser.add_argument("--min-solidity", type=float, default=0.35)
    parser.add_argument("--max-glue-score", type=int, default=4)

    args = parser.parse_args()

    img = load_image(args.image)

    flakes, mask, rejected = detect_flakes(
        img,
        min_area=args.min_area,
        max_area=args.max_area,
        threshold=args.threshold,
        blur=args.blur,
        min_flake_score=args.min_flake_score,
        min_solidity=args.min_solidity,
        max_glue_score=args.max_glue_score,
    )

    output = {
        "image_width": img.shape[1],
        "image_height": img.shape[0],
        "flake_count": len(flakes),
        "settings": vars(args),
        "rejected_counts": rejected,
        "flakes": flakes,
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)

    cv2.imwrite(args.mask, mask)
    save_preview(img, flakes, args.preview)

    print()
    print(f"Detected purple candidate flakes: {len(flakes)}")
    print("Rejected:")
    for k, v in rejected.items():
        print(f"  {k}: {v}")
    print()
    print(f"Saved JSON: {args.out}")
    print(f"Saved mask: {args.mask}")
    print(f"Saved preview: {args.preview}")
    print()


if __name__ == "__main__":
    main()