"""Runs INSIDE Fusion. Renders module marketing images from a job file.

Executed via the Fusion MCP bridge:
    python3 "Fusion CAD Agent/bridge/fusion_mcp.py" --exec-file visual/fusion_render.py

Reads visual/render-job.json, fires one local ray-traced render per entry, and
writes visual/render-job-result.json. Renders are queued by Fusion and run one at
a time in a background process, so this script does NOT block waiting for them -
the host driver (render_module.py) polls for the output files.

API notes earned the hard way, 2026-08-26:
  - activeProduct/activeViewport are None with no document open.
  - inCanvasRendering raises until activateRenderWorkspace() has been called.
  - sceneSettings.backgroundType is read-only; assigning backgroundEnvironment is
    what selects the environment background (and gives a gradient backdrop).
  - groundRoughness refuses assignment unless isGroundReflections is true.
  - cameraExposure is EV-like: HIGHER is DARKER. The default is 9.5.
"""

import json
import os
import time
import traceback

# Substituted by render_module.py before this script is sent to Fusion. It has
# to be injected rather than derived: the bridge transmits this file's CONTENTS,
# not its path, so __file__ does not exist inside Fusion. The default keeps the
# script runnable by hand from the Fusion script editor.
JOB_PATH = "__BN_JOB_PATH__"
if JOB_PATH.startswith("__BN_"):
    JOB_PATH = os.path.join(os.path.expanduser("~"), "Claude", "Mac Mini Setup",
                            "tools", "cad-product-agent", "production",
                            "ten-modules", "visual", "render-job.json")
RESULT_PATH = JOB_PATH.replace("render-job.json", "render-job-result.json")
TRACE_PATH = JOB_PATH.replace("render-job.json", "render-trace.log")


def trace(message):
    """Append a step marker, flushed immediately.

    A script that wedges never returns, so its print() output is lost. Only a
    file written step by step shows WHERE it stopped, which is the difference
    between fixing the wedge and guessing at it.
    """
    try:
        with open(TRACE_PATH, "a") as handle:
            handle.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        pass

IN = 2.54  # Fusion API is always centimetres


def _document_count(app):
    try:
        return app.documents.count
    except Exception:
        return -1


_WARMED = {"done": False}


def _warm_render_stack(app, environment_name):
    """Load the render environment on an EMPTY document before importing anything.

    This is the fix for the wedge, and it took a step-trace to find. The trace
    stopped dead at "scene:start" on six consecutive attempts: import succeeded
    in ~11s, workspace activation in ~2s, and then _apply_scene hung forever.

    Assigning backgroundEnvironment makes the material-library service resolve
    the environment asset. Doing that for the first time while a freshly imported
    design with ~113 appearance-carrying components is open wedges Fusion
    permanently - the process stays alive at ~0% CPU and every later API call
    hangs. It is the same subsystem, adexmtsv, that crashed outright earlier.

    Doing it first on an empty design costs about a second and makes the same
    assignment on the heavy design instant. Measured 2026-08-26: cold-then-heavy
    wedged 6 times out of 6; empty-first then heavy completed every time.
    """
    import adsk.core, adsk.fusion
    if _WARMED["done"] or not environment_name:
        return
    trace("warm:start")
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    adsk.doEvents()
    design = adsk.fusion.Design.cast(app.activeProduct)
    rm = design.renderManager
    if not rm.isRenderWorkspaceActive:
        rm.activateRenderWorkspace()
        adsk.doEvents()
    env = rm.renderEnvironments.itemByName(environment_name)
    if env is not None:
        rm.sceneSettings.backgroundEnvironment = env
        adsk.doEvents()
    trace("warm:done")
    _WARMED["done"] = True


_OPEN = {"module": None}


def _open_module(app, module_id, exports_root):
    """Import a module only when it is not already the open one.

    Importing an F3D is by far the most fragile operation in this pipeline - it
    is what wedges Fusion, and a wedge is unrecoverable without a restart. So do
    it as rarely as possible: once per module, not once per render. All of a
    module's views are rendered from the single import, then the document is
    closed before the next module.

    The earlier version cached every module's document and never closed any,
    which crashed the material-library service. The version after that closed and
    re-imported for EVERY render, which doubled the number of imports and wedged
    on the first one. This is the middle: exactly one document open, exactly one
    import per module.
    """
    import adsk.core, adsk.fusion
    if _OPEN["module"] == module_id and _document_count(app) >= 1:
        return adsk.fusion.Design.cast(app.activeProduct)
    if False:
        # Do NOT call Document.close() here.
        #
        # close(False) on a document that has never been saved - which every
        # import in this pipeline is - puts up a modal save prompt, and a modal
        # dialog blocks every subsequent API call. Fusion stays alive at ~0% CPU
        # and hangs forever; only killing it recovers. Measured 2026-08-26:
        # import into an empty session takes 10s and always works, while import
        # into a session with a document open wedges permanently.
        #
        # Recycling the whole process between modules discards documents with no
        # dialog and no risk, so that is what the host driver does instead.
        raise RuntimeError(
            "a document is already open; this session is spent. Recycle Fusion "
            "rather than closing documents - close() prompts and wedges the API.")
    _OPEN["module"] = None
    trace("import:start %s" % module_id)
    path = os.path.join(exports_root, module_id, module_id + ".f3d")
    options = app.importManager.createFusionArchiveImportOptions(path)
    app.importManager.importToNewDocument(options)
    adsk.doEvents()
    _OPEN["module"] = module_id
    trace("import:done")
    return adsk.fusion.Design.cast(app.activeProduct)


def _apply_scene(rm, entry):
    scene = rm.sceneSettings
    import adsk.core
    env_name = entry.get("environment")
    if env_name:
        # Assign the environment ONLY when it is actually changing.
        #
        # Render environments are material-library assets, and adexmtsv - the
        # Autodesk material-library service - is what crashed first on
        # 2026-08-26, taking Fusion with it. Fusion's own crash reporter recorded
        # CrashCount 5 with DWGFile pointing at this pipeline's BN-M01.f3d.
        # Reassigning the same environment on every render churned that service
        # for no benefit: the scene is global and the value does not change
        # between modules.
        current = None
        trace("scene:read_bgtype")
        try:
            if int(scene.backgroundType) == 0:      # environment background
                trace("scene:read_bgenv")
                current = scene.backgroundEnvironment.name
        except Exception:
            current = None
        trace("scene:bgtype_ok current=%s" % current)
        if current != env_name:
            trace("scene:itemByName")
            env = rm.renderEnvironments.itemByName(env_name)
            trace("scene:itemByName_ok found=%s" % (env is not None))
            if env is None:
                raise RuntimeError("no render environment named %r" % env_name)
            # Assigning the environment is what flips the read-only backgroundType.
            trace("scene:assign_env")
            scene.backgroundEnvironment = env
            trace("scene:assign_env_ok")
    solid = entry.get("background_solid")
    if solid:
        # The light-rig environments (Soft Light, Sharp Highlights, Rim
        # Highlights, Grid Light) are studio RIGS: used as a visible background
        # they render their own softbox geometry into frame. They are meant to
        # light the subject against a solid backdrop instead. Assigning the solid
        # colour flips backgroundType the same way assigning an environment does.
        scene.backgroundSolidColor = adsk.core.Color.create(
            int(solid[0]), int(solid[1]), int(solid[2]), 255)
    trace("scene:ground")
    scene.isGroundDisplayed = bool(entry.get("ground", True))
    scene.isGroundReflections = bool(entry.get("ground_reflections", False))
    if scene.isGroundReflections and "ground_roughness" in entry:
        scene.groundRoughness = float(entry["ground_roughness"])
    # isGroundDisplayed alone renders no visible floor. Flattening the ground is
    # what puts a shadow-catching plane under the product; groundPosition only
    # accepts a value once isGroundFlattened is true.
    if "ground_flattened" in entry:
        scene.isGroundFlattened = bool(entry["ground_flattened"])
    if scene.isGroundFlattened and "ground_position" in entry:
        # groundPosition is a Point3D, not a scalar height, and the API is in
        # centimetres. The value in the job is the ground height in inches.
        scene.groundPosition = adsk.core.Point3D.create(
            0.0, 0.0, float(entry["ground_position"]) * IN)
    if "ground_offset" in entry:
        scene.groundOffset = float(entry["ground_offset"])
    trace("scene:brightness")
    if "brightness" in entry:
        scene.brightness = float(entry["brightness"])
    trace("scene:exposure")
    if "exposure" in entry:
        scene.cameraExposure = float(entry["exposure"])
    if "focal_length" in entry:
        scene.cameraFocalLength = float(entry["focal_length"])
    if "light_angle" in entry:
        scene.lightAngle = float(entry["light_angle"])
    if entry.get("depth_of_field"):
        scene.isDepthOfFieldEnabled = True
        scene.depthOfFieldBlur = float(entry.get("dof_blur", 0.5))
    else:
        scene.isDepthOfFieldEnabled = False
    return {
        "environment": env_name,
        "background_type": int(scene.backgroundType),
        "background_solid": solid,
        "ground": scene.isGroundDisplayed,
        "ground_flattened": scene.isGroundFlattened,
        "brightness": scene.brightness,
        "exposure": scene.cameraExposure,
        "focal_length": scene.cameraFocalLength,
        "light_angle": scene.lightAngle,
    }


VIEW_EYES = {
    # Multipliers on the 24 x 20 x 18 inch frame, matching the existing native
    # build so a marketing render is recognisably the same camera family.
    "hero": (1.75, -1.75, 1.65),
    "iso": (1.75, -1.75, 1.65),
    "front": (0.5, -3.5, 0.5),
    "detail": (1.05, -1.15, 1.05),
}


def _apply_camera(app, entry):
    """Frame the module by placing the eye at an explicit distance.

    Do NOT use camera.viewExtents to zoom: with isFitView on, Fusion recomputes
    the extents and the assignment is silently discarded (measured 2026-08-26 -
    extents_before and extents_after came back byte-identical while the requested
    zoom was 0.18). Turning isFitView off and setting the eye distance directly is
    the lever that actually moves.

    distance_factor is a multiple of the module's body diagonal (36.06 in for a
    24 x 20 x 18 frame). Smaller is closer, so the subject fills more of the frame.
    """
    import adsk.core, adsk.fusion
    import math
    width_in, depth_in, height_in = 24.0, 20.0, 18.0
    diagonal = math.sqrt(width_in ** 2 + depth_in ** 2 + height_in ** 2)
    view = entry.get("view", "hero")
    mx, my, mz = VIEW_EYES.get(view, VIEW_EYES["hero"])

    offset = entry.get("target_offset_in", [0.0, 0.0, 0.0])
    target = (width_in / 2.0 + float(offset[0]),
              depth_in / 2.0 + float(offset[1]),
              height_in / 2.0 + float(offset[2]))
    direction = (width_in * mx - target[0],
                 depth_in * my - target[1],
                 height_in * mz - target[2])
    length = math.sqrt(sum(component ** 2 for component in direction)) or 1.0
    unit = tuple(component / length for component in direction)

    factor = float(entry.get("distance_factor", 2.0))
    distance = diagonal * factor
    eye = tuple(target[i] + unit[i] * distance for i in range(3))

    viewport = app.activeViewport
    camera = viewport.camera
    camera.eye = adsk.core.Point3D.create(eye[0] * IN, eye[1] * IN, eye[2] * IN)
    camera.target = adsk.core.Point3D.create(target[0] * IN, target[1] * IN,
                                             target[2] * IN)
    camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
    camera.isSmoothTransition = False
    camera.isFitView = False
    camera.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
    viewport.camera = camera
    adsk.doEvents()
    viewport.refresh()
    adsk.doEvents()
    # Deliberately NOT calling viewport.fit(): with a ground plane enabled it
    # frames the effectively infinite ground and shoves the product off centre.
    entry["_camera_log"] = {"distance_factor": factor, "distance_in": distance,
                            "eye_in": eye, "target_offset_in": list(offset)}
    return viewport.camera


def _apply_output(rm, entry):
    import adsk.fusion
    rendering = rm.rendering
    rendering.aspectRatio = adsk.fusion.RenderAspectRatios.CustomRenderAspectRatio
    rendering.resolution = adsk.fusion.RenderResolutions.CustomRenderResolution
    rendering.resolutionWidth = int(entry.get("width", 2400))
    rendering.resolutionHeight = int(entry.get("height", 1800))
    rendering.isBackgroundTransparent = bool(entry.get("transparent", False))
    rendering.renderQuality = int(entry.get("quality", 75))
    return rendering


def run(_context: str):
    import adsk.core, adsk.fusion
    results = []
    try:
        job = json.load(open(JOB_PATH))
        app = adsk.core.Application.get()
        exports_root = job["exports_root"]
        out_dir = job["output_dir"]
        os.makedirs(out_dir, exist_ok=True)
        for entry in job["renders"]:
            record = {"name": entry["name"], "module": entry["module"],
                      "view": entry.get("view", "hero")}
            try:
                _warm_render_stack(app, entry.get("environment"))
                design = _open_module(app, entry["module"], exports_root)
                rm = design.renderManager
                # Only switch workspace when not already in it. Workspace
                # activation tears down and rebuilds UI and asset state; doing it
                # per render is the same needless churn as reassigning the
                # environment, on the same subsystem that crashed.
                trace("workspace:check")
                if not rm.isRenderWorkspaceActive:
                    trace("workspace:activate")
                    rm.activateRenderWorkspace()
                    adsk.doEvents()
                    trace("workspace:active")
                trace("scene:start")
                record["scene"] = _apply_scene(rm, entry)
                trace("scene:done")
                camera = _apply_camera(app, entry)
                trace("camera:done")
                rendering = _apply_output(rm, entry)
                target = os.path.join(out_dir, entry["name"] + ".png")
                if os.path.exists(target):
                    os.remove(target)
                trace("render:fire %s" % entry["name"])
                future = rendering.startLocalRender(target, camera)
                trace("render:fired")
                adsk.doEvents()
                record.update({
                    "target": target,
                    "started": True,
                    "state": int(future.renderState),
                    "width": rendering.resolutionWidth,
                    "height": rendering.resolutionHeight,
                    "quality": rendering.renderQuality,
                    "transparent": rendering.isBackgroundTransparent,
                    "camera": entry.get("_camera_log"),
                })
            except Exception:
                record.update({"started": False,
                               "error": traceback.format_exc()})
            results.append(record)
        payload = {"queued": sum(1 for r in results if r.get("started")),
                   "results": results}
    except Exception:
        payload = {"fatal": traceback.format_exc(), "results": results}
    with open(RESULT_PATH, "w") as handle:
        json.dump(payload, handle, indent=2)
    print("RENDER_JOB_DONE queued=%s" % payload.get("queued", 0))
