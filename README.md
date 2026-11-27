# Background-Oriented Schlieren with an IDS uEye Camera

Image Processing 2 bachelor project: visualize warm-air refractive effects by
comparing a dot-pattern reference image with a measurement image. The software
estimates apparent pattern displacements in pixels. It does not directly measure
temperature, density, or air velocity.

## Verified setup and status

Real image pairs and approximately 10-second sequences were captured on
27 November 2026. The latest experiment settings were:

| Item | Setting |
|---|---|
| Camera | IDS uEye, displayed as UI325xCP-M; monochrome camera, saved as RGB8 |
| Native image size | 1600 x 1200 pixels; queried from the camera |
| Aperture | f/4, set manually on the lens |
| Exposure | 5 ms requested; approximately 4.999656 ms reported by the driver |
| Master gain | 0 |
| Focus | On the dot pattern; focus-ring marking approximately 0.4 m |
| Camera-to-pattern distance | 47 cm, reported by the operator |
| Printed dot diameter | 0.80 mm, reported by the operator |
| Illumination | Rear LED panel, with an additional sheet of paper |
| Orientation | Camera mounted sideways; rotate images 90 degrees clockwise |
| Sequence target | 10 seconds at 5 fps; measured approximately 5.01 fps |
| Analysis | 40-pixel window, 20-pixel grid step, 4-pixel search radius |

The camera-to-heat-source and heat-source-to-pattern distances were not measured
and confirmed in the session. An initial 23 cm / 24 cm split was suggested, not
verified. Lens focal length, room temperature, and heat-source temperatures were
not recorded. A high valid-vector percentage indicates accepted correlations;
it does not establish that every displacement is caused by warm air.

The experiment report, including local timestamps, settings, results, and
limitations, is [reports/experiment_report_2026-11-27.txt](reports/experiment_report_2026-11-27.txt).
The folder `static_f8_5ms_01` was actually captured at f/4, as confirmed by the
operator. Its historical name was retained.

## Project files

```text
configs/base.yaml                RGB8 shape for the I/O check only
scripts/capture.py               Capture a cold/static or cold/heated image pair
scripts/rotate_pair.py           Create lossless 90-degree clockwise pair copies
scripts/analyze.py               Analyze a saved reference/measurement pair
scripts/bos_video.py             Record lossless sequences and export BOS videos
scripts/visualize.py             Plot reference, measurement, and intensity difference
scripts/visualize_correaltion.py  Plot correlation regions, NCC, and subpixel fitting
scripts/visualoze_vectors.py     Plot an existing field over its reference image
scripts/visualize_vectors.py     Plot reference, measurement, and displacement arrows
scripts/visualize_quality.py     Plot correlation quality and vector validity
scripts/validate.py              Validate estimates against known synthetic shifts
scripts/check_io.py              Verify TIFF/JSON round trips
scripts/check_correlation.py     Inspect one known synthetic shift
scripts/check_synthetic.py       Display a synthetic image pair
src/bos/                         I/O, correlation, simulation, and metrics
reports/                         Experiment reports
```

The filenames `visualize_correaltion.py` and `visualoze_vectors.py` retain their
historical spelling for compatibility. All comments, prompts, errors, plot labels,
and documentation are in English. Historical images and acquisition logs remain
records of the original experiments.

## Environment

Run commands from the project root. Activate the existing environment:

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
```

For a fresh environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy scipy Pillow PyYAML matplotlib
export PYTHONPATH="$PWD/src"
```

For camera acquisition, also install `pyueye` and the matching native IDS uEye
Software Suite/driver. The Python package alone is insufficient:

```bash
python -m pip install pyueye
```

MP4 export requires `ffmpeg` with the `libx264` encoder:

```bash
ffmpeg -version
ffmpeg -hide_banner -encoders
```

For headless plotting, if needed:

```bash
export MPLBACKEND=Agg
export MPLCONFIGDIR=/tmp/bos-matplotlib
```

There is no dependency lockfile. The experiment report lists the installed
versions observed during the documentation audit.

## Prepare the physical setup

```text
Camera -> warm-air measurement region -> dot pattern -> LED backlight
```

Secure the camera and pattern. Focus on the pattern in uEye Demo, then close Demo
before running capture commands. Keep aperture, focus, illumination, and geometry
unchanged within a measurement. The scripts have no live preview and do not
control the heat source. Automatic exposure and gain are disabled; RGB8 is used.
Unsupported automatic white balance is reported without stopping acquisition.
Other image-processing settings, such as gamma and gain boost, are not explicitly
configured by the scripts. In the supplied Demo screenshots both were disabled.

For a candle, keep its rising warm air in front of the patterned region. For a
hairdryer, hold or mount it steadily and avoid blowing directly onto the paper.
Let residual warm air dissipate before a new cold reference. Pattern motion,
camera motion, and reflections can also produce apparent displacements.

## Capture and analyze an image pair

Choose a new output name for every acquisition. Existing output folders are
rejected.

### Static control: both images without heating

```bash
python scripts/capture.py data/raw/static_new_01 --exposure-ms 5 --gain 0
```

Press Enter for the cold reference, keep everything still, then press Enter for
the second cold frame. This checks the baseline displacement and valid-vector
coverage. Inspect local maps as well as the median.

### Cold reference followed by a heated image

```bash
python scripts/capture.py data/raw/heated_new_01 --exposure-ms 5 --gain 0 --heated
```

1. Keep the heat source off and press Enter for the reference.
2. Turn on the source without moving the setup.
3. For the candle trials, approximately 30 seconds was the suggested wait.
   Keep the actual wait consistent and record it. Hairdryer trials used a short
   wait of a few seconds after switching on.
4. Withdraw your hand and press Enter for the measurement.

Both images are saved after the second capture. Do not exit after the first
Enter if you want to retain the pair. `--heated` changes the prompt and test label;
it does not switch the source on.

### Correct the sideways camera orientation

Rotate both images before analysis, preserving the originals:

```bash
python scripts/rotate_pair.py data/raw/heated_new_01 data/raw/heated_new_01_cw90
PAIR="data/raw/heated_new_01_cw90"
python scripts/analyze.py "$PAIR/reference" "$PAIR/moving" --window 40
```

For an upright camera, skip rotation and set `PAIR` to the original folder.
Rotated copies are uncompressed TIFFs with updated shape metadata. Imported TIFF
pairs without JSON can be rotated; their unknown capture timestamps remain
`null`. Standard analysis requires matching `frame.tif` and `frame.json` files.

`analyze.py` prints a new path such as
`data/processed/bos_pair_<generated_id>/field.npz`. Use that exact field with the
corresponding reference:

```bash
FIELD="data/processed/bos_pair_REPLACE_WITH_GENERATED_ID/field.npz"
OUT="results/heated_new_01"
mkdir -p "$OUT"
```

Replace the field-path placeholder with the actual output. Window sizes are
32, 40, or 52 pixels; grid spacing is half the window size.

## Export Python plots

These commands use the `PAIR`, `FIELD`, and `OUT` values above. The destination
folder must exist; PNGs are never overwritten. Omit `--output` or `--output-dir`
for interactive display in a graphical session.

### Reference, measurement, and signed intensity difference

```bash
python scripts/visualize.py "$PAIR/reference" "$PAIR/moving" --output "$OUT/01_intensity_difference.png"
```

The difference is `measurement - reference` intensity, not displacement.

### Correlation window and normalized cross-correlation (NCC)

```bash
python scripts/visualize_correaltion.py "$PAIR/reference" "$PAIR/moving" --window 40 --output-dir "$OUT"
```

Creates `02_correlation_window.png` and `03_ncc_map.png`. Add `--cell ROW COL`
to select a zero-based grid cell; otherwise the central grid cell is selected.

```bash
python scripts/visualize_correaltion.py "$PAIR/reference" "$PAIR/moving" --window 40 --subpixel --output-dir "$OUT"
```

Creates `04_subpixel_interpolation.png` with the NCC samples and, where accepted,
a parabolic subpixel fit.

### Arrows over the reference using a saved field

```bash
python scripts/visualoze_vectors.py "$PAIR/reference" "$FIELD" --arrow-scale 40 --stride 3 --output "$OUT/05_vector_field.png"
```

`--arrow-scale 40` enlarges displayed arrow lengths by a factor of 40. `--stride 3`
shows every third grid row and column. The `1 px` key uses the same arrow scale.
Neither option changes measured values; invalid vectors are omitted.

### Reference, measurement, and magnitude map with arrows

```bash
python scripts/visualize_vectors.py "$PAIR/reference" "$PAIR/moving" --arrow-scale 40 --stride 3 --limit-px 2 --output "$OUT/06_pair_and_vectors.png"
```

This script recomputes a field for the supplied images. Blue shading shows total
displacement magnitude, not a radial component. For original sideways images,
add `--rotate-cw 90`. Do not rotate already corrected images again.

A frame from the latest recorded hairdryer sequence can be inspected directly:

```bash
python scripts/visualize_vectors.py data/raw/video_hairdryer_04/reference data/raw/video_hairdryer_04/frames/000025 --rotate-cw 90 --arrow-scale 40 --stride 3 --limit-px 2
```

### Correlation quality and validity

```bash
python scripts/visualize_quality.py "$FIELD" --output "$OUT/07_quality.png"
```

Shows the NCC maximum, separation from the next distinct peak, and accepted or
rejected grid cells. The older plot tools export at 300 dpi; the three-panel
`visualize_vectors.py` tool exports at 200 dpi.

## Record a 10-second BOS video

Recording and processing are separate steps. Capture stores uncompressed TIFFs;
correlation runs offline and can take longer than the recording itself.

Use new names for both raw and result folders:

```bash
python scripts/bos_video.py record data/raw/video_new_01 --seconds 10 --fps 5 --exposure-ms 5 --gain 0
```

1. With the source off and the scene cooled, press Enter for the reference.
2. Switch on the heat source without disturbing the setup.
3. Once the desired warm-air flow is established, press Enter to start recording.
4. Keep the setup fixed until the script finishes.

The 27 November setup achieved approximately 5 fps. An initial 10 fps target
produced 51 measurements in 10 seconds at 5.11 fps. Subsequent 5 fps targets
produced 50 measurements at approximately 5.01 fps. Capture, transfer, storage,
and the time-slot scheduling all affect the attainable rate; it is not a hardware
frame-rate guarantee. A low-frame-rate warning does not invalidate saved images.

At 1600 x 1200 RGB8, each raw image uses approximately 5.76 MB: about 288 MB for
50 frames, plus the reference, metadata, processed fields, and MP4.

### Process and rotate the sequence

```bash
python scripts/bos_video.py process data/raw/video_new_01 results/video_new_01 --rotate-cw 90 --window 40 --component u --limit-px 2 --fps 5
```

Output: `results/video_new_01/bos.mp4`.

| Option | Meaning |
|---|---|
| `--rotate-cw 90` | Rotate the reference and all images clockwise before analysis and display |
| `--window 40` | Correlation-window size; step is 20 pixels |
| `--component u` | Horizontal displacement; `v` selects vertical displacement |
| `--limit-px 2` | Fixed display scale from -2 to +2 pixels |
| `--fps 5` | Export frame rate, independent of the acquisition target |

The left panel displays the corrected raw image; the right displays the BOS field
in grayscale. Every frame is compared with the same cold reference, not with the
preceding heated frame. No global-motion correction is applied. Values beyond
the display limit saturate only in the visualization; NPZ values are preserved.

Playback follows recorded relative timestamps, holding each measurement until
the next one. Before the first sample, the first image is displayed. Export length
is rounded up to a whole output frame: a measured duration just above 10 seconds
can become a 10.2-second MP4 at 5 fps. Increasing export fps adds no measurements
or interpolated flow. MP4 compression affects only the presentation video.

## Data and coordinate conventions

```text
data/raw/heated_new_01/
  camera.json
  reference/frame.tif
  reference/frame.json
  moving/frame.tif
  moving/frame.json

data/raw/video_new_01/
  sequence.json
  reference/frame.tif
  reference/frame.json
  frames/000000/frame.tif
  frames/000000/frame.json
  ...

results/video_new_01/
  processing.json
  fields/000000.npz
  ...
  bos.mp4
```

- `camera.json`: pair mode, exposure requested/reported, and requested master gain.
- `frame.json`: format, shape, source, and host UTC capture timestamp.
- `sequence.json`: camera settings, per-frame relative times, duration, and
  completion status. Incomplete sequences are rejected by processing.
- `processing.json`: reference path, rotation, window, step, display component,
  scale, and export fps.

Timestamps come from the host, not camera hardware. Relative sequence times use
a monotonic clock. Aperture, focus, distances, and heat-source settings are manual
and are not read by the scripts; record them separately.

| NPZ array | Meaning |
|---|---|
| `x_px`, `y_px` | Window-centre positions in the analyzed reference image |
| `u_px` | Horizontal apparent pattern displacement, positive right |
| `v_px` | Vertical apparent pattern displacement, positive down |
| `magnitude_px` | Displacement magnitude |
| `ncc_peak` | Highest normalized cross-correlation |
| `peak_margin` | Difference from the next separated correlation peak |
| `valid` | Boolean validity mask |
| `time_s` | Relative sample time in per-frame video fields |

Invalid displacements are `NaN`, not zero. Peaks on the 4-pixel search boundary
are rejected. At 90 degrees clockwise, vector components transform as
`u_new = -v_old`, `v_new = u_old`, with positions rotated accordingly. Analysis is
rerun on the rotated images, so grid locations and individual estimates can differ
slightly. Never overlay an unrotated field on a rotated image.

## Validation and logs

```bash
python scripts/check_io.py
python scripts/validate.py
python scripts/check_correlation.py
```

Expected validation messages include:

```text
PASS: All pixels and metadata match.
PASS: Quick validation checks.
```

The quick check requires at least 90% valid vectors and at most 0.10-pixel RMSE
for five known shifts. It also checks textureless images, ambiguous periodic
patterns, and shifts at or outside the search range. It saves a demonstration
pair under `data/checks/bos_validation_<generated_id>/`.

Optional parameter sweep:

```bash
python scripts/validate.py --sweep --noise-std 0.01
```

This saves `sweep.csv`. Noise is expressed as a standard deviation on the [0, 1]
intensity scale. `--noise-std` requires `--sweep`.

Append-only logs: `logs/capture.log`, `logs/analyze.log`, `logs/io_check.log`, and
`logs/validate.log`. Video progress is printed to the terminal. Refer to timestamps
and dataset paths when interpreting older entries.

Use `--help` on the capture, rotation, analysis, visualization, or validation
scripts, or on `bos_video.py record` / `bos_video.py process`, to inspect options.

## Interpretation limits

The repeated candle trials showed a localized two-sided horizontal-displacement
structure above the flame, consistent with a refractive warm-air plume. Hairdryer
trials also showed broader shifts; camera/pattern motion and airflow-induced
paper movement can contribute. Global offsets were not removed. No cold-blowing
control or independent temperature/velocity measurement was recorded.

The spatial resolution is the correlation grid, not the full sensor resolution.
Raw-image brightness alone and valid-vector percentage alone do not establish
measurement accuracy. Earlier metadata with a leading space in `channel_order`
(`" RGB"`) are rejected; the supported value is `"RGB"`.
