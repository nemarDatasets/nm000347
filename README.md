[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000347-blue)](https://doi.org/10.82901/nemar.nm000347)

HefmiIch2025
============

Hybrid EEG-fNIRS MI dataset for ICH from Shi et al 2025.


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

37 participants, 98 sessions (25 participants with 3 sessions, 11 with 2, 1 with 1), 2,940 trials (15 left-hand and 15 right-hand
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

Dataset Overview
----------------
  Code: HefmiIch2025
  Paradigm: imagery
  DOI: 10.1038/s41597-025-06100-7
  Subjects: 37
  Sessions per subject: 1-3 (98 sessions in total)
  Events: left_hand=1, right_hand=2
  Trial interval: [0, 10] s
  File format: MAT (pre-epoched)
  Data preprocessed: True

Acquisition
-----------
  Sampling rate: 256.0 Hz
  Number of channels: 32
  Channel types: eeg=32
  Channel names: FC1, AF3, AF4, CP1, CP2, CP6, Cz, C3, C4, T7, T8, FC2, FC5, FC6, Pz, CP5, PO3, PO4, Oz, Fp2, Fp1, Fz, F3, F4, F7, F8, P3, P4, P7, P8, O1, O2
  Montage: biosemi32
  Hardware: g.HIamp (g.tec medical engineering GmbH)
  Line frequency: 50.0 Hz
  Online filters: {}

Participants
------------
  Number of subjects: 37
  Health status: mixed (17 healthy, 20 ICH patients)
  Clinical population: intracerebral hemorrhage (ICH)
  Age: min=20.0, max=65.0
  Gender distribution: female=8, male=29
  Handedness: right-handed
  Species: human

Experimental Protocol
---------------------
  Paradigm: imagery
  Number of classes: 2
  Class labels: left_hand, right_hand
  Trial duration: 27.0 s
  Study design: 2-class hand MI (left/right grasping) for ICH rehabilitation. 17 healthy + 20 ICH patients, 1-3 sessions (consecutive runs of one visit) per participant, 98 in total.
  Feedback type: none
  Stimulus type: directional arrow + auditory beep
  Stimulus modalities: visual, auditory
  Primary modality: visual
  Synchronicity: synchronous
  Mode: offline

HED Event Annotations
---------------------
  Schema: HED 8.4.0 | Browse: https://www.hedtags.org/hed-schema-browser

  left_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Left, Hand

  right_hand
    ├─ Sensory-event, Experimental-stimulus, Visual-presentation
    └─ Agent-action
       └─ Imagine
          ├─ Move
          └─ Right, Hand

Paradigm-Specific Parameters
----------------------------
  Detected paradigm: motor_imagery
  Imagery tasks: left_hand, right_hand
  Cue duration: 2.0 s
  Imagery duration: 10.0 s

Data Structure
--------------
  Trials: 2940
  Trials context: 98 sessions x 30 trials (15 left_hand, 15 right_hand) = 2940

Signal Processing
-----------------
  Classifiers: CSP+SVM, FBCSP+SVM, EEGBaseNet, TF+SVM
  Feature extraction: CSP, FBCSP, time-frequency features
  Frequency bands: preprocessing=[0.5, 30.0] Hz
  Spatial filters: CSP, FBCSP

Cross-Validation
----------------
  Method: 5-fold
  Folds: 5
  Evaluation type: within_subject

BCI Application
---------------
  Applications: rehabilitation
  Environment: clinical
  Online feedback: False

Tags
----
  Pathology: Healthy, Stroke
  Modality: Motor
  Type: Clinical, Research

Documentation
-------------
  DOI: 10.1038/s41597-025-06100-7
  License: CC-BY-NC-ND-4.0
  Investigators: Jian Shi, Danyang Chen, Xingwei Zhao, Zhixian Zhao, Shengjie Li, Yeguang Xu, Tao Ding, Zheng Zhu, Peng Zhang, Qing Ye, Yingxin Tang, Ping Zhang, Bo Tao, Zhouping Tang
  Institution: Huazhong University of Science and Technology
  Country: CN
  Data URL: https://figshare.com/articles/dataset/28955456
  Publication year: 2025

References
----------
Shi, J., Chen, D., et al. (2025). HEFMI-ICH: a hybrid EEG-fNIRS motor imagery dataset for brain-computer interface in intracerebral hemorrhage. Scientific Data. https://doi.org/10.1038/s41597-025-06100-7
Appelhoff, S., Sanderson, M., Brooks, T., Vliet, M., Quentin, R., Holdgraf, C., Chaumon, M., Mikulan, E., Tavabi, K., Hochenberger, R., Welke, D., Brunner, C., Rockhill, A., Larson, E., Gramfort, A. and Jas, M. (2019). MNE-BIDS: Organizing electrophysiological data into the BIDS format and facilitating their analysis. Journal of Open Source Software 4: (1896). https://doi.org/10.21105/joss.01896

Pernet, C. R., Appelhoff, S., Gorgolewski, K. J., Flandin, G., Phillips, C., Delorme, A., Oostenveld, R. (2019). EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Scientific Data, 6, 103. https://doi.org/10.1038/s41597-019-0104-8

---
Generated by MOABB 1.5.0 (Mother of All BCI Benchmarks)
https://github.com/NeuroTechX/moabb
