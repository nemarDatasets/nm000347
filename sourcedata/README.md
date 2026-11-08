# sourcedata: original distribution

The EEG epoch files of the figshare release (article 28955456, version 4, DOI 10.6084/m9.figshare.28955456.v4),
byte for byte, at the depositor's own paths: `epo_data/Normals/EEG/subject<N>/<k>_epo.mat` (healthy controls) and
`epo_data/Patients/EEG/subject<N>/<k>_epo.mat` (ICH patients). These paths come from the `folder_structure` field of the
figshare article record (`figshare_article_28955456_v4.json`, also the folder layout of the article's zip); the figshare file listing
(`figshare_filelist_28955456.json`) gives bare file names only.

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
