#!/usr/bin/env python3
"""
siia_to_kml.py - turn SIIA map query responses into a KML/KMZ for Google Earth.

How to capture (in your browser, while logged in to SIIA):
  1. Open DevTools (F12) > Network tab. Tick "Preserve log".
  2. Click the CVPs / chambers / posts you care about on the map.
     Each click fires .../MapServer/<n>/query requests (one per layer).
  3. Right-click anywhere in the request list > "Save all as HAR with content".
  4. Run:   python siia_to_kml.py capture.har -o siia.kmz

You can pass several HAR files, or plain .json files you saved from the
Response tab of a single query. Features are de-duplicated by objectid.

Note: a HAR file contains your session cookies/tokens. Keep it on your
machine and delete it when done; don't share it.

Only uses the Python standard library. If the service ever answers in a
projection other than Web Mercator, install pyproj (pip install pyproj).
"""
import argparse
import base64
import html
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Optional: give layer numbers readable names, e.g. {6: "Camaras", 10: "Condutas"}
LAYER_NAMES = {}

QUERY_RE = re.compile(r"/rest/services/(.+?)/MapServer/(\d+)/query", re.I)
WEB_MERCATOR = {3857, 102100, 102113, 900913}
R = 6378137.0


def merc_to_lonlat(x, y):
    lon = math.degrees(x / R)
    lat = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)
    return lon, lat


def make_transformer(wkid):
    if wkid in WEB_MERCATOR or wkid is None:
        return merc_to_lonlat
    if wkid == 4326:
        return lambda x, y: (x, y)
    try:
        from pyproj import Transformer
    except ImportError:
        sys.exit(f"Response uses spatial reference {wkid}; install pyproj (pip install pyproj).")
    t = Transformer.from_crs(wkid, 4326, always_xy=True)
    return lambda x, y: t.transform(x, y)


def wkid_of(data):
    sr = data.get("spatialReference") or {}
    return sr.get("latestWkid") or sr.get("wkid")


def load_har(path):
    har = json.loads(Path(path).read_text(encoding="utf-8"))
    for entry in har["log"]["entries"]:
        m = QUERY_RE.search(entry["request"]["url"])
        if not m:
            continue
        content = entry["response"].get("content", {})
        text = content.get("text")
        if not text:
            continue
        if content.get("encoding") == "base64":
            text = base64.b64decode(text).decode("utf-8", "replace")
        try:
            data = json.loads(text)
        except ValueError:
            continue  # e.g. pbf responses
        if "features" in data:
            yield int(m.group(2)), data


def load_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    m = re.search(r"(\d+)", Path(path).stem)
    yield (int(m.group(1)) if m else 0), data


def layer_label(layer_id, data):
    if layer_id in LAYER_NAMES:
        return LAYER_NAMES[layer_id]
    gt = (data.get("geometryType") or "").replace("esriGeometry", "").lower()
    if not gt:
        for f in data["features"]:
            g = f.get("geometry") or {}
            gt = "point" if "x" in g else "polyline" if "paths" in g else "polygon" if "rings" in g else ""
            if gt:
                break
    return f"Layer {layer_id}" + (f" ({gt})" if gt else "")


def fmt_attr(key, value):
    if key.endswith("_date") and isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return value


def description(attrs):
    rows = "".join(
        f"<tr><td><b>{html.escape(str(k))}</b></td><td>{html.escape(str(fmt_attr(k, v)))}</td></tr>"
        for k, v in attrs.items()
        if v not in (None, "")
    )
    return f"<table>{rows}</table>"


def coords(points, tf):
    return " ".join("{:.7f},{:.7f},0".format(*tf(x, y)) for x, y in points)


def geometry_kml(g, tf):
    if "x" in g and "y" in g:
        return f"<Point><coordinates>{coords([(g['x'], g['y'])], tf)}</coordinates></Point>"
    if "paths" in g:
        parts = [f"<LineString><tessellate>1</tessellate><coordinates>{coords(p, tf)}</coordinates></LineString>"
                 for p in g["paths"]]
        return parts[0] if len(parts) == 1 else f"<MultiGeometry>{''.join(parts)}</MultiGeometry>"
    if "rings" in g:
        parts = [f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords(r, tf)}</coordinates>"
                 f"</LinearRing></outerBoundaryIs></Polygon>" for r in g["rings"]]
        return parts[0] if len(parts) == 1 else f"<MultiGeometry>{''.join(parts)}</MultiGeometry>"
    return None


def build_kml(layers):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>SIIA export</name>',
           '<Style id="pt"><IconStyle><color>ff0080ff</color><scale>0.8</scale><Icon>'
           '<href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle>'
           '<LabelStyle><scale>0.7</scale></LabelStyle></Style>',
           '<Style id="ln"><LineStyle><color>ff00ffff</color><width>3</width></LineStyle></Style>',
           '<Style id="pg"><LineStyle><color>ff00ffff</color></LineStyle>'
           '<PolyStyle><color>4000ffff</color></PolyStyle></Style>']
    counts = {}
    for label in sorted(layers):
        out.append(f"<Folder><name>{html.escape(label)}</name>")
        for attrs, geom_xml, style in layers[label].values():
            name = " ".join(str(attrs.get(k)) for k in ("tipoutilizacao", "idobjeto") if attrs.get(k))
            out.append(f"<Placemark><name>{html.escape(name)}</name><styleUrl>#{style}</styleUrl>"
                       f"<description><![CDATA[{description(attrs)}]]></description>{geom_xml}</Placemark>")
        out.append("</Folder>")
        counts[label] = len(layers[label])
    out.append("</Document></kml>")
    return "\n".join(out), counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help=".har and/or .json files")
    ap.add_argument("-o", "--output", default="siia.kml", help="output .kml or .kmz")
    args = ap.parse_args()

    layers = {}
    for path in args.inputs:
        loader = load_har if path.lower().endswith(".har") else load_json
        print(loader(path))
        for layer_id, data in loader(path):
            tf = make_transformer(wkid_of(data))
            label = layer_label(layer_id, data)
            bucket = layers.setdefault(label, {})
            for f in data["features"]:
                g = f.get("geometry")
                attrs = f.get("attributes", {})
                if not g:
                    continue
                gx = geometry_kml(g, tf)
                if gx is None:
                    continue
                oid = attrs.get("objectid", attrs.get("OBJECTID", attrs.get("idobjeto", json.dumps(g))))
                style = "pt" if "x" in g else "ln" if "paths" in g else "pg"
                bucket[oid] = (attrs, gx, style)

    if not layers:
        sys.exit("No MapServer query responses found. Did you click features with DevTools open and "
                 "save the HAR 'with content'?")

    kml, counts = build_kml(layers)
    out = Path(args.output)
    if out.suffix.lower() == ".kmz":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", kml)
    else:
        out.write_text(kml, encoding="utf-8")
    for label, n in counts.items():
        print(f"{label}: {n} features")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()