import ezdxf

# Constants for dimensions and offsets
W = 24.0  # Outside width
D = 20.0  # Outside depth
H = 18.0  # Outside height

# Offsets for views
FRONT_DX, FRONT_DY = 0.0, 0.0
TOP_DX, TOP_DY = 0.0, 30.0
RIGHT_DX, RIGHT_DY = 34.0, 0.0

# Helper function to place points with offsets
def place(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]

# Create a new DXF document
doc = ezdxf.new("R2010", setup=True)
msp = doc.modelspace()

# Set units to inches
doc.header["$INSUNITS"] = 1

# Add title block
msp.add_text("Modular Overland Camp System — Base Frame", height=2.0).set_placement((FRONT_DX + W / 2, FRONT_DY + H + 3))

# Add front view
front_posts = [(0, 0), (0, H - 1.0), (W - 1.0, H - 1.0), (W - 1.0, 0)]
front_members = [(2.5, 0), (2.5, H - 1.0), (W - 3.5, H - 1.0), (W - 3.5, 0)]
msp.add_lwpolyline(place(front_posts, FRONT_DX, FRONT_DY), close=True)
msp.add_lwpolyline(place([(x, 2.5) for x, y in front_members], FRONT_DX, FRONT_DY), close=True)
msp.add_lwpolyline(place([(x, H - 3.5) for x, y in front_members], FRONT_DX, FRONT_DY), close=True)
msp.add_text("front", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 1))

# Add top view
top_posts = [(0, 0), (D - 1.0, 0), (D - 1.0, H - 1.0), (0, H - 1.0)]
top_members = [(2.5, 0), (W - 1.0, 0), (W - 1.0, D - 1.0), (2.5, D - 1.0)]
msp.add_lwpolyline(place(top_posts, TOP_DX, TOP_DY), close=True)
msp.add_lwpolyline(place([(2.5, y) for x, y in top_members], TOP_DX, TOP_DY), close=True)
msp.add_lwpolyline(place([(W - 3.5, y) for x, y in top_members], TOP_DX, TOP_DY), close=True)
msp.add_text("top", height=0.75).set_placement((TOP_DX + D / 2, TOP_DY - 1))

# Add right view
right_posts = [(0, 0), (0, H - 1.0), (D - 1.0, H - 1.0), (D - 1.0, 0)]
right_members = [(2.5, 0), (2.5, H - 1.0), (W - 1.0, H - 1.0), (W - 1.0, 0)]
msp.add_lwpolyline(place(right_posts, RIGHT_DX, RIGHT_DY), close=True)
msp.add_lwpolyline(place([(x, 2.5) for x, y in right_members], RIGHT_DX, RIGHT_DY), close=True)
msp.add_lwpolyline(place([(x, H - 3.5) for x, y in right_members], RIGHT_DX, RIGHT_DY), close=True)
msp.add_text("right", height=0.75).set_placement((RIGHT_DX + D / 2, RIGHT_DY - 1))

# Draw the extrusion members
front_posts = [(0, 0), (0, H - 1.0), (W - 1.0, H - 1.0), (W - 1.0, 0)]
front_members = [(2.5, 0), (W - 3.5, H - 1.0)]
top_posts = [(0, 0), (D - 1.0, 0), (D - 1.0, H - 1.0), (0, H - 1.0)]
top_members = [(2.5, 0), (W - 1.0, D - 1.0)]
right_posts = [(0, 0), (D - 1.0, H - 1.0), (D - 1.0, 0)]
right_members = [(2.5, 0), (W - 1.0, H - 1.0)]

msp.add_lwpolyline(place(front_posts, FRONT_DX, FRONT_DY), close=True)
msp.add_lwpolyline(place([(x, 2.5) for x, y in front_members], FRONT_DX, FRONT_DY), close=True)
msp.add_lwpolyline(place([(x, H - 3.5) for x, y in front_members], FRONT_DX, FRONT_DY), close=True)

msp.add_lwpolyline(place(top_posts, TOP_DX, TOP_DY), close=True)
msp.add_lwpolyline(place([(2.5, y) for x, y in top_members], TOP_DX, TOP_DY), close=True)
msp.add_lwpolyline(place([(W - 3.5, y) for x, y in top_members], TOP_DX, TOP_DY), close=True)

msp.add_lwpolyline(place(right_posts, RIGHT_DX, RIGHT_DY), close=True)
msp.add_lwpolyline(place([(x, 2.5) for x, y in right_members], RIGHT_DX, RIGHT_DY), close=True)
msp.add_lwpolyline(place([(x, H - 3.5) for x, y in right_members], RIGHT_DX, RIGHT_DY), close=True)

# Cut list
msp.add_text("Cut List", height=1.0).set_placement((FRONT_DX + W / 2, FRONT_DY - 5))
msp.add_text("4x Posts @ 18.0\"", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 8))
msp.add_text("4x Width Members @ 22.0\"", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 10))
msp.add_text("4x Depth Members @ 20.0\"", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 12))

# Save the DXF file
OUTPUT_PATH = '/Users/cmken/Claude/Fusion CAD Agent/exports/overland-base-frame.dxf'
doc.saveas(OUTPUT_PATH)