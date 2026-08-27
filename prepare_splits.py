import logging
import os
import re
from collections import defaultdict
from glob import glob

import hydra
import numpy as np
import pandas as pd
from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def dict_to_yaml(value_to_write, depth=0):
    yaml_string = ""
    whitespaces = "  " * depth
    if isinstance(value_to_write, dict):
        for key, value in value_to_write.items():
            yaml_string += f"\n{whitespaces}{key}: {dict_to_yaml(value, depth+1)}"
    elif isinstance(value_to_write, list):
        for value in value_to_write:
            yaml_string += f"\n{whitespaces}- {dict_to_yaml(value, depth+1)}"
    elif isinstance(value_to_write, str):
        yaml_string += f'"{value_to_write}"'
    else:
        raise NotImplementedError(f"Type {type(value_to_write)} not implemented")
    return yaml_string


def pair_by_names(files, subject_matching_regex=None):
    """
    Takes a list of file names and returns a list of tuples of file names in
    the list that share substrings matches by the regular expression
    'subject_matching_regex'. The regex should match to 1 group in each file.

    That is, a list of files ['FILE_1_1', 'FILE_1_2', 'FILE_2_1'] and
    subject_matching_regex ".*?_(\d+).*" will result in:

       [ ('FILE_1_1', 'FILE_1_2') , ('FILE_2_1',) ]

    Args:
        files:                  (list) A list of filenames
        subject_matching_regex: (str)  A regex string that that matches exactly
                                       one group (sub-string) within all file
                                       names in 'files'. Pairing will be made
                                       based on these sub-strings.

    Returns:
        A list of tuples of paired filenames
    """
    if subject_matching_regex is not None:
        logger.info(f"Pairing files based on regex {subject_matching_regex}")
        regex = re.compile(subject_matching_regex)
        names = []
        for f_path in files:
            f_path = os.path.split(f_path)[-1]  # Split just in case full paths
            matches = re.findall(regex, f_path)
            if len(matches) != 1:
                raise ValueError(
                    "'subject_matching_regex' of {} matched {} "
                    "substrings ({}) within filename {}, "
                    "expected 1.".format(
                        subject_matching_regex, len(matches), matches, f_path
                    )
                )
            names.append(matches[0])
    else:
        names = [os.path.splitext(os.path.split(i)[-1])[0] for i in files]
    inds = defaultdict(list)
    for i, item in enumerate(names):
        inds[item].append(i)
    pairs = inds.values()
    return np.array([tuple(np.array(files)[i]) for i in pairs], dtype=object)


def get_split_sizes(subject_dirs, n_splits, cfg):
    """
    Returns:
        3 ints, number of training-, validation- and testing samples for each
        split.
    """
    n_total = len(subject_dirs)
    if n_splits > 1:
        n_test = int(np.ceil(n_total / n_splits))
    else:
        n_test = int(np.ceil(n_total * cfg.splitting.test_fraction))
    if cfg.splitting.max_test_subjects is not None:
        n_test = min(n_test, cfg.splitting.max_test_subjects)
    n_val = int(np.ceil(n_total * cfg.splitting.validation_fraction))
    if cfg.splitting.max_validation_subjects is not None:
        n_val = min(n_val, cfg.splitting.max_validation_subjects)
    if n_val + n_test > n_total:
        raise ValueError(
            "Too large test/validation_fraction - fractions must be <= 1.0 in total"
        )
    n_train = n_total - n_test - n_val
    return n_train, n_val, n_test


@hydra.main(config_path="./config", version_base="1.2", config_name="data_splits")
def main(cfg: DictConfig):
    hydra_cfg = HydraConfig.get()
    logger.info(f"overrides:\n{OmegaConf.to_yaml(hydra_cfg.overrides)}")

    save_file = os.path.abspath(cfg.save_file)
    n_splits = int(cfg.cv_n_splits)
    randomstate = np.random.RandomState(cfg.seed)

    if os.path.exists(save_file):
        raise FileExistsError(f"File {save_file} already exists!")

    out_dir = os.path.split(save_file)[0]
    os.makedirs(out_dir, exist_ok=True)

    datasplit_dict = defaultdict(dict)

    for dataset in cfg.datasets:
        dataset_cfg = cfg.datasets[dataset]
        # Process each dataset
        dataset_name = dataset_cfg.name
        logger.info(f"Processing dataset {dataset_name}")

        data_dir = os.path.join(cfg.general.save_dir, dataset_name)

        # Get subject dirs
        subject_dirs = glob(os.path.join(data_dir, "*"))
        subject_dir_names = [os.path.split(i)[-1] for i in subject_dirs]
        subject_dir_names = [
            i for i in subject_dir_names if i not in dataset_cfg.bad_recordings
        ]

        if dataset_cfg.splitting.family_id_extractor is not None:
            family_ids = instantiate(dataset_cfg.splitting.family_id_extractor)
            mapped_subject_dirs = defaultdict(list)
            for subject_dir in subject_dir_names:
                subject_id = os.path.split(subject_dir)[-1]
                family_id = family_ids[subject_id]
                mapped_subject_dirs[family_id].append(subject_dir)
            subject_dir_names = np.array(
                list(mapped_subject_dirs.values()), dtype=object
            )
        else:
            subject_dir_names = pair_by_names(
                subject_dir_names, dataset_cfg.splitting.subject_id_regex
            )

        if n_splits > len(subject_dir_names):
            raise ValueError(
                f"CV ({n_splits}) cannot be larger than number of "
                f"subjects ({len(subject_dir_names)})"
            )

        # Get train/val/test sizes
        n_train, n_val, n_test = get_split_sizes(
            subject_dir_names, n_splits, dataset_cfg
        )

        # Shuffle and split the files into CV parts
        randomstate.shuffle(subject_dir_names)
        splits = np.array_split(subject_dir_names, n_splits)

        # Prepare dataframe to store counts
        col_names = (
            ["split_{}".format(i) for i in range(n_splits)]
            if n_splits != 1
            else ["fixed_split"]
        )
        counts_df = pd.DataFrame(
            index=[
                "train_records",
                "train_subjects",
                "val_records",
                "val_subjects",
                "test_records",
                "test_subjects",
                "total_records",
                "total_subjects",
            ],
            columns=col_names,
        )

        # write files to save_file
        for split_index, (test_split, col_name) in enumerate(zip(splits, col_names)):
            print("  Split %i/%i" % (split_index + 1, n_splits), end="\r", flush=True)

            # Set root path to split folder
            if n_splits > 1:
                save_key = f"split_{split_index}"
                test_data = test_split
                train_val_data = np.concatenate(
                    [x for ind, x in enumerate(splits) if ind != split_index]
                )
            else:
                save_key = None
                test_data = splits[0][:n_test]  # 0, because there is only 1 split
                train_val_data = splits[0][n_test:]

            # Extract validation data from the remaining data
            randomstate.shuffle(train_val_data)
            valid_data = train_val_data[:n_val]
            train_data = train_val_data[n_val:]

            # resolve subjects into records
            train_records = [str(rec) for tup in train_data for rec in tup]
            valid_records = [str(rec) for tup in valid_data for rec in tup]
            test_records = [str(rec) for tup in test_data for rec in tup]

            if save_key is not None and save_key not in datasplit_dict:
                datasplit_dict[save_key] = defaultdict(dict)

            if save_key is not None:
                if len(train_records) > 0:
                    datasplit_dict[save_key]["train"][dataset_name] = train_records
                if len(valid_records) > 0:
                    datasplit_dict[save_key]["valid"][dataset_name] = valid_records
                if len(test_records) > 0:
                    datasplit_dict[save_key]["test"][dataset_name] = test_records
            else:
                if len(train_records) > 0:
                    datasplit_dict["train"][dataset_name] = train_records
                if len(valid_records) > 0:
                    datasplit_dict["valid"][dataset_name] = valid_records
                if len(test_records) > 0:
                    datasplit_dict["test"][dataset_name] = test_records

            counts_col = [
                len(train_records),
                len(train_data),
                len(valid_records),
                len(valid_data),
                len(test_records),
                len(test_data),
                np.sum([len(train_records), len(valid_records), len(test_records)]),
                np.sum([len(train_data), len(valid_data), len(test_data)]),
            ]
            counts_df[col_name] = counts_col
        counts_df["sum"] = np.sum(counts_df, axis=1)
        logger.info(f"\n{counts_df.T}")

    # Save datasplit_dict
    logger.info(f"Saving datasplit_dict to {save_file}")
    with open(save_file, "w") as f:
        f.write(dict_to_yaml(datasplit_dict))


if __name__ == "__main__":
    main()
