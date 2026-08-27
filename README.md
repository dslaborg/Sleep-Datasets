# Sleep-Datasets

Repository containing the code to preprocess varying sleep datasets building upon
the [psg_utils](https://github.com/perslev/psg-utils) library used for U-Sleep. The preprocessed data created with this
repo was used for training and evaluating [AnySleep](https://github.com/dslaborg/AnySleep).

## Supported datasets

| Dataset                         | URL                                                                | Permission required |
|---------------------------------|--------------------------------------------------------------------|---------------------|
| abc                             | https://doi.org/10.25822/nx52-bc11                                 | yes                 |
| ccshs                           | https://doi.org/10.25822/cg2n-4y91                                 | yes                 |
| cfs                             | https://doi.org/10.25822/jmyx-mz90                                 | yes                 |
| chat                            | https://doi.org/10.25822/d68d-8g03                                 | yes                 |
| dcsm                            | https://doi.org/10.17894/ucph.282d3c1e-9b98-4c1e-886e-704afdfa9179 | no                  |
| dodo, dodh                      | https://doi.org/10.5281/zenodo.15900394                            | no                  |
| hpap                            | https://doi.org/10.25822/xmwv-yz91                                 | yes                 |
| isruc-sg1, isruc-sg2, isruc-sg3 | https://sleeptight.isr.uc.pt/                                      | no                  |
| mass-c1                         | https://doi.org/10.5683/SP3/OVISPE                                 | yes                 |
| mass-c3                         | https://doi.org/10.5683/SP3/9MYUCS                                 | yes                 |
| mesa                            | https://doi.org/10.25822/n7hq-c406                                 | yes                 |
| mros                            | https://doi.org/10.25822/kc27-0425                                 | yes                 |
| phys                            | https://doi.org/10.13026/6phb-r450                                 | no                  |
| sedf-sc, sedf-st                | https://doi.org/10.13026/1q9b-ge17                                 | no                  |
| shhs                            | https://doi.org/10.25822/ghy8-ks59                                 | yes                 |
| sof                             | https://doi.org/10.25822/e1cf-rx65                                 | yes                 |
| svuh                            | https://doi.org/10.13026/C26C7D                                    | no                  |

## Installation

```shell
# Clone the repository
git clone https://github.com/dslaborg/Sleep-Datasets.git
cd anysleep

# Install dependencies
conda env create -f env.yaml

# Install psg_utils fork from https://github.com/n-grieger/psg-utils
git clone https://github.com/n-grieger/psg-utils.git
pip install ./psg-utils
```

## Overview of this repo

```
Sleep-Datasets/
├── config/                           # Hydra configuration files for main scripts
├── checks/                           # Ad hoc verification notebooks for script outputs/logs
├── utils/                            # various mostly dataset-specific utils for extracting psgs/hypnograms/metadata
├── extract_all.sh                    # Runs extraction for all datasets
├── create_datasplit_from_uslep_archive.py  # Script to recreate the datasplit of U-Sleep as a yaml file
├── extract_hypno.py                  # extract "clean" hypnograms from a dataset
├── extract_psg.py                    # extract "clean" PSGs from a dataset
├── prepare_splits.py                 # create a custom datasplit
├── preprocess.py                     # preprocess extracted PSGs and hypnograms
├── env.yaml
├── usleep_split.yaml
└── usleep_split_fixed.yaml
```

## Scripts

The main workflow to preprocess the supported sleep datasets looks as follows:

1. download the datasets from the URLs listed above, note that some datasets require access requests
    * we recommend at least 10 TB of free space on your hard drives, the downloaded datasets and processed files should
      each take approximately 5 TB of space
    * place all datasets in a common folder, the final file structure should look like this:

    <details open>
    <summary>File structure</summary>

    ```
    <base_dir>/
    ├── abc/
    │   ├── datasets/
    │   ├── documentation/
    │   └── polysomnography/
    ├── ccshs/
    │   ├── datasets/
    │   ├── documentation/
    │   ├── forms/
    │   └── polysomnography/
    ├── cfs/
    │   ├── datasets/
    │   ├── forms/
    │   └── polysomnography/
    ├── chat/
    │   ├── datasets/
    │   ├── documentation/
    │   ├── forms/
    │   └── polysomnography/
    ├── dcsm/
    │   └── data/
    ├── dreem/
    │   ├── dodh/
    │   ├── dodo/
    │   ├── prepared/
    │   └── scorers/
    ├── homepap/
    │   ├── datasets/
    │   ├── documentation/
    │   ├── forms/
    │   └── polysomnography/
    ├── isruc/
    │   ├── isruc-sg1/
    │   ├── isruc-sg2/
    │   └── isruc-sg3/
    ├── MASS/
    │   ├── SS1_Annotations/
    │   ├── SS1_EDF/
    │   ├── SS2_Annotations/
    │   ├── SS2_EDF/
    │   ├── SS3_Annotations/
    │   ├── SS3_EDF/
    │   ├── SS4_Annotations/
    │   ├── SS4_EDF/
    │   ├── SS5_Annotations/
    │   └── SS5_EDF/
    ├── mesa/
    │   ├── actigraphy/
    │   ├── datasets/
    │   ├── documentation/
    │   ├── forms/
    │   ├── mesa/
    │   ├── overlap/
    │   └── polysomnography/
    ├── mros/
    │   ├── datasets/
    │   ├── documentation/
    │   ├── forms/
    │   └── polysomnography/
    ├── phys/
    │   └── physionet.org/
    ├── shhs/
    │   ├── biostatistics-with-r/
    │   ├── datasets/
    │   ├── documentation/
    │   ├── forms/
    │   └── polysomnography/
    ├── sleepedfx/
    │   └── physionet.org/
    ├── sof/
    │   ├── datasets/
    │   ├── documentation/
    │   └── polysomnography/
    └── SVUH/
        └── physionet.org/
    ```
    </details>

    * set the `base_dir` and `save_dir` fields in the `base_config.yaml` to the directory you downloaded the data to and
      the directory you want to use for saving the extracted and preprocessed data

2. use `extract_hypno.py` and `extract_psg.py` to extract the PSG signals and hypnograms in a "clean" and unified format
   for each dataset; run `extract_hypno.py` before `extract_psg.py`
    * unifies hypnogram encodings
    * fills offsets and gaps in hypnograms with `UNKNOWN`
    * filters and renames EEG/EOG channels, if necessary creates montages
    * ... and much more
    * `extract.sh` contains the extraction commands for all supported datasets
3. use `preprocess.py` to combine and preprocess extracted signals/hypnograms into a unified HDF5 file
    * resamples the signals to 128 Hz (configurable)
    * scales/normalizes signals
    * shortens PSGs/hypnograms to common lengths for each recording

### Using a subset of datasets

To work with only a subset of datasets, remove the unwanted datasets everywhere they are referenced:

* `extract_all.sh`: omit the command lines for the datasets you do not want
* `config/preprocess.yaml`: delete the `dataset/<name>@datasets.<name>` defaults line for each dataset you do not want
  to include in the combined h5 file
* `config/data_splits.yaml`: delete the corresponding `dataset/<name>@datasets.<name>` line so the dataset is excluded
  from the datasplit as well.

### create_datasplit_from_uslep_archive.py

Creates the exact datasplit used by Perslev et al. in the format of a yaml file. Expects the U-Sleep archive folder from
https://erda.ku.dk/public/archives/58ffa82fae31cd9c89213b1260f694df/published-archive.html.

This repo contains the extracted datasplit files as:

* `usleep_split.yaml`: This is the original datasplit used by Perslev et al.
* `usleep_split_fixed.yaml`: The original datasplit used by Perslev et al. contains some "bad recordings" (see dataset
  configs); these have been removed in this "fixed" version of the datasplit. Additionally, the datasplit used by
  Perslev et al. was based on an old version of the DODO/H datasets with different file names, which we updated manually
  with the new names from https://github.com/Dreem-Organization/dreem-learning-open (luckily, no mapping from old to new
  names is needed since all recordings are in the test set).

Arguments:

- `-p=<path>`: path to the extracted U-Sleep archive folder (required)

Sample call:

```bash
python create_datasplit_from_uslep_archive.py -p ./usleep-archive
```

### extract_hypno.py

Extracts the hypnograms from raw dataset files and unifies them into a common "clean" format (`.ids` files) for
preprocessing. Writes logs to `logs/dataset/<dataset>/<timestamp>/extract_hypno.log`. Sleep stage encoding:

- 0: Wake
- 1: N1
- 2: N2
- 3: N3
- 4: REM
- 9: Artifact (filtered during evaluation)

Arguments:

- This is a Hydra-based script; any configuration can be overwritten using command line arguments
- `-cn=<dataset>/<dataset_name>`: name of the dataset to extract, for which a `<dataset_name>.yaml` file must exist in
  the `config/<dataset>` directory (e.g. `config/dataset/abc.yaml`). Use `config/dataset_w_emg` to include EMG channels

Sample call:

```bash
python extract_hypno.py -cn=dataset/abc
```

### extract_psg.py

Extracts the PSG files from raw dataset files and unifies them into a common "clean" format (`.h5` files) for
preprocessing. Writes logs to `logs/dataset/<dataset>/<timestamp>/extract_psg.log`.

Arguments:

- This is a Hydra-based script; any configuration can be overwritten using command line arguments
- `-cn=<dataset>/<dataset_name>`: name of the dataset to extract, for which a `<dataset_name>.yaml` file must exist in
  the `config/<dataset>` directory (e.g. `config/dataset/abc.yaml`). Use `config/dataset_w_emg` to include EMG channels

Sample call:

```bash
python extract_psg.py -cn=dataset/abc
```

`extract_all.sh` runs both extraction scripts for all supported datasets.

### prepare_splits.py

Creates a custom dataset split (train/valid/test per dataset) following the rules defined by Perslev et al. (fraction-
based split with optional caps on the number of validation/test subjects, family-aware splitting where configured), and
saves it as a yaml file. Optionally supports splits for cross validation runs with the `cv_n_splits` config parameter.

Arguments:

- This is a Hydra-based script (loading `data_splits.yaml` by default, with split ratios defined in the separate dataset
  configs); any configuration can be overwritten using command line arguments
- Commonly overridden parameters:
    - `cv_n_splits`: number of cross-validation splits to create
    - `seed`: random seed for the split
    - `save_file`: where to write the resulting split yaml

Sample call:

```bash
python prepare_splits.py seed=42 save_file=./my_split.yaml
```

### preprocess.py

Preprocesses the extracted PSGs and hypnograms following the steps described by Perslev et al. and combines them into a
single HDF5 file. Resamples the signals, strips/aligns the PSGs and hypnograms to per-recording common lengths, applies
optional filtering and quality control, and scales the signals. Raises an error if the output file already exists
(delete it to re-run).

Arguments:

- This is a Hydra-based script (loading `preprocess.yaml` by default); any configuration can be overwritten using
  command line arguments
- Commonly overridden parameters:
    - `save_file`: where to write the resulting combined h5 file

Sample call:

```bash
python preprocess.py save_file=./processed_data.h5
```

Output structure of the resulting h5 file:

```
processed_data.h5
    ├── Dataset_Name/
    │   ├── Subject_Name/
    │   │   ├── PSG/
    │   │   │   ├── EEG_Channel (e.g., 'F3-M2')
    │   │   │   └── EOG_Channel (e.g., 'E1-M2')
    │   │   ├── hypnogram      # Sleep stage labels per 30s epoch
    │   │   └── class_to_index/  # Epoch indices grouped by sleep stage to filter for all epochs of a given stage
    │   └── ...
    └── ...
```

### Checks

Contains scripts for verification of extraction and preprocessing logs (e.g., for consistent recording IDs, missing
channels, etc). They are meant to be run from within that directory (they read sibling paths like `../logs/...`) and
each writes a corresponding `check_*.log` file summarizing what it checked:

* `check_logs_after_extraction.ipynb` (→ `check_dataset.log`): after running the extraction step, checks the extraction
  logs in `../logs/dataset/...` and verifies for every dataset that all recordings have **both** a PSG and a hypnogram,
  and that the extracted PSGs contain the required EEG/EOG channels.
* `check_logs_after_extraction_w_emg.ipynb` (→ `check_dataset_w_emg.log`): same as above, but for the
  `config/dataset_w_emg`
  (EMG) extraction logs in `../logs/dataset_w_emg/...`.
* `check_preprocessed_recs.ipynb` (→ `check_preprocessing.log`): after the preprocessing step, cross-checks the
  datasplit file against the `preprocess` run log and verifies that every dataset present in the datasplit was
  preprocessed and that all recordings from the datasplit are present in the log.
* `check_preprocessed_recs_w_emg.ipynb` (→ `check_preprocessing_w_emg.log`): same as above, but for the W-EMG
  preprocessed data.

## Configuration

The configuration is implemented using the [Hydra](https://hydra.cc/) framework based on YAML files. If you are not
familiar with Hydra, see the [official documentation](https://hydra.cc/docs/intro) for an introduction.

All configuration files are located in the `config/` directory with the following hierarchy:

- `config/base_config.yaml`: Base configuration for all other configs (except for dataset configs); contains the shared
  settings (sample rate, epoch duration, stage encodings, `base_dir`/`save_dir`)
- `data_splits.yaml`: config expected by `prepare_splits.py`
- `preprocess.yaml`: config expected by `preprocess.py`; preprocesses all datasets with the standard settings (no
  bandpass filtering, no EMG channels)
- `preprocess_with_emg.yaml`: same as `preprocess.yaml`, but uses the `config/dataset_w_emg` dataset configs, which
  additionally extract the EMG channels where available
- `preprocess_with_filtering.yaml`: same as `preprocess.yaml`, but additionally applies a 0.3–35 Hz bandpass filter
  (4th-order Butterworth, IIR)
- `config/dataset/_base_dataset.yaml`: dataset base configuration
- `config/dataset/<dataset>.yaml`: configs for specific datasets with dataset-specific overwrites
- `config/dataset_w_emg`: same structure as `config/dataset`

Configuration files lower in the hierarchy override parameters from higher-level files. All configurations can also be
overwritten using command line arguments when running a script.

To inspect the final resolved configuration of a run, check the `.hydra/` folder in the output directory after running a
script.

### Configuration specialties of datasets

List of noteworthy datasets that deviate from the standard configuration with dataset-specific overwrites in
`config/dataset/<dataset>.yaml`:

* **`cfs`:** The study contains repeated visits from the same families, which we do not want to split apart in the
  training/validation/test splits. Family IDs are extracted by `splitting.family_id_extractor`
  (implemented in `utils/splitting_utils.py`).
* **`mass-c1` and `mass-c3`:** The hypnograms (`*Base.edf`) starts partway into the PSG. Both configs set
  `hypno.write_offsets_to_file: True`. `extract_hypno.py` writes each subject's first hypnogram start time to
  `preparations/offsets.json`, which are read by `extract_psg.py` to trim the PSG by the same amount.
* **`dodo` and `dodh`:** Each Dreem recording has several independent expert scorers. `prepare_gs_dreem` (called via
  `hypno.prepare_func`) computes a gold standard and saves it as `.npy` under
  `cache/<name>/preparations/goldstandards/`. The PSG side uses the custom
  `dod_extract` function because the Dreem `.h5` files are not standard EDFs.

## Git LFS

Log files are stored with [Git LFS](https://git-lfs.com/) instead of directly in the repository.

This means that a normal `git clone` only fetches small *pointer files* (a few hundred bytes) instead of the actual
binary content. If you try to use these files directly, you will instead see LFS pointer text like the following:

```text
version https://git-lfs.github.com/spec/v1
oid sha256:1b41e3...
size 123456789
```

To install Git LFS and configure your local git, run:

```bash
git lfs install
```

If you have already cloned (or pulled) before installing it, download the actual file contents with:

```bash
git lfs pull
```

To check which files are tracked by LFS and whether the real content or only the pointer is present locally, use:

```bash
git lfs ls-files         # lists LFS-tracked files ('-': content, '*': pointer only)
```

## License

This project is released under the MIT License. See LICENSE file for details.
