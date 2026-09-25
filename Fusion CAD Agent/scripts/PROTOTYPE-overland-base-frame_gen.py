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
front_posts = [(0, 0), (0, H), (W, H), (W, 0)]
front_members = [(2, 0), (2, H), (W - 2, H), (W - 2, 0)]
msp.add_lwpolyline(place(front_posts, FRONT_DX, FRONT_DY), close=True)
msp.add_lwpolyline(place(front_members, FRONT_DX, FRONT_DY), close=True)
msp.add_text("front", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 1))

# Add top view
top_posts = [(0, 0), (D, 0), (D, H), (0, H)]
top_members = [(0, 2), (W, 2), (W, D - 2), (0, D - 2)]
msp.add_lwpolyline(place(top_posts, TOP_DX, TOP_DY), close=True)
msp.add_lwpolyline(place(top_members, TOP_DX, TOP_DY), close=True)
msp.add_text("top", height=0.75).set_placement((TOP_DX + W / 2, TOP_DY - 1))

# Add right view
right_posts = [(0, 0), (0, H), (D, H), (D, 0)]
right_members = [(2, 0), (2, H), (W - 2, H), (W - 2, 0)]
msp.add_lwpolyline(place(right_posts, RIGHT_DX, RIGHT_DY), close=True)
msp.add_lwpolyline(place(right_members, RIGHT_DX, RIGHT_DY), close=True)
msp.add_text("right", height=0.75).set_placement((RIGHT_DX + D / 2, RIGHT_DY - 1))

# Draw the extrusion members in each view
# Front view: 2 vertical posts and 2 horizontal members
front_posts = [(0, 0), (0, H), (W, H), (W, 0)]
front_members = [(2, 0), (2, H), (W - 2, H), (W - 2, 0)]
msp.add_lwpolyline(place(front_posts, FRONT_DX, FRONT_DY), close=True)
msp.add_lwpolyline(place(front_members, FRONT_DX, FRONT_DY), close=True)

# Top view: 2 vertical posts and 2 horizontal members
top_posts = [(0, 0), (D, 0), (D, H), (0, H)]
top_members = [(0, 2), (W, 2), (W, D - 2), (0, D - 2)]
msp.add_lwpolyline(place(top_posts, TOP_DX, TOP_DY), close=True)
msp.add_lwpolyline(place(top_members, TOP_DX, TOP_DY), close=True)

# Right view: 2 vertical posts and 2 horizontal members
right_posts = [(0, 0), (0, H), (D, H), (D, 0)]
right_members = [(2, 0), (2, H), (W - 2, H), (W - 2, 0)]
msp.add_lwpolyline(place(right_posts, RIGHT_DX, RIGHT_DY), close=True)
msp.add_lwpolyline(place(right_members, RIGHT_DX, RIGHT_DY), close=True)

# Cut list
msp.add_text("Cut List", height=1.0).set_placement((FRONT_DX + W / 2, FRONT_DY - 5))
msp.add_text("4x Posts @ 18.0\"", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 8))
msp.add_text("4x Width Members @ 22.0\"", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 10))
msp.add_text("4x Depth Members @ 18.0\"", height=0.75).set_placement((FRONT_DX + W / 2, FRONT_DY - 12))

# Save the DXF file
OUTPUT_PATH = '/Users/cmken/Claude/Fusion CAD Agent/exports/overland-base-frame.dxf'
doc.saveas(OUTPUT_PATH)