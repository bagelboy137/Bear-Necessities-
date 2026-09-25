# 02 — Frame assembly guide

Assembles the bare 24 × 20 × 18 in frame from the parts in
`01-frame-cut-list-and-bom.md`.

> **Not build-verified.** No one has assembled this frame yet. This sequence is
> derived from the CAD geometry and standard 80/20-style extrusion practice, not
> from a build. Expect to discover bracket-access and T-nut-fit details the CAD
> did not show. If you find the sequence wants changing, it probably does —
> please tell Bear Necessities.
>
> **Torque is not specified.** Follow 80/20's published torque specification for
> the `3393` fastener (request from the vendor). Do not guess a value.

---

## Before you start

**You have:**

- 8 × profile cut to 18 in, 4 × profile cut to 22 in (12 pieces).
- 24 × `4132` gusseted corner brackets.
- 48 × `3393` bolt + T-nut assemblies.

**You need (not supplied):**

- Hex/Allen key or driver bit matching the `3393` bolt head.
- A torque wrench/driver capable of 80/20's specified value.
- A machinist's square or framing square.
- A rubber mallet.
- A flat, level assembly surface at least 30 × 30 in.
- Calipers or a tape measure you trust to 1/32 in.

**Read 80/20's own assembly instructions for the `4132` bracket and `3393`
fastener first.** They cover slide-in vs. drop-in T-nut orientation, thread
engagement, and the correct torque — none of which this pack invents.

---

## Naming

| Name | Length | Qty | Position |
|---|---|---:|---|
| Post | 18 in | 4 | The 4 vertical corners |
| Depth rail | 18 in | 4 | Front-to-back, 2 at the top, 2 at the bottom |
| Width rail | 22 in | 4 | Left-to-right, 2 at the top, 2 at the bottom |

The **outside** dimensions are 24 (width) × 20 (depth) × 18 (height). The width
rails and depth rails butt into the faces of the posts, so a post sits "inside"
the ends of the top and bottom rectangles.

---

## Step 1 — Build the bottom rectangle

1. Lay 2 width rails (22 in) and 2 depth rails (18 in) on the flat surface in a
   rectangle: width rails front and back, depth rails left and right, forming a
   24 × 20 in outside footprint.
2. At each of the 4 corners, the end of a depth rail butts against the inside
   face of a width rail (or vice versa — pick one convention and keep it on all
   four corners and both rectangles).
3. Slide a `3393` T-nut into the slot of each member at each joint, position one
   `4132` bracket spanning the corner on the **inside** face, and start both
   bolts by hand. One bracket per corner at this stage.
4. Square the rectangle: measure both diagonals, adjust until they are equal,
   then snug all 8 bolts. Re-check the diagonals. Torque to spec.
5. Result: a flat 24 × 20 in rectangle, 8 bolts, 4 brackets used.

## Step 2 — Stand the four posts

1. Stand a post vertically at each corner of the bottom rectangle, on the
   outside of the rail ends so the post's outside faces are flush with the
   24 × 20 in footprint.
2. At each corner the post now meets **two** bottom rails (one width, one depth).
   Add one `4132` bracket between the post and each of those two rails — 2
   brackets per corner.
3. T-nuts in, bolts started by hand, then check each post for plumb with the
   square against two adjacent faces before torquing. Torque all bolts.
4. Brackets used so far: 4 (bottom rectangle corners) + 8 (post-to-bottom-rail,
   2 per corner) = 12.

## Step 3 — Build the top rectangle in place

1. Lay the 2 remaining width rails and 2 remaining depth rails across the tops of
   the posts in the same rectangle pattern as the bottom.
2. At each corner: one `4132` bracket between the two top rails (the top-rectangle
   corner joint), and one bracket between the post top and **one** of the two top
   rails. That is 2 brackets per corner.

   > This gives 3 brackets total per top corner (rail-to-rail, post-to-rail ×1)
   > and matches the 24-bracket total: 8 corners × 3 = 24. The bottom corners get
   > their 3rd bracket from Step 1; the top corners get theirs here. If your
   > bracket access says to distribute them differently, do — the count is 3 per
   > corner, the exact placement is not a released detail.

3. T-nuts, hand-start, square the top rectangle by diagonal, check the whole
   frame stands square (measure the two diagonals on all four vertical faces),
   then torque everything.

## Step 4 — Final check

- All 24 brackets installed, all 48 bolts torqued to 80/20's spec.
- Outside dimensions: 24 × 20 in footprint, 18 in tall, within your build
  tolerance. (The CAD target is 24 × 20 × 18 in; the concept models hold
  ±0.002 in, a physical frame will not — decide your own acceptance band, the
  project's physical test plan calls for measuring "both diagonals on all six
  faces" and leaves the tolerance blank pending a drawing.)
- Every vertical face square (equal diagonals).
- No bracket slipping in a slot when you push on the frame by hand.
- Re-check torque after the first day and after the first drive — the project's
  test plan explicitly calls for a torque-retention re-check, and vibration
  loosening of the joint is one of the open engineering questions.

---

## What comes after the frame

The bare frame is the end of this pack's step-by-step content. To go further you
need material this pack does not fully provide:

- **Panels / skins** — cut-to-size sheet, but the panel drawings don't exist yet
  (`00-status-and-limitations.md` §3d).
- **Handles, feet, gasket, anti-skid tread** — off-the-shelf, listed in
  `05-off-the-shelf-parts-catalog.md`, but load ratings for the handles are
  untested.
- **The module interior** — see `04-module-concepts.md` for the ten concepts and
  what each still needs.
- **Vehicle mounting** — **not in this pack.** `00-status-and-limitations.md`
  §3a. Until Bear Necessities publishes a measured C-02 bracket, restrain the
  module with rated cargo straps to the vehicle's own anchor points and treat it
  as cargo, not as a fixed install.
