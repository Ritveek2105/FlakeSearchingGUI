import numpy as np


def select_bare_chip_points_grid_blocks(
    lab,
    flake_mask,
    block_size=80,
    candidates_per_block=150,
    patch_radius=3,
    max_texture_allowed=6,
    max_bare_points=8000,
):
    """
    Select bare-chip points using square grid blocks.

    The image is divided into blocks. In each block, the program searches
    random candidate patches and picks the smoothest unmasked patch.
    This forces points to cover the whole image.
    """

    L = lab[:, :, 0]
    A = lab[:, :, 1]
    B = lab[:, :, 2]

    h, w = L.shape

    bare_points = []
    bare_values = []

    for y0 in range(0, h, block_size):
        for x0 in range(0, w, block_size):

            y1_block = y0
            y2_block = min(y0 + block_size, h)

            x1_block = x0
            x2_block = min(x0 + block_size, w)

            if y2_block - y1_block < 2 * patch_radius + 1:
                continue

            if x2_block - x1_block < 2 * patch_radius + 1:
                continue

            best_score = None
            best_point = None
            best_value = None

            for _ in range(candidates_per_block):

                x = np.random.randint(
                    x1_block + patch_radius,
                    x2_block - patch_radius,
                )

                y = np.random.randint(
                    y1_block + patch_radius,
                    y2_block - patch_radius,
                )

                if flake_mask[y, x]:
                    continue

                y1 = y - patch_radius
                y2 = y + patch_radius + 1

                x1 = x - patch_radius
                x2 = x + patch_radius + 1

                patch_mask = flake_mask[y1:y2, x1:x2]

                if np.mean(patch_mask) > 0:
                    continue

                L_patch = L[y1:y2, x1:x2]
                A_patch = A[y1:y2, x1:x2]
                B_patch = B[y1:y2, x1:x2]

                texture_L = np.std(L_patch)
                texture_A = np.std(A_patch)
                texture_B = np.std(B_patch)

                if texture_L > max_texture_allowed:
                    continue

                if texture_A > max_texture_allowed:
                    continue

                if texture_B > max_texture_allowed:
                    continue

                score = texture_L + texture_A + texture_B

                if best_score is None or score < best_score:
                    best_score = score
                    best_point = [x, y]
                    best_value = [
                        np.median(L_patch),
                        np.median(A_patch),
                        np.median(B_patch),
                    ]

            if best_point is not None:
                bare_points.append(best_point)
                bare_values.append(best_value)

    bare_points = np.asarray(bare_points)
    bare_values = np.asarray(bare_values)

    if len(bare_points) > max_bare_points:
        idx = np.random.choice(
            len(bare_points),
            max_bare_points,
            replace=False,
        )

        bare_points = bare_points[idx]
        bare_values = bare_values[idx]

    return bare_points, bare_values