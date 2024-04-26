#!/usr/bin/env python3

# Import necessary libraries
from heapq import heappush, heappop, heapify
import sys
import numpy as np
import imageio.v2 as imageio
import matplotlib.pyplot as plt

# Constants for Mars surface
mars_average_surface_depth_km = 0.5  # in kilometers

# Calculate sea level based on average surface depth
sea_level = -mars_average_surface_depth_km

# Input and output file paths
file_input = "PIA00005.tif"  # Input image file path
file_output = "rivers000010.tif"  # Output image file path

# Optional parameters for river mapping
seed = None  # Random seed for reproducibility
contrast = 5  # Contrast parameter for river map generation
bit_depth = 20  # Bit depth of the output image
draw_linewidth = False  # Flag to draw river lines with width
river_limit = 0  # Limit for river detection

# Set random seed if provided
if seed:
    np.random.seed(seed=seed)

# Set recursion limit to avoid stack overflow
sys.setrecursionlimit(65536)

# Read the input image
print("Reading image")
input_image = imageio.imread(file_input)

# Convert to grayscale if image is color
if len(input_image.shape) == 3 and input_image.shape[2] == 3:
    input_image = np.dot(input_image[...,:3], [0.2989, 0.5870, 0.1140])

# Get the heightmap from the input image
heightmap = np.array(input_image)
(X, Y) = heightmap.shape

# Print information about the input image
print("Input image dimensions:", X, "x", Y)
print("Input image loaded successfully")

# Find start points for river mapping
print("Finding start points")

# Initialize visited array to keep track of visited pixels
visited = np.zeros((X, Y), dtype=bool)

# List to store start points for river mapping
start_points = []

# Function to add a start point to the list
def add_start_point(x, y):
    start_points.append((heightmap[x, y] + np.random.random(), x, y))
    visited[x, y] = True

# Counter for number of points to explore
to_explore = 0

# Iterate through each pixel to find start points
for x in range(1, X-1):
    for y in range(1, Y-1):
        # Check if the pixel is below sea level
        if heightmap[x, y] <= sea_level:
            continue
        to_explore += 1
        if to_explore % 1000000 == 0:
            print("Found", str(to_explore // 1000000), "millions points to explore")
        # Check if the pixel has a neighboring pixel below sea level
        if (heightmap[x-1, y] <= sea_level or heightmap[x+1, y] <= sea_level or heightmap[x, y-1] <= sea_level or heightmap[x, y+1] <= sea_level):
            add_start_point(x, y)

# Check pixels on the edges of the image
for x in range(X):
    if heightmap[x, 0] > sea_level:
        add_start_point(x, 0)
        to_explore += 1
    if heightmap[x, -1] > sea_level:
        add_start_point(x, Y-1)
        to_explore += 1

for y in range(1, Y-1):
    if heightmap[0, y] > sea_level:
        add_start_point(0, y)
        to_explore += 1
    if heightmap[-1, y] > sea_level:
        add_start_point(X-1, y)
        to_explore += 1

# Print information about the start points
print("Found", str(len(start_points)), "start points for river mapping")

# Create a heap from the start points list
heap = start_points[:]
heapify(heap)

# Print information about river tree construction
print("Building river trees:", str(to_explore), "points to visit")

# Array to store flow directions
flow_dirs = np.zeros((X, Y), dtype=np.int8)

# Function to try pushing a pixel to the heap
def try_push(x, y):
    if not visited[x, y]:
        h = heightmap[x, y]
        if h > sea_level:
            heappush(heap, (h + np.random.random(), x, y))
            visited[x, y] = True
            return True
    return False

# Function to process neighboring pixels
def process_neighbors(x, y):
    dirs = 0
    if x > 0 and try_push(x-1, y):
        dirs+= 1
    if y > 0 and try_push(x, y-1):
        dirs += 2
    if x < X-1 and try_push(x+1, y):
        dirs += 4
    if y < Y-1 and try_push(x, y+1):
        dirs += 8
    flow_dirs[x, y] = dirs

# Iterate until the heap is empty
while len(heap) > 0:
    t = heappop(heap)
    to_explore -= 1
    if to_explore % 1000000 == 0:
        print(str(to_explore // 1000000), "million points left", "Altitude:", int(t[0]), "Queue:", len(heap))
    process_neighbors(t[1], t[2])

# Cleanup visited and heightmap arrays
visited = None
heightmap = None

# Print information about water quantity calculation
print("Calculating water quantity")

# Array to store water quantity
waterq = np.ones((X, Y))

# Function to recursively set water quantity for each pixel
def set_water(x, y):
    water = 1
    dirs = flow_dirs[x, y]

    if dirs % 2 == 1:
        water += set_water(x-1, y)
    dirs //= 2
    if dirs % 2 == 1:
        water += set_water(x, y-1)
    dirs //= 2
    if dirs % 2 == 1:
        water += set_water(x+1, y)
    dirs //= 2
    if dirs % 2 == 1:
        water += set_water(x, y+1)
    waterq[x, y] = water
    return water

# Find the maximal water quantity
maxwater = 0
for start in start_points:
    water = set_water(start[1], start[2])
    if water > maxwater:
        maxwater = water

# Print information about maximal water quantity
print("Maximal water quantity:", str(maxwater))

# Cleanup flow_dirs array
flow_dirs = None

# Print information about image generation
print("Generating image")

# Calculate power for water quantity transformation
power = 1 / contrast

# Generate river map based on the specified parameters
if draw_linewidth:
    bit_depth = 1
    river_array = np.zeros((X, Y), dtype=bool)

    for x in range(X):
        for y in range(Y):
            q = waterq[x,y]
            if q >= river_limit:
                rsize = int((q / river_limit)**power)
                if rsize > 1:
                    rsize -= 1
                    xmin = max(x-rsize, 0)
                    xmax = min(x+rsize+1, X)
                    ymin = max(y-rsize, 0)
                    ymax = min(y+rsize+1,Y)
                    river_array[xmin:xmax,y] = True
                    river_array[x,ymin:ymax] = True
                else:
                    river_array[x,y] = True
    data = np.uint8(river_array * 255)

else:
    if bit_depth <= 8:
        bit_depth = 8
        dtype = np.uint8
    elif bit_depth <= 16:
        bit_depth = 16
        dtype = np.uint16
    elif bit_depth <= 32:
        bit_depth = 32
        dtype = np.uint32
    else:
        bit_depth = 64
        dtype = np.uint64

    maxvalue = 2 ** bit_depth - 1
    coeff = maxvalue / (maxwater ** power)

    data = np.floor((waterq ** power) * coeff).astype(dtype)

# Cleanup waterq array
waterq = None

# Save the generated image to the output file
imageio.imwrite(file_output, data)

# Print information about the output image
print("Output image saved to:", file_output)

# Display the input and output images
fig, axes = plt.subplots(1, 2, figsize=(12, 6))

# Input image
axes[0].imshow(input_image, cmap='gray')
axes[0].set_title('Input Image')
axes[0].axis('off')

# Output image
axes[1].imshow(data, cmap='gray')
axes[1].set_title('Generated River Map')
axes[1].axis('off')

# Adjust layout to fit images
plt.tight_layout()

# Show the images
plt.show()
