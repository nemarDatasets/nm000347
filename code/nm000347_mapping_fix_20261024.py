"""Correct the participant/session mapping of NEMAR nm000347 (HefmiIch2025) by renames.

Usage: python build.py <repo> <inputs_dir> <out_dir>

<repo>       plain git clone of nemarDatasets/nm000347 (no `git annex init` needed), checked out on the new branch,
             whose HEAD is the main commit being corrected.
<inputs_dir> hefmiich2025_file_map_v1.json (true mapping, 98 rows: subject, session, figshare_file_id, group, folder,
             name, size, md5), figshare_article_28955456_v4.json (figshare article record with folder_structure),
             old_vs_true_mapping_rows.json (independent cross-check of the old loader's assignment).
<out_dir>    build receipts (plan.json, build.json).

What it does (stdlib only, no network):
1. Recomputes the assignment of nm000347 <= 1.0.4 from the deposit's own sourcedata/figshare_filelist_28955456.json
   with the rule of the MOABB loader that made it (EEG epoch files = *_epo.mat above 40 MB, sorted by figshare file id,
   a new subject at every 1_epo.mat, local name subNN_k_epo.mat, BIDS sub-NN / ses-(k-1)) and checks it against the
   deposit's sourcedata_provenance.json (names, bytes, subjects) and against old_vs_true_mapping_rows.json.
2. Moves every recording to its true participant/session with `git mv` (same bytes, same git-annex key):
   sub-01..sub-17 = epo_data/Normals/EEG/subject1..17 (group healthy), sub-18..sub-37 = epo_data/Patients/EEG/subject1..20
   (group patient, sub-(17+N)); ses-01..ses-03 = the depositor's 1_epo.mat..3_epo.mat. task/run entities are unchanged.
3. Moves sourcedata/subNN_k_epo.mat to the depositor's own path sourcedata/epo_data/<group>/EEG/subject<N>/<k>_epo.mat.
4. Rewrites the text files the mapping touches: scans.tsv/json (filename + source_file, figshare_file_id,
   previous_filename columns), *_eeg.json TaskDescription (sessions per participant), participants.tsv/json,
   sourcedata_provenance.json, sourcedata/README.md, README.md, dataset_description.json (GeneratedBy note), CHANGES,
   code/HefmiIch2025.metadata.yaml (two fields), plus sourcedata/mapping_correction_20261024.tsv and the figshare
   article record. Nothing else changes.
Fails (exit != 0) before writing anything if any cross-check disagrees.
"""

import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO, INP, OUT = (Path(a) for a in sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)
FIGSHARE_ARTICLE = 28955456
DATE = "2026-10-24"
BRANCH_NOTE = "branch fix-20261024-mapping"


def die(msg):
    print("FATAL:", msg, flush=True)
    sys.exit(3)


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def read_tsv(p):
    # MOABB/mne-bids wrote some TSVs with a UTF-8 BOM; rewritten files are plain UTF-8
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f, delimiter="\t"))


def write_text(p, text):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def write_json(p, obj, indent=4):
    write_text(p, json.dumps(obj, indent=indent, ensure_ascii=False) + "\n")


PTR = re.compile(r"/annex/objects/(SHA256E-s(\d+)--([0-9a-f]{64})((?:\.[A-Za-z0-9]+)*))")


def pointer_key(path):
    try:
        txt = (REPO / path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    m = PTR.fullmatch(txt)
    return m.group(1) if m else None


# ----------------------------------------------------------------------------------------------------------------- inputs
fmap = json.loads((INP / "hefmiich2025_file_map_v1.json").read_text())["files"]
article_bytes = (INP / "figshare_article_28955456_v4.json").read_bytes()
article = json.loads(article_bytes)
xcheck = json.loads((INP / "old_vs_true_mapping_rows.json").read_text())
filelist = json.loads((REPO / "sourcedata" / f"figshare_filelist_{FIGSHARE_ARTICLE}.json").read_text())
prov_old = json.loads((REPO / "sourcedata" / "sourcedata_provenance.json").read_text())

if len(fmap) != 98:
    die(f"file map has {len(fmap)} rows")

# folder_structure of the article record is the authority; re-derive every row of the file map from it.
fs = article.get("folder_structure") or {}
art_files = {f["id"]: f for f in article["files"]}
for r in fmap:
    fid = r["figshare_file_id"]
    folder = fs.get(str(fid))
    if folder != r["folder"]:
        die(f"file {fid}: folder_structure {folder!r} != file map {r['folder']!r}")
    a = art_files[fid]
    if (a["name"], a["size"], a["computed_md5"]) != (r["name"], r["size"], r["md5"]):
        die(f"file {fid}: article record name/size/md5 differ from the file map")
    m = re.fullmatch(r"epo_data/(Normals|Patients)/EEG/subject(\d+)", r["folder"])
    if not m or m.group(1) != r["group"]:
        die(f"bad folder {r['folder']}")
    n = int(m.group(2))
    expect_subject = n if r["group"] == "Normals" else 17 + n
    if expect_subject != r["subject"] or r["name"] != f"{r['session']}_epo.mat":
        die(f"file map row inconsistent: {r}")

# ------------------------------------------------------------------------------------- the old (v<=1.0.4) assignment
eeg = sorted(
    ((f["id"], f["name"], f["size"]) for f in filelist if f["name"].endswith("_epo.mat") and f["size"] > 40_000_000),
    key=lambda x: x[0],
)
old = {}
subj = 0
per = defaultdict(int)
for fid, name, size in eeg:
    if name == "1_epo.mat":
        subj += 1
    per[subj] += 1
    old[fid] = dict(old_subject=subj, old_session=per[subj] - 1, local=f"sub{subj:02d}_{per[subj]}_epo.mat", size=size)
if len(old) != 98 or subj != 37:
    die(f"old rule gives {len(old)} files / {subj} subjects")

prov_files = {e["file"]: e for e in prov_old["files"]}
for fid, o in old.items():
    e = prov_files.get(o["local"])
    if e is None or e["bytes"] != o["size"] or str(e["subject"]) != str(o["old_subject"]):
        die(f"provenance disagrees for {o['local']}: {e}")
xc = {r["file_id"]: r for r in xcheck}
for r in fmap:
    o, x = old[r["figshare_file_id"]], xc[r["figshare_file_id"]]
    if (x["local"], x["old_subject"], x["old_session"], x["new_subject"], x["true_session"]) != (
        o["local"], o["old_subject"], o["old_session"], r["subject"], r["session"]
    ):
        die(f"cross-check disagrees for file {r['figshare_file_id']}: {x} vs {o} / {r}")

# ---------------------------------------------------------------------------------------------------- rename plan
tree = git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
tree_set = set(tree)
plan = []  # one row per recording
renames = []  # (old path, new path)
for r in sorted(fmap, key=lambda r: (r["subject"], r["session"])):
    o = old[r["figshare_file_id"]]
    os_, oi = o["old_subject"], o["old_session"]
    S, k = r["subject"], r["session"]
    old_pref, new_pref = f"sub-{os_}_ses-{oi}_", f"sub-{S:02d}_ses-{k:02d}_"
    old_dir, new_dir = f"sub-{os_}/ses-{oi}", f"sub-{S:02d}/ses-{k:02d}"
    files = [p for p in tree if p.startswith(old_dir + "/")]
    if len(files) != 11:
        die(f"{old_dir}: {len(files)} files, expected 11")
    for p in files:
        rel = p[len(old_dir) + 1 :]
        parent, _, name = rel.rpartition("/")
        if not name.startswith(old_pref):
            die(f"unexpected name {p}")
        newp = new_dir + "/" + (parent + "/" if parent else "") + new_pref + name[len(old_pref) :]
        renames.append((p, newp))
    n_folder = int(r["folder"].rsplit("subject", 1)[1])
    src_old = f"sourcedata/{o['local']}"
    src_new = f"sourcedata/{r['folder']}/{r['name']}"
    if src_old not in tree_set:
        die(f"missing {src_old}")
    renames.append((src_old, src_new))
    bdf_old = f"{old_dir}/eeg/{old_pref}task-imagery_run-0_eeg.bdf"
    bdf_new = f"{new_dir}/eeg/{new_pref}task-imagery_run-0_eeg.bdf"
    if bdf_old not in tree_set:
        die(f"missing {bdf_old}")
    plan.append(
        dict(
            participant_id=f"sub-{S:02d}",
            session=f"ses-{k:02d}",
            subject=S,
            session_k=k,
            group="healthy" if r["group"] == "Normals" else "patient",
            depositor_group=r["group"],
            depositor_subject=n_folder,
            source_file=src_new,
            figshare_file_id=r["figshare_file_id"],
            bytes=r["size"],
            md5=r["md5"],
            sha256=prov_files[o["local"]]["sha256"],
            previous_participant=f"sub-{os_}",
            previous_session=f"ses-{oi}",
            previous_sourcedata=src_old,
            previous_bdf=bdf_old,
            new_bdf=bdf_new,
            bdf_key=pointer_key(bdf_old),
            mat_key=pointer_key(src_old),
        )
    )
olds = [a for a, _ in renames]
news = [b for _, b in renames]
if len(set(olds)) != len(olds) or len(set(news)) != len(news) or set(news) & tree_set:
    die("rename plan has duplicates or collides with existing paths")
moved_dirs = {p.split("/")[0] for p in olds if p.startswith("sub-")}
left = [p for p in tree if p.startswith("sub-") and p.split("/")[0] in moved_dirs and p not in set(olds)]
if left:
    die(f"files left behind in old subject dirs: {left[:5]}")
for row in plan:
    if not row["bdf_key"] or not row["mat_key"]:
        die(f"not an annex pointer: {row['previous_bdf']} / {row['previous_sourcedata']}")
    if row["mat_key"].split("--")[1].split(".")[0] != row["sha256"]:
        die(f"mat key != provenance sha256 for {row['previous_sourcedata']}")
(OUT / "plan.json").write_text(json.dumps(dict(plan=plan, renames=renames), indent=1))
print("plan OK:", len(plan), "recordings,", len(renames), "renames", flush=True)

# --------------------------------------------------------------------------------------------------- apply renames
for a, b in renames:
    (REPO / b).parent.mkdir(parents=True, exist_ok=True)
    git("mv", a, b)

# ----------------------------------------------------------------------------------------- per-recording sidecars
SESS_TEXT_OLD = "17 healthy + 20 ICH patients, 1-6 sessions per subject."
SESS_TEXT_NEW = (
    "17 healthy + 20 ICH patients, 1-3 sessions per participant (98 in total; the sessions of a participant are "
    "consecutive runs of one visit)."
)
for row in plan:
    sdir = REPO / row["participant_id"] / row["session"]
    pref = f"{row['participant_id']}_{row['session']}_"
    scans = sdir / f"{pref}scans.tsv"
    rows = read_tsv(scans)
    if rows[0] != ["filename", "acq_time"] or len(rows) != 2:
        die(f"unexpected scans.tsv {scans}: {rows}")
    old_fn = rows[1][0]
    if old_fn != row["previous_bdf"].split("/", 2)[2]:
        die(f"scans.tsv of {row['previous_bdf']} names {old_fn}")
    new_fn = row["new_bdf"].split("/", 2)[2]
    out = io.StringIO()
    w = csv.writer(out, delimiter="\t", lineterminator="\n")
    w.writerow(["filename", "acq_time", "source_file", "figshare_file_id", "previous_filename"])
    w.writerow([new_fn, rows[1][1], row["source_file"], row["figshare_file_id"], row["previous_bdf"]])
    write_text(scans, out.getvalue())
    sj = sdir / f"{pref}scans.json"
    j = json.loads(sj.read_text())
    j["source_file"] = {
        "Description": "Original file this recording was converted from (byte-identical copy under sourcedata/, at the "
        "depositor's path in figshare article 28955456 v4)."
    }
    j["figshare_file_id"] = {"Description": "figshare file id of source_file (article 28955456, version 4)."}
    j["previous_filename"] = {
        "Description": "Path of this same recording (same bytes) in versions <= 1.0.4 of this deposit, which assigned "
        "recordings to the wrong participants; see the README section 'Correction (2026-10-24)'."
    }
    write_text(sj, json.dumps(j, indent="\t") + "\n")
    ej = sdir / "eeg" / f"{pref}task-imagery_run-0_eeg.json"
    t = ej.read_text()
    if t.count(SESS_TEXT_OLD) != 1:
        die(f"TaskDescription text not found once in {ej}")
    write_text(ej, t.replace(SESS_TEXT_OLD, SESS_TEXT_NEW))

# ------------------------------------------------------------------------------------------------------ participants
by_subj = defaultdict(list)
for row in plan:
    by_subj[row["subject"]].append(row)
old_pt = read_tsv(REPO / "participants.tsv")
hdr = old_pt[0]
if hdr != ["participant_id", "age", "sex", "hand", "weight", "height", "group", "species", "bci_experience"]:
    die(f"participants.tsv header {hdr}")
out = io.StringIO()
w = csv.writer(out, delimiter="\t", lineterminator="\n")
w.writerow(hdr + ["source_folder", "n_sessions"])
for S in range(1, 38):
    rr = by_subj[S]
    r0 = rr[0]
    folder = "epo_data/{}/EEG/subject{}".format(r0["depositor_group"], r0["depositor_subject"])
    w.writerow([f"sub-{S:02d}", "n/a", "n/a", "R", "n/a", "n/a", r0["group"], "human", "n/a", folder, len(rr)])
write_text(REPO / "participants.tsv", out.getvalue())
pj = json.loads((REPO / "participants.json").read_text())
pj["group"] = {
    "Description": "Participant group, from the depositor's folder (Normals = healthy controls, Patients = ICH patients).",
    "Levels": {
        "healthy": "healthy control (figshare epo_data/Normals/EEG/subject1-17 = sub-01..sub-17)",
        "patient": "intracerebral hemorrhage (ICH) patient (figshare epo_data/Patients/EEG/subject1-20 = sub-18..sub-37)",
    },
}
pj["hand"]["Description"] = "Handedness of the participant (all participants were right-handed according to the paper)."
pj["source_folder"] = {
    "Description": "The depositor's folder holding this participant's EEG epoch files in figshare article 28955456 v4 "
    "(folder_structure of the article record); the files are under sourcedata/ at the same path."
}
pj["n_sessions"] = {"Description": "Number of sessions (consecutive runs of one visit) released for this participant."}
pj["Description"] = (
    "Participant list (17 healthy controls, 20 ICH patients). Age, sex, weight and height per participant are not "
    "released; the paper reports 8 female / 29 male, aged 20-65."
)
write_json(REPO / "participants.json", pj)

# ------------------------------------------------------------------------------------------------------- sourcedata
art_name = f"figshare_article_{FIGSHARE_ARTICLE}_v4.json"
(REPO / "sourcedata" / art_name).write_bytes(article_bytes)
corr = io.StringIO()
w = csv.writer(corr, delimiter="\t", lineterminator="\n")
cols = [
    "participant_id", "session", "group", "source_file", "figshare_file_id", "bytes", "md5", "sha256", "bids_file",
    "previous_participant", "previous_session", "previous_sourcedata", "previous_bids_file",
]
w.writerow(cols)
for row in plan:
    w.writerow([row["participant_id"], row["session"], row["group"], row["source_file"], row["figshare_file_id"],
                row["bytes"], row["md5"], row["sha256"], row["new_bdf"], row["previous_participant"],
                row["previous_session"], row["previous_sourcedata"], row["previous_bdf"]])
write_text(REPO / "sourcedata" / "mapping_correction_20261024.tsv", corr.getvalue())

shared_old = [e for e in prov_old["files"] if e.get("subject") in (None, "")]
files = []
for row in plan:
    files.append(
        dict(
            file=row["source_file"][len("sourcedata/"):],
            bytes=row["bytes"],
            sha256=row["sha256"],
            subject=str(row["subject"]),
            session=row["session_k"],
            participant_id=row["participant_id"],
            group=row["group"],
            figshare_file_id=row["figshare_file_id"],
            md5=row["md5"],
            url=f"https://ndownloader.figshare.com/files/{row['figshare_file_id']}",
            previous_name=row["previous_sourcedata"][len("sourcedata/"):],
        )
    )
files += shared_old
files.append(
    dict(
        file=art_name,
        bytes=len(article_bytes),
        sha256=hashlib.sha256(article_bytes).hexdigest(),
        subject=None,
        url=f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE}/versions/4",
        how="figshare article record (metadata only), retrieved 2026-10-24T13:36Z; its folder_structure field (figshare "
        "file id -> depositor folder) is the source of the participant/session assignment of this deposit",
    )
)
prov = dict(prov_old)
prov["files"] = files
prov["n_files"] = len(files)
prov["total_bytes"] = sum(e["bytes"] for e in files)
prov["n_subjects_recorded"] = len({e["subject"] for e in files if e.get("subject")})
prov["naming"] = "depositor_paths: epo_data/<Normals|Patients>/EEG/subject<N>/<k>_epo.mat (figshare article 28955456 v4 folder_structure)"
prov["subject_rule"] = "subject 1-17 = epo_data/Normals/EEG/subject1-17; subject 18-37 = epo_data/Patients/EEG/subject1-20 (17 + N); session k = <k>_epo.mat"
prov["revisions"] = list(prov_old.get("revisions") or []) + [
    dict(
        date=DATE,
        version=f"unreleased ({BRANCH_NOTE})",
        renamed_files=98,
        added_files=1,
        added_bytes=len(article_bytes),
        note="Participant mapping corrected. The 98 EEG epoch files (same bytes and SHA-256) moved from the MOABB cache "
        "names subNN_k_epo.mat of the old loader, which assigned them to the wrong subjects (figshare upload order), to "
        "the depositor's paths epo_data/<group>/EEG/subject<N>/<k>_epo.mat taken from the figshare article record "
        "(added as " + art_name + "); 'subject' now follows that folder. previous_name gives each file's old name.",
    )
]
write_json(REPO / "sourcedata" / "sourcedata_provenance.json", prov, indent=1)

write_text(
    REPO / "sourcedata" / "README.md",
    f"""# sourcedata: original distribution

The EEG epoch files of the figshare release (article {FIGSHARE_ARTICLE}, version 4, DOI 10.6084/m9.figshare.28955456.v4),
byte for byte, at the depositor's own paths: `epo_data/Normals/EEG/subject<N>/<k>_epo.mat` (healthy controls) and
`epo_data/Patients/EEG/subject<N>/<k>_epo.mat` (ICH patients). These paths come from the `folder_structure` field of the
figshare article record (`{art_name}`, also the folder layout of the article's zip); the figshare file listing
(`figshare_filelist_{FIGSHARE_ARTICLE}.json`) gives bare file names only.

| | |
|---|---|
| MOABB class | `moabb.datasets.HefmiIch2025` |
| Retrieved | 2026-08-13 (EEG epoch files); 2026-10-16 (file list); 2026-10-24 (article record) |
| Files | 98 EEG epoch files + 2 figshare metadata files |
| License | CC-BY-NC-ND-4.0 |
| Upstream DOI | 10.1038/s41597-025-06100-7 |

`sourcedata_provenance.json` lists every file with its size, SHA-256, figshare file id and md5, and the BIDS participant
(`subject` = MOABB subject number, `participant_id`) and session it belongs to.

Until version 1.0.4 these files were named `subNN_k_epo.mat` after the cache of the MOABB loader of the time, which
assigned them to the wrong participants (see the README of the dataset, section "Correction (2026-10-24)").
`mapping_correction_20261024.tsv` lists, for every file, its old name and BIDS path and its corrected ones.
""",
)

# ------------------------------------------------------------------------------------------------ dataset level text
readme = (REPO / "README.md").read_text()
n_sess = Counter(len(v) for v in by_subj.values())
CORR = f"""
Correction (2026-10-24): participant and session mapping
--------------------------------------------------------
Versions up to 1.0.4 of this deposit assigned the 98 EEG recordings to the wrong participants. The export was made
with the MOABB `HefmiIch2025` loader of that time, which built participants from the figshare file listing: it sorted
the EEG epoch files by figshare file id (the upload order) and started a new participant at every file named
`1_epo.mat`. The figshare file names carry no participant (every participant's files are `1_epo.mat`, `2_epo.mat`,
`3_epo.mat`) and the upload order is shuffled, so 23 of the 37 participants of versions <= 1.0.4 mixed sessions of 2 to
5 different people, 31 of the 37 real people were split across 2 or 3 participants, and some participants had up to 6
sessions although nobody has more than 3. Only `sub-8` of version 1.0.4 was one complete person (now `sub-25`).

This version assigns every file by the depositor's own folder, published in the figshare article record
(`folder_structure` of https://api.figshare.com/v2/articles/28955456/versions/4, the same folders as the article zip):

- `sub-01` ... `sub-17` = `epo_data/Normals/EEG/subject1` ... `subject17`: healthy controls (`group` = healthy);
- `sub-18` ... `sub-37` = `epo_data/Patients/EEG/subject1` ... `subject20`: ICH patients (`group` = patient;
  `sub-(17+N)` for `subjectN`);
- `ses-01`, `ses-02`, `ses-03` = the depositor's `1_epo.mat`, `2_epo.mat`, `3_epo.mat`.

37 participants, 98 sessions ({n_sess[3]} participants with 3 sessions, {n_sess[2]} with 2, {n_sess[1]} with 1), 2,940 trials (15 left-hand and 15 right-hand
trials per session). The sessions of a participant are not separate visits: they are consecutive runs recorded on the
same day, in order, starting 15 to 34 minutes apart (start times of the raw HDF5 recordings of the same release; each
run lasts about 15 minutes).
Treat them as runs of one visit, e.g. when designing cross-session evaluations.

The assignment was checked four ways: the article zip's central directory (98/98 files in the same folders, matched
by md5); the creation times in the MAT headers (the 98 files form 37 contiguous blocks, one per folder, sessions in
order); per-session spectral fingerprints (participant identification AUC 0.97-0.99 with this mapping, 0.54-0.58 with
the old one, 0.50 by chance); and md5 against figshare (98/98).

No signal data changed. Every recording is the file of version 1.0.4 under a new name (same bytes, same git-annex key);
each session's `scans.tsv` gives the recording's source file, figshare file id and previous path, and
`sourcedata/mapping_correction_20261024.tsv` lists the old and new paths of every file. The patient-code field of the
BDF headers still holds the participant number of the 1.0.4 export (MOABB wrote it there); the BIDS file names and
`participants.tsv` are authoritative. Results computed on versions <= 1.0.4 that rely on participant identity
(within- or cross-session and cross-subject splits, per-participant statistics) should be recomputed.
"""
anchor = "\nDataset Overview\n----------------\n"
if readme.count(anchor) != 1:
    die("README anchor not found")
readme = readme.replace(anchor, "\n" + CORR + anchor, 1)
for a, b in (
    ("  Study design: 2-class hand MI (left/right grasping) for ICH rehabilitation. 17 healthy + 20 ICH patients, 1-6 sessions per subject.",
     "  Study design: 2-class hand MI (left/right grasping) for ICH rehabilitation. 17 healthy + 20 ICH patients, 1-3 sessions (consecutive runs of one visit) per participant, 98 in total."),
    ("  Trials: 3330\n  Trials context: 37 subjects x ~3 sessions x 30 trials = ~3330",
     "  Trials: 2940\n  Trials context: 98 sessions x 30 trials (15 left_hand, 15 right_hand) = 2940"),
    ("  Sessions per subject: 3\n", "  Sessions per subject: 1-3 (98 sessions in total)\n"),
):
    if readme.count(a) != 1:
        die(f"README line not found once: {a[:60]}")
    readme = readme.replace(a, b)
write_text(REPO / "README.md", readme)

dd = json.loads((REPO / "dataset_description.json").read_text())
dd["GeneratedBy"] = list(dd.get("GeneratedBy") or []) + [
    {
        "Name": "nm000347 participant-mapping correction",
        "Version": DATE,
        "Description": "Recordings and source files re-assigned to their true participants and sessions by renaming "
        "only (no signal changed): sub-01..sub-17 = figshare epo_data/Normals/EEG/subject1-17 (healthy controls), "
        "sub-18..sub-37 = epo_data/Patients/EEG/subject1-20 (ICH patients), ses-01..03 = the depositor's "
        "1_epo.mat..3_epo.mat. Versions <= 1.0.4 mixed sessions of different people (README, section 'Correction "
        "(2026-10-24)'); the sessions of a participant are consecutive runs of one visit.",
        "CodeURL": "https://github.com/nemarDatasets/nm000347/blob/fix-20261024-mapping/code/nm000347_mapping_fix_20261024.py",
    }
]
write_text(REPO / "dataset_description.json", json.dumps(dd, indent=2, ensure_ascii=False) + "\n")

changes = (REPO / "CHANGES").read_text()
entry = f"""Unreleased ({BRANCH_NOTE}, prepared {DATE})
  - Participant/session mapping corrected (see README, "Correction (2026-10-24)"). Versions <= 1.0.4 assigned the 98
    recordings to participants by figshare upload order, mixing sessions of 2-5 people in 23 of 37 participants.
    Recordings now follow the depositor's folders: sub-01..sub-17 healthy controls (Normals/subject1-17),
    sub-18..sub-37 ICH patients (Patients/subject1-20), ses-01..03 = 1_epo.mat..3_epo.mat (consecutive same-day runs).
  - All 98 recordings and 98 source files renamed only (same bytes and git-annex keys); scans.tsv gains source_file,
    figshare_file_id and previous_filename; participants.tsv group is healthy/patient (was ICH for everyone) and gains
    source_folder, n_sessions; sourcedata/ uses the depositor's paths, adds the figshare article record and
    mapping_correction_20261024.tsv; README trial count corrected to 2940 (98 sessions x 30).
"""
write_text(REPO / "CHANGES", entry + changes)

yml = REPO / "code" / "HefmiIch2025.metadata.yaml"
y = yml.read_text()
for a, b in (
    ("1-6 sessions per\n    subject.", "1-3 sessions per participant (98 in total; consecutive runs of one visit)."),
    ("  n_trials: 3330\n", "  n_trials: 2940\n"),
    ("trials_context: 37 subjects x ~3 sessions x 30 trials = ~3330", "trials_context: 98 sessions x 30 trials = 2940"),
):
    c = y.count(a)
    if c < 1:
        die(f"metadata.yaml text not found: {a}")
    y = y.replace(a, b)
y = "# Edited 2026-10-24 (participant-mapping correction): study_design sessions, n_trials, trials_context.\n" + y
write_text(yml, y)

code_dst = REPO / "code" / "nm000347_mapping_fix_20261024.py"
code_dst.write_bytes(Path(__file__).read_bytes())

# -------------------------------------------------------------------------------------------------------- stage, check
git("add", "-A")
st = git("status", "--porcelain")
(OUT / "status_porcelain.txt").write_text(st)
for row in plan:
    if pointer_key(row["new_bdf"]) != row["bdf_key"] or pointer_key(row["source_file"]) != row["mat_key"]:
        die(f"key changed for {row['new_bdf']}")
build = dict(
    head_before=git("rev-parse", "HEAD").strip(),
    n_renames=len(renames),
    sessions_per_participant=dict(n_sess),
    groups=dict(Counter(r["group"] for r in plan)),
    session_k=dict(Counter(r["session_k"] for r in plan)),
)
(OUT / "build.json").write_text(json.dumps(build, indent=1))
print("BUILD_STAGED", json.dumps(build))
