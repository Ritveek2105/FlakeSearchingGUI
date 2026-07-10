
macro_dir = File.getParent(getInfo("macro.filepath"));
project_dir = File.getParent(File.getParent(macro_dir));

input_dir = project_dir + "/data/corrected_tiles/";
output_dir = project_dir + "/data/stitched_images/";

run("Grid/Collection stitching",
    "type=[Grid: row-by-row] "
    + "order=[Snake by rows] "
    + "grid_size_x=6 "
    + "grid_size_y=4 "
    + "tile_overlap=40 "
    + "first_file_index_i=1 "
    + "directory=[" + input_dir + "] "
    + "file_names={i}_graphene_corrected.tif "
    + "output_textfile_name=TileConfiguration.txt "
    + "fusion_method=[Linear Blending] "
    + "regression_threshold=0.30 "
    + "max/avg_displacement_threshold=2.50 "
    + "absolute_displacement_threshold=3.50 "
    + "compute_overlap "
    + "subpixel_accuracy "
    + "computation_parameters=[Save memory (but be slower)] "
    + "image_output=[Fuse and display]");

saveAs("Tiff", output_dir + "Fused.tif");
close("*");
