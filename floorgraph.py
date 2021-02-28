#!/usr/bin/env python3
import numpy as np
import cv2 as cv

def boundary_points(component):
	"get coordinates of all pixels that are on the edge of the component"
	# this is a kind of simple findContours
	# can probably be replaced by findContours

	shrunk = cv.erode(component.astype(np.uint8), None)
	boundary = component & ~shrunk
	(i, j) = np.nonzero(boundary)
	return np.array([i, j]).T

def on_mouse_lookup(event, x, y, flags, param):
	if flags & cv.EVENT_FLAG_LBUTTON:
		label = labels[y,x]
		adj = graph.get(label, None)
		print(f"label {label} at {x}x{y} <-> {adj}   ", end="\r", flush=True)

def draw_map(title="map"):
	canvas = np.zeros((height, width, 3), np.float32)

	overlays = [] # (index, cx, cy)

	# draw components
	for label in range(1, numlabels+1):
		mask = (labels == label)

		# 0 = blank, then corridor labels, then room labels
		color = np.array([1.0, 0.5, 0.0]) if label <= numcorridors else np.array([0.0, 0.5, 1.0])
		canvas[mask] = color * label / numlabels

		# calculate centroid from moments
		m = cv.moments(mask.astype(np.uint8))
		if m['m00'] > 0: # component has any pixels at all
			cx = int(m['m10'] / m['m00'])
			cy = int(m['m01'] / m['m00'])
			overlays.append((label, cx, cy))

	# draw text labels
	for label, cx, cy in overlays:
		text = f"{label}"
		(sx, sy), baseline = cv.getTextSize(text, cv.FONT_HERSHEY_SIMPLEX, 1.0, 2)
		cv.putText(canvas, text, (cx - sx//2, cy + sy//2), cv.FONT_HERSHEY_SIMPLEX, 1.0, (1,1,1), 2)

	# show
	cv.namedWindow(title, cv.WINDOW_AUTOSIZE)
	cv.setMouseCallback(title, on_mouse_lookup)
	cv.imshow(title, canvas ** (1/2.2))


floorplan = cv.imread("a9a53dde0cb2016ee9c4c182c842a5fff3dd1321-input.png", cv.IMREAD_GRAYSCALE)
(height, width) = floorplan.shape[:2]

# some of those walls aren't aligned right. kernel shape and iterations are fudge factors
kernel = cv.getStructuringElement(cv.MORPH_RECT, (7,9))
room = cv.morphologyEx(floorplan, cv.MORPH_OPEN, kernel=kernel, iterations=12)
# use an ellipse in the general case. result is less pretty but more robust

# masks
floorplan = (floorplan > 0)
room = (room > 0)
corridor = floorplan & ~room

# number contains 0 (background), labels are 0..N-1, with 1..N-1 being object
numcorridors, corridor_labels = cv.connectedComponents(corridor.astype(np.uint8))
numcorridors -= 1
numrooms, room_labels = cv.connectedComponents(room.astype(np.uint8))
numrooms -= 1

# 0 = background, then corridors, then rooms
numlabels = numcorridors + numrooms

# combined label map
labels = np.zeros((height, width), np.uint16)
labels[corridor] = corridor_labels[corridor]
labels[room] = numcorridors + room_labels[room]

print("building graph")
graph = {} # label -> {adjacent labels}

for L in range(1, numlabels+1):
	boundary = boundary_points(labels == L)
	# take neighborhood
	adjacents = np.concatenate([ labels[i-1:i+2, j-1:j+2].flat for i,j in boundary ])
	adjacents = set(adjacents) - {0, L}
	graph[L] = adjacents
	print(f"  {L} -> {adjacents}")

print("done")

draw_map("map 1")
cv.waitKey()
print()

print("relabeling dead-end corridors")
for L in range(1, numcorridors+1):
	adj = graph[L]
	if len(adj) == 1:
		(R,) = adj
		print(f"  corridor {L} := room {R}")
		labels[labels == L] = R

print("done")

draw_map("map 2")
cv.waitKey()
print()
cv.destroyAllWindows()
